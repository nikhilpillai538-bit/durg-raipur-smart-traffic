# app.py — Flask backend for the UrbanFlow dashboard
#
# The HTML/JS frontend (templates/index.html + static/js/app.js) is static —
# browsers can't import Python. This server is the bridge: it wraps
# traffic_engine.py, ml_predictor.py, and your parking modules behind a small
# JSON API that the page's JavaScript calls.
#
# Run with:  python app.py
# Then open: http://127.0.0.1:5000

from flask import Flask, jsonify, request, render_template

from traffic_engine import CORRIDOR_NODES, TomTomTrafficEngine
from ml_predictor import TrafficPredictorEngine

# Same two files your Streamlit app already depends on — keep them in this folder.
from parking_spots import PARKING_HUBS
from parking_generator import ParkingMockGenerator

app = Flask(__name__)

# ---------------------------------------------------------------
# One-time setup (mirrors the @st.cache_resource pattern from the
# Streamlit app — load a saved model if one exists, else train once).
# ---------------------------------------------------------------
predictor = TrafficPredictorEngine()
if not predictor.load():
    predictor.train_models()
    predictor.save()

parking_gen = ParkingMockGenerator(PARKING_HUBS)

# The mockup's sidebar only offers "Weekday" / "Weekend" (not a full 7-day
# picker), so we map each choice to one representative day for the model.
DAY_CHOICE_MAP = {
    "weekday": "Wednesday",
    "weekend": "Saturday",
}


def get_engine() -> TomTomTrafficEngine:
    """Build an engine using an API key from the request, if the page sent one."""
    api_key = request.args.get("api_key") or request.headers.get("X-TomTom-Key")
    return TomTomTrafficEngine(api_key=api_key or None)


def resolve_day(day_param: str) -> str:
    return DAY_CHOICE_MAP.get((day_param or "weekday").lower(), "Wednesday")


def result_to_dict(r) -> dict:
    return {
        "live_mins": r.live_mins,
        "free_flow_mins": r.free_flow_mins,
        "congestion_index": r.congestion_index,
        "status_label": r.status_label,
        "status_color": r.status_color,
        "source": r.source,
        "timestamp": r.timestamp,
    }


def forecast_to_dict(f) -> dict:
    return {
        "origin": f.origin,
        "destination": f.destination,
        "target_datetime": f.target_datetime,
        "predicted_travel_mins": f.predicted_travel_mins,
        "travel_mins_low": f.travel_mins_low,
        "travel_mins_high": f.travel_mins_high,
        "predicted_parking_pct": f.predicted_parking_pct,
        "congestion_index": f.congestion_index,
        "status_label": f.status_label,
        "status_color": f.status_color,
    }


def calculate_environmental_impact(extra_delay_mins: float, vehicle_count: int = 1):
    wasted_liters = (extra_delay_mins / 60.0) * 0.6 * vehicle_count  # ~0.6 L/hour idling
    wasted_inr = wasted_liters * 102.0  # approx Rs.102/Liter petrol rate
    co2_kg = wasted_liters * 2.3  # ~2.3 kg CO2 per liter of petrol
    return round(wasted_liters, 2), round(wasted_inr, 1), round(co2_kg, 2)


# ---------------------------------------------------------------
# Page
# ---------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", nodes=list(CORRIDOR_NODES.keys()))


# ---------------------------------------------------------------
# JSON API — everything the page's JS calls
# ---------------------------------------------------------------
@app.route("/api/nodes")
def api_nodes():
    return jsonify(list(CORRIDOR_NODES.keys()))


@app.route("/api/live")
def api_live():
    origin = request.args.get("origin", "Durg Station")
    destination = request.args.get("destination", "Telibandha Lake Raipur")
    if origin not in CORRIDOR_NODES or destination not in CORRIDOR_NODES:
        return jsonify({"error": f"unknown origin/destination: {origin} / {destination}"}), 400

    engine = get_engine()
    o, d = CORRIDOR_NODES[origin], CORRIDOR_NODES[destination]
    result = engine.fetch_live_travel_time(o["lat"], o["lon"], d["lat"], d["lon"])
    return jsonify(result_to_dict(result))


@app.route("/api/corridor-snapshot")
def api_corridor_snapshot():
    engine = get_engine()
    snapshot = engine.fetch_corridor_snapshot()
    return jsonify({seg: result_to_dict(r) for seg, r in snapshot.items()})


@app.route("/api/forecast")
def api_forecast():
    hour = int(request.args.get("hour", 12))
    day = resolve_day(request.args.get("day"))
    origin = request.args.get("origin", "Durg Station")
    destination = request.args.get("destination", "Telibandha Lake Raipur")
    f = predictor.predict(hour, day, origin, destination)
    return jsonify(forecast_to_dict(f))


@app.route("/api/forecast-24h")
def api_forecast_24h():
    day = resolve_day(request.args.get("day"))
    origin = request.args.get("origin", "Durg Station")
    destination = request.args.get("destination", "Telibandha Lake Raipur")
    forecasts = [predictor.predict(h, day, origin, destination) for h in range(24)]
    return jsonify([forecast_to_dict(f) for f in forecasts])


@app.route("/api/best-time")
def api_best_time():
    hour = int(request.args.get("hour", 12))
    day = resolve_day(request.args.get("day"))
    origin = request.args.get("origin", "Durg Station")
    destination = request.args.get("destination", "Telibandha Lake Raipur")

    future_hours = [(hour + i) % 24 for i in range(5)]
    predictions = {h: predictor.predict(h, day, origin, destination).predicted_travel_mins for h in future_hours}
    best_hour = min(predictions, key=predictions.get)
    time_saved = round(predictions[hour] - predictions[best_hour], 1)

    return jsonify({
        "current_hour": hour,
        "best_hour": best_hour,
        "time_saved_mins": time_saved,
        "is_optimal_now": best_hour == hour or time_saved <= 2,
    })


@app.route("/api/parking")
def api_parking():
    df = parking_gen.fetch_snapshot()
    return jsonify(df.to_dict(orient="records"))


@app.route("/api/environmental")
def api_environmental():
    delay_mins = float(request.args.get("delay_mins", 0))
    vehicle_count = int(request.args.get("vehicle_count", 1))
    liters, inr, co2 = calculate_environmental_impact(delay_mins, vehicle_count)
    return jsonify({"fuel_liters": liters, "cost_inr": inr, "co2_kg": co2, "delay_mins": round(delay_mins, 1)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)