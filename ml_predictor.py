# ml_predictor.py
"""
Random Forest based travel-time / parking-occupancy forecaster for the
Durg-Bhilai-Raipur corridor.

Synchronized with traffic_engine.py:
  - Imports the SAME `CORRIDOR_NODES` coordinates, so both modules always
    agree on where "Durg Station", "Telibandha Lake Raipur", etc. actually are.
  - Reuses `MapplsTrafficEngine.classify_congestion()` so a "MODERATE TRAFFIC"
    label means exactly the same thing whether it came from a live API call
    or a model prediction.
  - Can pull live readings straight from `MapplsTrafficEngine` and blend them
    into the training set (`sync_with_live_engine`), so the model gradually
    learns from real traffic instead of only synthetic data.
  - Segment distances are derived from the real corridor coordinates
    (haversine), so travel-time baselines scale correctly for any
    origin/destination pair along the corridor, not just Durg -> Raipur.

New capability requested: predicting travel time / parking availability for
an arbitrary future hour (e.g. "6:00 PM next Tuesday") via
`predict_for_future_datetime(...)` or the convenience
`predict_next_weekday(weekday, hour, ...)`.
"""

import math
import logging
import datetime
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List, Tuple

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

from traffic_engine import CORRIDOR_NODES, MapplsTrafficEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ml_predictor")

DAYS_MAP = {
    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
    "Friday": 4, "Saturday": 5, "Sunday": 6,
}
DAYS_LIST = list(DAYS_MAP.keys())


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in km."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def corridor_path_distance_km(nodes: dict, origin: str, destination: str) -> float:
    """
    Distance along the corridor between two named nodes, summing consecutive
    segment distances if both nodes exist in the ordered corridor, otherwise
    falling back to a straight-line estimate with a road-winding factor.
    """
    names = list(nodes.keys())
    if origin in names and destination in names:
        i, j = names.index(origin), names.index(destination)
        lo, hi = min(i, j), max(i, j)
        dist = 0.0
        for k in range(lo, hi):
            a, b = nodes[names[k]], nodes[names[k + 1]]
            dist += haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
        return dist
    # Fallback: straight-line * typical road-winding factor
    o, d = nodes.get(origin), nodes.get(destination)
    if o and d:
        return haversine_km(o["lat"], o["lon"], d["lat"], d["lon"]) * 1.35
    raise ValueError(f"Unknown corridor node(s): {origin!r} / {destination!r}")


@dataclass
class TrafficForecast:
    """Mirrors TrafficResult from traffic_engine.py so both modules speak
    the same schema downstream (dashboards, APIs, etc.)."""
    origin: str
    destination: str
    target_datetime: str
    predicted_travel_mins: float
    travel_mins_low: float
    travel_mins_high: float
    predicted_parking_pct: float
    congestion_index: float
    status_label: str
    status_color: str
    source: str  # "ml_prediction"


