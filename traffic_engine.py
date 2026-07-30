# traffic_engine.py
"""
Live traffic engine for the Durg–Raipur corridor.

Enhancements over the original version:
  - Session reuse + automatic retries with backoff for TomTom API calls
  - Real timeout/connection-error handling via a proper Retry adapter
  - Short-lived in-memory caching so repeated calls (e.g. dashboard polling)
    don't hammer the API or the heuristic fallback unnecessarily
  - Concurrent fetching across multiple corridor segments (ThreadPoolExecutor)
  - Structured logging instead of print()
  - Type hints + dataclass result object instead of a raw tuple
  - API key sourced from env var (TOMTOM_API_KEY) if not passed explicitly
  - Input validation on coordinates
"""

import os
import time
import logging
import datetime
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Tuple, List
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter, Retry
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("traffic_engine")

# Coordinates for key corridor segments
CORRIDOR_NODES: Dict[str, Dict[str, float]] = {
    "Durg Station": {"lat": 21.1904, "lon": 81.2849},
    "Bhilai Steel Plant": {"lat": 21.1784, "lon": 81.3813},
    "GE Road Charoda": {"lat": 21.2162, "lon": 81.4468},
    "Amanaka Flyover Raipur": {"lat": 21.2468, "lon": 81.5985},
    "Raipur Clock Tower": {"lat": 21.2422, "lon": 81.6337},
    "Telibandha Lake Raipur": {"lat": 21.2335, "lon": 81.6616},
}


@dataclass
class TrafficResult:
    live_mins: float
    free_flow_mins: float
    congestion_index: float
    status_label: str
    status_color: str
    source: str  # "tomtom_api" or "heuristic_fallback"
    timestamp: str

    def as_dict(self) -> dict:
        return asdict(self)