class TrafficPredictorEngine:
    def __init__(
        self,
        corridor_nodes: dict = CORRIDOR_NODES,
        reference_route: Tuple[str, str] = ("Durg Station", "Telibandha Lake Raipur"),
        model_dir: str = "models",
    ):
        self.corridor_nodes = corridor_nodes
        self.reference_origin, self.reference_destination = reference_route
        self.reference_distance_km = corridor_path_distance_km(
            corridor_nodes, self.reference_origin, self.reference_destination
        )

        self.model_travel = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
        self.model_parking = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
        self.is_trained = False

        self.model_dir = Path(model_dir)
        self.live_history: List[dict] = []  # samples collected from the live engine

    # ------------------------------------------------------------------ #
    # Data generation
    # ------------------------------------------------------------------ #
    def generate_synthetic_historical_dataset(self, days_count: int = 60) -> Tuple[pd.DataFrame, np.ndarray, np.ndarray]:
        """
        Generates synthetic training data across EVERY segment of the real
        corridor (not just one route), so the model learns how travel time
        scales with both time-of-day and distance. Distances are derived
        from the actual CORRIDOR_NODES coordinates via haversine, keeping
        this in sync with traffic_engine.py's geography.
        """
        np.random.seed(42)
        names = list(self.corridor_nodes.keys())
        segment_pairs = list(zip(names[:-1], names[1:])) + [
            (self.reference_origin, self.reference_destination)
        ]

        records = []
        hours_per_day = 24
        for origin, destination in segment_pairs:
            dist_km = corridor_path_distance_km(self.corridor_nodes, origin, destination)
            # Assume ~45 km/h average free-flow speed on this corridor,
            # matching the ~38 min baseline traffic_engine.py uses for the
            # full Durg -> Raipur route.
            base_free_flow = max(dist_km / 45.0 * 60.0, 4.0)

            hours = np.tile(np.arange(hours_per_day), days_count)
            day_of_week = np.random.randint(0, 7, hours_per_day * days_count)
            is_weekend = np.where(day_of_week >= 5, 1, 0)

            morning_peak = np.exp(-((hours - 9) ** 2) / 4.0) * (base_free_flow * 0.55)
            evening_peak = np.exp(-((hours - 18) ** 2) / 5.0) * (base_free_flow * 0.65)
            weekend_factor = is_weekend * (-base_free_flow * 0.20)
            noise = np.random.normal(0, base_free_flow * 0.06, hours_per_day * days_count)

            y_travel = base_free_flow + morning_peak + evening_peak + weekend_factor + noise
            y_travel = np.clip(y_travel, base_free_flow * 0.9, base_free_flow * 2.0)

            for h, d, w, y in zip(hours, day_of_week, is_weekend, y_travel):
                records.append({
                    "hour": h, "day_of_week": d, "is_weekend": w,
                    "distance_km": round(dist_km, 2), "travel_mins": round(float(y), 1),
                })

        df = pd.DataFrame(records)
        X = df[["hour", "day_of_week", "is_weekend", "distance_km"]]
        y_travel = df["travel_mins"].values

        # Parking occupancy stays corridor-hub-generic (not distance dependent)
        hours_all = df["hour"].values
        parking_base = 25.0 + (np.sin((hours_all - 12) / 3.5) ** 2) * 55.0
        parking_noise = np.random.normal(0, 3.0, len(df))
        y_parking = np.clip(parking_base + parking_noise, 10.0, 98.0)

        return X, y_travel, y_parking

    # ------------------------------------------------------------------ #
    # Training
    # ------------------------------------------------------------------ #
    def train_models(self, extra_X: Optional[pd.DataFrame] = None,
                      extra_y_travel: Optional[np.ndarray] = None) -> Tuple[float, float]:
        """Trains both Random Forest models. Optionally blends in real
        live-observed data (see sync_with_live_engine) alongside the
        synthetic dataset."""
        X, y_travel, y_parking = self.generate_synthetic_historical_dataset()

        if extra_X is not None and extra_y_travel is not None and len(extra_X) > 0:
            # Oversample live data slightly so real observations carry more
            # weight than a single synthetic row would.
            repeat = max(1, len(X) // max(len(extra_X), 1) // 20)
            X = pd.concat([X] + [extra_X] * repeat, ignore_index=True)
            y_travel = np.concatenate([y_travel] + [extra_y_travel] * repeat)
            logger.info("Blended %d live samples (x%d weight) into training set.", len(extra_X), repeat)

        X_train, X_test, y_tr_train, y_tr_test = train_test_split(
            X, y_travel, test_size=0.2, random_state=42
        )
        self.model_travel.fit(X_train, y_tr_train)
        mae_travel = round(mean_absolute_error(y_tr_test, self.model_travel.predict(X_test)), 2)

        # Parking model trains on the (unmodified) synthetic-only features
        X_park, _, y_parking = self.generate_synthetic_historical_dataset()
        Xp_train, Xp_test, yp_train, yp_test = train_test_split(
            X_park[["hour", "day_of_week", "is_weekend"]], y_parking, test_size=0.2, random_state=42
        )
        self.model_parking.fit(Xp_train, yp_train)
        mae_parking = round(mean_absolute_error(yp_test, self.model_parking.predict(Xp_test)), 2)

        self.is_trained = True
        logger.info("Training complete. Travel MAE=%.2f min, Parking MAE=%.2f%%", mae_travel, mae_parking)
        return mae_travel, mae_parking

    def save(self, name: str = "traffic_predictor") -> None:
        self.model_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model_travel, self.model_dir / f"{name}_travel.joblib")
        joblib.dump(self.model_parking, self.model_dir / f"{name}_parking.joblib")
        logger.info("Models saved to %s/", self.model_dir)

    def load(self, name: str = "traffic_predictor") -> bool:
        travel_path = self.model_dir / f"{name}_travel.joblib"
        parking_path = self.model_dir / f"{name}_parking.joblib"
        if travel_path.exists() and parking_path.exists():
            self.model_travel = joblib.load(travel_path)
            self.model_parking = joblib.load(parking_path)
            self.is_trained = True
            logger.info("Loaded existing models from %s/", self.model_dir)
            return True
        return False

    # ------------------------------------------------------------------ #
    # Live-data synchronization
    # ------------------------------------------------------------------ #
    def sync_with_live_engine(self, engine: MapplsTrafficEngine, retrain: bool = True) -> int:
        """
        Pulls a fresh live snapshot for every corridor segment from
        MapplsTrafficEngine and stores it as a training sample tagged with
        the CURRENT hour/day. Call this periodically (e.g. hourly cron) to
        let the model absorb real conditions over time. Returns the number
        of samples collected.
        """
        snapshot = engine.fetch_corridor_snapshot(self.corridor_nodes)
        now = datetime.datetime.now()

        new_samples = 0
        for seg_name, result in snapshot.items():
            origin, destination = [s.strip() for s in seg_name.split("->")]
            try:
                dist_km = corridor_path_distance_km(self.corridor_nodes, origin, destination)
            except ValueError:
                continue
            self.live_history.append({
                "hour": now.hour,
                "day_of_week": now.weekday(),
                "is_weekend": int(now.weekday() >= 5),
                "distance_km": round(dist_km, 2),
                "travel_mins": result.live_mins,
            })
            new_samples += 1

        logger.info("Collected %d live samples from MapplsTrafficEngine.", new_samples)

        if retrain and self.live_history:
            live_df = pd.DataFrame(self.live_history)
            self.train_models(
                extra_X=live_df[["hour", "day_of_week", "is_weekend", "distance_km"]],
                extra_y_travel=live_df["travel_mins"].values,
            )
        return new_samples

    # ------------------------------------------------------------------ #
    # Prediction
    # ------------------------------------------------------------------ #
    def _predict_with_confidence(self, model: RandomForestRegressor, input_row: pd.DataFrame) -> Tuple[float, float, float]:
        """Returns (mean, low, high) using the spread across individual trees
        in the forest as an approximate 90% confidence interval."""
        row_values = input_row.values  # individual trees don't carry feature-name metadata
        tree_preds = np.array([tree.predict(row_values)[0] for tree in model.estimators_])
        mean = float(tree_preds.mean())
        low = float(np.percentile(tree_preds, 5))
        high = float(np.percentile(tree_preds, 95))
        return round(mean, 1), round(low, 1), round(high, 1)

    def predict(
        self,
        hour: int,
        day_of_week_str: str,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
    ) -> TrafficForecast:
        """Predicts travel time + parking occupancy for a given hour/day
        along a given corridor segment (defaults to the reference route)."""
        if not self.is_trained:
            self.train_models()

        origin = origin or self.reference_origin
        destination = destination or self.reference_destination
        dist_km = corridor_path_distance_km(self.corridor_nodes, origin, destination)
        free_flow_mins = max(dist_km / 45.0 * 60.0, 4.0)

        day_num = DAYS_MAP.get(day_of_week_str, 0)
        is_wknd = int(day_num >= 5)

        travel_input = pd.DataFrame(
            [[hour, day_num, is_wknd, dist_km]],
            columns=["hour", "day_of_week", "is_weekend", "distance_km"],
        )
        parking_input = pd.DataFrame(
            [[hour, day_num, is_wknd]], columns=["hour", "day_of_week", "is_weekend"]
        )

        pred_travel, low, high = self._predict_with_confidence(self.model_travel, travel_input)
        pred_parking = round(self.model_parking.predict(parking_input)[0], 1)

        congestion_index = round(pred_travel / max(free_flow_mins, 1.0), 2)
        status_label, status_color = MapplsTrafficEngine.classify_congestion(congestion_index)

        target_repr = f"{day_of_week_str} @ {hour:02d}:00"
        return TrafficForecast(
            origin=origin,
            destination=destination,
            target_datetime=target_repr,
            predicted_travel_mins=pred_travel,
            travel_mins_low=low,
            travel_mins_high=high,
            predicted_parking_pct=pred_parking,
            congestion_index=congestion_index,
            status_label=status_label,
            status_color=status_color,
            source="ml_prediction",
        )

    def predict_for_future_datetime(
        self,
        target_dt: datetime.datetime,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
    ) -> TrafficForecast:
        """Predicts for an explicit future datetime object."""
        day_name = DAYS_LIST[target_dt.weekday()]
        forecast = self.predict(target_dt.hour, day_name, origin, destination)
        forecast.target_datetime = target_dt.strftime("%A, %d %b %Y @ %H:%M")
        return forecast

    def predict_next_weekday(
        self,
        weekday_name: str,
        hour: int,
        minute: int = 0,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        from_dt: Optional[datetime.datetime] = None,
    ) -> TrafficForecast:
        """
        Convenience wrapper for requests like "6:00 PM next Tuesday".
        Finds the next occurrence of `weekday_name` at `hour`:`minute` that
        is strictly in the future relative to `from_dt` (defaults to now).
        """
        if weekday_name not in DAYS_MAP:
            raise ValueError(f"Unknown weekday: {weekday_name!r}")

        now = from_dt or datetime.datetime.now()
        target_weekday = DAYS_MAP[weekday_name]
        days_ahead = (target_weekday - now.weekday()) % 7
        candidate = (now + datetime.timedelta(days=days_ahead)).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )
        if candidate <= now:
            candidate += datetime.timedelta(days=7)

        return self.predict_for_future_datetime(candidate, origin, destination)

    def predict_full_corridor(
        self, hour: int, day_of_week_str: str
    ) -> List[TrafficForecast]:
        """Predicts every consecutive segment of the corridor for the given
        hour/day in one call — useful for a full-route forecast dashboard."""
        names = list(self.corridor_nodes.keys())
        return [
            self.predict(hour, day_of_week_str, o, d)
            for o, d in zip(names[:-1], names[1:])
        ]


# Quick test runner
if __name__ == "__main__":
    predictor = TrafficPredictorEngine()

    if not predictor.load():
        mae_t, mae_p = predictor.train_models()
        predictor.save()
        print("=== ML MODEL TRAINING COMPLETE ===")
        print(f"Travel Time Model MAE : ±{mae_t} minutes")
        print(f"Parking Model MAE     : ±{mae_p}% occupancy\n")
    else:
        print("=== LOADED EXISTING MODELS FROM DISK ===\n")

    # Sample prediction: Friday @ 6 PM, Durg -> Raipur (reference route)
    forecast = predictor.predict(hour=18, day_of_week_str="Friday")
    print("--- SAMPLE PREDICTION (Friday @ 6:00 PM, Durg -> Raipur) ---")
    print(f"Predicted Travel Time : {forecast.predicted_travel_mins} mins "
          f"(90% CI: {forecast.travel_mins_low}-{forecast.travel_mins_high})")
    print(f"Predicted Parking     : {forecast.predicted_parking_pct}%")
    print(f"Congestion            : {forecast.congestion_index}x — {forecast.status_label}\n")

    # Requested scenario: "6:00 PM next Tuesday"
    next_tue = predictor.predict_next_weekday("Tuesday", hour=18)
    print(f"--- FORECAST: {next_tue.target_datetime} ({next_tue.origin} -> {next_tue.destination}) ---")
    print(f"Predicted Travel Time : {next_tue.predicted_travel_mins} mins "
          f"(90% CI: {next_tue.travel_mins_low}-{next_tue.travel_mins_high})")
    print(f"Predicted Parking     : {next_tue.predicted_parking_pct}%")
    print(f"Congestion            : {next_tue.congestion_index}x — {next_tue.status_label}\n")

    # Full corridor forecast for the same future slot
    print("--- FULL CORRIDOR FORECAST (Tuesday @ 18:00) ---")
    for seg in predictor.predict_full_corridor(hour=18, day_of_week_str="Tuesday"):
        print(f"{seg.origin:22s} -> {seg.destination:25s} | {seg.predicted_travel_mins:5.1f} min | {seg.status_label}")

    # Optional: sync with the live engine (uses fallback heuristic if no API key)
    print("\n--- SYNCING WITH LIVE TRAFFIC ENGINE ---")
    live_engine = MapplsTrafficEngine()
    n = predictor.sync_with_live_engine(live_engine)
    print(f"Absorbed {n} live samples into the model and retrained.")