class TomTomTrafficEngine:
    BASE_URL = "https://api.tomtom.com/routing/1/calculateRoute"

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_ttl_seconds: int = 90,
        max_retries: int = 3,
        request_timeout: int = 6,
    ):
        # Fall back to environment variable so the key isn't hardcoded in scripts
        self.api_key = api_key or os.environ.get("TOMTOM_API_KEY")
        self.request_timeout = request_timeout
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: Dict[Tuple[float, float, float, float], Tuple[float, TrafficResult]] = {}

        # Reusable session with retry/backoff for transient network issues
        self.session = requests.Session()
        retries = Retry(
            total=max_retries,
            backoff_factor=0.5,  # 0.5s, 1s, 2s...
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _has_valid_key(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    @staticmethod
    def _validate_coords(lat: float, lon: float) -> None:
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            raise ValueError(f"Invalid coordinates: lat={lat}, lon={lon}")

    def _cache_get(self, key: Tuple[float, float, float, float]) -> Optional[TrafficResult]:
        entry = self._cache.get(key)
        if not entry:
            return None
        cached_at, result = entry
        if time.time() - cached_at > self.cache_ttl_seconds:
            return None
        return result

    def _cache_set(self, key: Tuple[float, float, float, float], result: TrafficResult) -> None:
        self._cache[key] = (time.time(), result)

    def fetch_live_travel_time(
        self,
        orig_lat: float,
        orig_lon: float,
        dest_lat: float,
        dest_lon: float,
        use_cache: bool = True,
    ) -> TrafficResult:
        """
        Fetches travel time using the TomTom Calculate Route API, with
        caching, retries, and a heuristic fallback if the API is unavailable.
        """
        self._validate_coords(orig_lat, orig_lon)
        self._validate_coords(dest_lat, dest_lon)

        cache_key = (orig_lat, orig_lon, dest_lat, dest_lon)
        if use_cache:
            cached = self._cache_get(cache_key)
            if cached:
                logger.info("Cache hit for %s", cache_key)
                return cached

        result = self._fetch_from_api(orig_lat, orig_lon, dest_lat, dest_lon)
        if result is None:
            result = self._heuristic_fallback()

        self._cache_set(cache_key, result)
        return result

    def _fetch_from_api(
        self, orig_lat: float, orig_lon: float, dest_lat: float, dest_lon: float
    ) -> Optional[TrafficResult]:
        if not self._has_valid_key():
            logger.info("No valid TomTom API key configured; skipping live call.")
            return None

        url = f"{self.BASE_URL}/{orig_lat},{orig_lon}:{dest_lat},{dest_lon}/json"
        params = {
            "key": self.api_key,
            "traffic": "true",
            # Without this, TomTom omits noTrafficTravelTimeInSeconds (and the
            # historic/live-incident variants) from the summary entirely.
            "computeTravelTimeFor": "all",
        }

        try:
            response = self.session.get(url, params=params, timeout=self.request_timeout)
            response.raise_for_status()
            data = response.json()

            routes = data.get("routes")
            if not routes:
                logger.warning("TomTom response had no routes; falling back.")
                return None

            summary = routes[0]["summary"]
            live_sec = summary["travelTimeInSeconds"]

            # noTrafficTravelTimeInSeconds should be present now, but fall back
            # to deriving it from the (always-present) trafficDelayInSeconds
            # if TomTom ever omits it again.
            if "noTrafficTravelTimeInSeconds" in summary:
                free_sec = summary["noTrafficTravelTimeInSeconds"]
            else:
                delay_sec = summary.get("trafficDelayInSeconds", 0)
                free_sec = max(live_sec - delay_sec, 1)
                logger.info(
                    "noTrafficTravelTimeInSeconds missing from response; "
                    "derived free-flow time from trafficDelayInSeconds instead."
                )

            live_mins = round(live_sec / 60.0, 1)
            free_mins = round(free_sec / 60.0, 1)
            congestion_index = round(live_mins / max(free_mins, 1.0), 2)
            status_label, status_color = self.classify_congestion(congestion_index)

            return TrafficResult(
                live_mins=live_mins,
                free_flow_mins=free_mins,
                congestion_index=congestion_index,
                status_label=status_label,
                status_color=status_color,
                source="tomtom_api",
                timestamp=datetime.datetime.now().isoformat(timespec="seconds"),
            )

        except requests.exceptions.Timeout:
            logger.warning("TomTom API timed out after %ss; falling back.", self.request_timeout)
        except requests.exceptions.HTTPError as e:
            logger.warning("TomTom API HTTP error: %s; falling back.", e)
        except (KeyError, IndexError, ValueError) as e:
            logger.warning("TomTom API returned unexpected payload (%s); falling back.", e)
        except requests.exceptions.RequestException as e:
            logger.warning("TomTom API request failed (%s); falling back.", e)

        return None

    def _heuristic_fallback(self) -> TrafficResult:
        """Dynamic heuristic fallback modeling the Durg-Raipur peak curve."""
        current_hour = datetime.datetime.now().hour
        base_free_flow = 38.0  # Approx 38 mins baseline between Durg and Raipur

        if 9 <= current_hour <= 11 or 18 <= current_hour <= 20:
            mult = np.random.uniform(1.35, 1.65)
        elif 12 <= current_hour <= 16:
            mult = np.random.uniform(1.10, 1.25)
        else:
            mult = np.random.uniform(1.00, 1.10)

        live_mins = round(base_free_flow * mult, 1)
        free_mins = base_free_flow
        congestion_index = round(live_mins / free_mins, 2)
        status_label, status_color = self.classify_congestion(congestion_index)

        return TrafficResult(
            live_mins=live_mins,
            free_flow_mins=free_mins,
            congestion_index=congestion_index,
            status_label=status_label,
            status_color=status_color,
            source="heuristic_fallback",
            timestamp=datetime.datetime.now().isoformat(timespec="seconds"),
        )

    @staticmethod
    def classify_congestion(index: float) -> Tuple[str, str]:
        """Categorizes congestion levels based on index thresholds."""
        if index >= 1.35:
            return "PEAK / HEAVY TRAFFIC", "#FF4B4B"  # Red
        elif index >= 1.15:
            return "MODERATE TRAFFIC", "#FFAA00"       # Orange
        else:
            return "NORMAL / SMOOTH FLOW", "#00CC96"   # Green

    def fetch_corridor_snapshot(
        self, nodes: Dict[str, Dict[str, float]] = CORRIDOR_NODES, max_workers: int = 4
    ) -> Dict[str, TrafficResult]:
        """
        Fetches travel time for every consecutive segment along the corridor
        concurrently, returning a dict keyed by 'Origin -> Destination'.
        """
        names = list(nodes.keys())
        segments = list(zip(names[:-1], names[1:]))
        results: Dict[str, TrafficResult] = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_seg = {
                executor.submit(
                    self.fetch_live_travel_time,
                    nodes[o]["lat"], nodes[o]["lon"],
                    nodes[d]["lat"], nodes[d]["lon"],
                ): f"{o} -> {d}"
                for o, d in segments
            }
            for future in as_completed(future_to_seg):
                seg_name = future_to_seg[future]
                try:
                    results[seg_name] = future.result()
                except Exception as e:
                    logger.error("Segment %s failed: %s", seg_name, e)

        return results


# Quick test runner
if __name__ == "__main__":
    engine = TomTomTrafficEngine(api_key=os.getenv("TOMTOM_API_KEY")) # or set TOMTOM_API_KEY env var

    durg = CORRIDOR_NODES["Durg Station"]
    raipur = CORRIDOR_NODES["Telibandha Lake Raipur"]

    result = engine.fetch_live_travel_time(
        durg["lat"], durg["lon"], raipur["lat"], raipur["lon"]
    )
    print("=== LIVE CORRIDOR STATS (Durg -> Raipur) ===")
    print(f"Travel Time     : {result.live_mins} mins (Free-flow: {result.free_flow_mins} mins)")
    print(f"Congestion Index: {result.congestion_index}x")
    print(f"Status          : {result.status_label}")
    print(f"Source          : {result.source}")
    print()

    print("=== FULL CORRIDOR SNAPSHOT (concurrent) ===")
    snapshot = engine.fetch_corridor_snapshot()
    for segment, res in snapshot.items():
        print(f"{segment:45s} | {res.live_mins:5.1f} min | {res.status_label:22s} | {res.source}")