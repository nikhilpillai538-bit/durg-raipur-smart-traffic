# app.py
import os
import time
import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import folium
from streamlit_folium import st_folium

# Phase 1 & Phase 2 modules
from parking_spots import PARKING_HUBS
from parking_generator import ParkingMockGenerator
from traffic_engine import CORRIDOR_NODES, TomTomTrafficEngine
from ml_predictor import TrafficPredictorEngine

# ==========================================
# PAGE SETUP
# ==========================================
st.set_page_config(
    page_title="Durg-Raipur Smart Traffic Engine",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==========================================
# THEME (light / dark toggle) — kept simple on purpose
# ==========================================
LIGHT_THEME = {
    "app_bg": "#FFFFFF",
    "sidebar_bg": "#F5F6FA",
    "text": "#1A1A1A",
    "accent": "#1565C0",
    "grid": "#E0E0E0",
    "fig_bg": "#FFFFFF",
    "primary": "#1565C0",
    "highlight": "#E64A19",
    "fill": "#BBDEFB",
    "map_tiles": "CartoDB positron",
}
DARK_THEME = {
    "app_bg": "#0E1117",
    "sidebar_bg": "#1A1D24",
    "text": "#EEEEEE",
    "accent": "#00BCD4",
    "grid": "#2D323E",
    "fig_bg": "#161A22",
    "primary": "#00BCD4",
    "highlight": "#FF7043",
    "fill": "#0D4753",
    "map_tiles": "CartoDB dark_matter",
}

dark_mode = st.sidebar.checkbox("🌙 Dark mode", value=False)
THEME = DARK_THEME if dark_mode else LIGHT_THEME

# CSS — covers every text-bearing element explicitly, not just headers,
# so nothing ends up dark-text-on-dark-background (or the reverse).
st.markdown(
    f"""
    <style>
        .stApp {{ background-color: {THEME['app_bg']}; }}
        section[data-testid="stSidebar"] {{ background-color: {THEME['sidebar_bg']}; }}

        /* General body text: paragraphs, captions, widget labels, radio/checkbox labels */
        .stApp p, .stApp span, .stApp label, .stApp li,
        div[data-testid="stMarkdownContainer"] p,
        div[data-testid="stCaptionContainer"],
        div[data-testid="stWidgetLabel"] p,
        div[data-testid="stWidgetLabel"] label {{
            color: {THEME['text']} !important;
        }}

        div[data-testid="stMetricValue"] {{ color: {THEME['accent']}; }}
        div[data-testid="stMetricLabel"], div[data-testid="stMetricDelta"] {{ color: {THEME['text']} !important; }}
        h1, h2, h3 {{ color: {THEME['text']}; }}
        .stTabs [aria-selected="true"] {{ color: {THEME['accent']} !important; border-bottom-color: {THEME['accent']} !important; }}
        .stTabs [data-baseweb="tab"] {{ color: {THEME['text']}; }}
        div[data-testid="stExpander"] {{ border: 1px solid {THEME['grid']}; border-radius: 6px; }}

        /* Dropdown widgets (selectbox) — both the closed box and the open popover list */
        div[data-baseweb="select"] > div {{
            background-color: {THEME['fig_bg']} !important;
            color: {THEME['text']} !important;
            border-color: {THEME['grid']} !important;
        }}
        div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"] {{
            background-color: {THEME['fig_bg']} !important;
        }}
        div[role="option"], li[role="option"] {{
            background-color: {THEME['fig_bg']} !important;
            color: {THEME['text']} !important;
        }}
        div[role="option"]:hover, li[role="option"]:hover {{
            background-color: {THEME['grid']} !important;
        }}

        /* Radio buttons (used for day-of-week) */
        div[role="radiogroup"] label, div[role="radiogroup"] p {{
            color: {THEME['text']} !important;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Durg – Raipur Smart Traffic & Parking Dashboard")
st.caption("Live corridor monitoring and travel-time predictions for NH-49 / GE Road")

# ==========================================
# CACHED INITIALIZATION
# ==========================================
@st.cache_resource
def load_ml_engine() -> TrafficPredictorEngine:
    predictor = TrafficPredictorEngine()
    if not predictor.load():
        predictor.train_models()
        predictor.save()
    return predictor


@st.cache_data(ttl=60)
def get_live_traffic(_engine: TomTomTrafficEngine, o_lat, o_lon, d_lat, d_lon):
    return _engine.fetch_live_travel_time(o_lat, o_lon, d_lat, d_lon)


@st.cache_data(ttl=60)
def get_parking_snapshot(_gen: ParkingMockGenerator) -> pd.DataFrame:
    return _gen.fetch_snapshot()


@st.cache_data(ttl=60)
def get_corridor_snapshot(_engine: TomTomTrafficEngine):
    return _engine.fetch_corridor_snapshot()


ml_engine = load_ml_engine()
parking_gen = ParkingMockGenerator(PARKING_HUBS)

# ==========================================
# SIDEBAR CONTROLS
# ==========================================
st.sidebar.header("Corridor Controls")

api_key = st.sidebar.text_input(
    "TomTom API Key (optional)",
    type="password",
    help="Leave empty to use TOMTOM_API_KEY from the environment, or the local heuristic simulator if neither is set.",
)

st.sidebar.subheader("Route")
origin_node = st.sidebar.selectbox("Origin", list(CORRIDOR_NODES.keys()), index=0)
dest_node = st.sidebar.selectbox("Destination", list(CORRIDOR_NODES.keys()), index=len(CORRIDOR_NODES) - 1)

st.sidebar.subheader("Predict for a different time")
selected_hour = st.sidebar.slider("Hour of day", 0, 23, datetime.datetime.now().hour)

# All 7 days, Monday through Sunday — radio buttons so every option is always
# visible at once, with no dropdown/popover that could clip or hide entries.
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
current_day_idx = min(datetime.datetime.now().weekday(), 6)
selected_day = st.sidebar.radio(
    "Day of week",
    options=DAYS_OF_WEEK,
    index=current_day_idx,
)

st.sidebar.markdown("---")
auto_refresh = st.sidebar.checkbox("🔄 Enable Auto-Refresh (60s)", value=False)

# ==========================================
# LIVE DATA
# ==========================================
traffic_engine = TomTomTrafficEngine(api_key=api_key or None)
orig_coords = CORRIDOR_NODES[origin_node]
dest_coords = CORRIDOR_NODES[dest_node]

live = get_live_traffic(
    traffic_engine, orig_coords["lat"], orig_coords["lon"], dest_coords["lat"], dest_coords["lon"]
)
df_parking = get_parking_snapshot(parking_gen)
avg_available_spots = int(df_parking["available_spots"].mean())

# ==========================================
# TOP METRICS
# ==========================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Live Travel Time", f"{live.live_mins} min", f"{round(live.live_mins - live.free_flow_mins, 1)} min delay")

with col2:
    st.metric("Congestion Index", f"{live.congestion_index}x")

with col3:
    st.markdown("**Current Status**")
    st.markdown(f":{'red' if live.congestion_index >= 1.35 else ('orange' if live.congestion_index >= 1.15 else 'green')}[{live.status_label}]")
    st.caption(f"source: {live.source}")

with col4:
    st.metric("Avg. Parking Openings", f"{avg_available_spots} spots", f"{len(df_parking)} hubs")


def calculate_environmental_impact(extra_delay_mins: float, vehicle_count: int = 1):
    """Rough estimate of fuel wasted and CO2 emitted while idling in traffic delay."""
    wasted_liters = (extra_delay_mins / 60.0) * 0.6 * vehicle_count  # ~0.6 L/hour idling
    wasted_inr = wasted_liters * 102.0  # approx ₹102/Liter petrol rate
    co2_kg = wasted_liters * 2.3  # ~2.3 kg CO2 per liter of petrol
    return round(wasted_liters, 2), round(wasted_inr, 1), round(co2_kg, 2)


delay_mins = max(0.0, live.live_mins - live.free_flow_mins)
liters, inr, co2 = calculate_environmental_impact(delay_mins)

with st.expander("🌱 Environmental & Delay Impact Metrics"):
    ec1, ec2, ec3 = st.columns(3)
    ec1.metric("Fuel Wasted (Idle)", f"{liters} L", f"₹{inr} Cost")
    ec2.metric("Excess CO₂ Emissions", f"{co2} kg", "Per Vehicle Trip")
    ec3.metric("Corridor Delay Factor", f"{round(delay_mins, 1)} Mins", "Above Free-Flow")

st.divider()

tab1, tab2, tab3 = st.tabs(["Live Corridor Map", "Traffic Predictions", "Parking Availability"])

# ------------------------------------------
# TAB 1: LIVE MAP
# ------------------------------------------
with tab1:
    c_map, c_info = st.columns([2, 1])

    with c_map:
        m = folium.Map(location=[21.2150, 81.4800], zoom_start=11, tiles=THEME["map_tiles"])

        folium.Marker(
            [orig_coords["lat"], orig_coords["lon"]],
            popup=f"Origin: {origin_node}",
            icon=folium.Icon(color="green"),
        ).add_to(m)
        folium.Marker(
            [dest_coords["lat"], dest_coords["lon"]],
            popup=f"Destination: {dest_node}",
            icon=folium.Icon(color="red"),
        ).add_to(m)

        folium.PolyLine(
            [(orig_coords["lat"], orig_coords["lon"]), (dest_coords["lat"], dest_coords["lon"])],
            color=live.status_color,
            weight=5,
            opacity=0.8,
        ).add_to(m)

        for _, row in df_parking.iterrows():
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=6,
                popup=f"{row['location_name']}: {row['available_spots']} spots left",
                color="#3186cc",
                fill=True,
                fill_color="#3186cc",
            ).add_to(m)

        st_folium(m, width=720, height=420)

    with c_info:
        st.subheader("Route details")
        st.write(f"Origin: {origin_node}")
        st.write(f"Destination: {dest_node}")
        st.write(f"Free-flow time: {live.free_flow_mins} min")
        st.write(f"Current live time: {live.live_mins} min")

        st.subheader("Recommendation")
        if live.congestion_index >= 1.35:
            st.warning("Heavy traffic on this route. Consider delaying departure by ~20 minutes.")
        elif live.congestion_index >= 1.15:
            st.info("Moderate traffic. Expect minor slowdowns near major junctions.")
        else:
            st.success("Traffic is light — good time to travel.")

    with st.expander("All corridor segments (live)"):
        snapshot = get_corridor_snapshot(traffic_engine)
        rows = [
            {
                "Segment": seg,
                "Live (min)": r.live_mins,
                "Free-flow (min)": r.free_flow_mins,
                "Congestion": r.congestion_index,
                "Status": r.status_label,
                "Source": r.source,
            }
            for seg, r in snapshot.items()
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ------------------------------------------
# TAB 2: TRAFFIC PREDICTIONS
# ------------------------------------------
with tab2:
    st.subheader(f"Predicted 24-hour travel trend ({selected_day}, {origin_node} → {dest_node})")

    chart_type = st.selectbox("Chart type", ["Line", "Bar", "Scatter", "Area", "Pie"])

    hourly_forecasts = [ml_engine.predict(h, selected_day, origin_node, dest_node) for h in range(24)]
    hours = np.arange(24)
    travel_vals = [f.predicted_travel_mins for f in hourly_forecasts]
    status_colors = [f.status_color for f in hourly_forecasts]

    selected_forecast = ml_engine.predict(selected_hour, selected_day, origin_node, dest_node)

    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor(THEME["fig_bg"])
    ax.set_facecolor(THEME["fig_bg"])

    if chart_type == "Line":
        ax.plot(hours, travel_vals, color=THEME["primary"], linewidth=2.5,
                 marker="o", markersize=4, label="Predicted duration (min)")
        ax.scatter([selected_hour], [selected_forecast.predicted_travel_mins],
                    color=THEME["highlight"], s=100, zorder=5,
                    label=f"Selected hour ({selected_hour}:00)")

    elif chart_type == "Bar":
        edge_colors = [THEME["text"] if h == selected_hour else THEME["fig_bg"] for h in hours]
        edge_widths = [2 if h == selected_hour else 0.5 for h in hours]
        ax.bar(hours, travel_vals, color=status_colors, edgecolor=edge_colors, linewidth=edge_widths)

    elif chart_type == "Scatter":
        ax.scatter(hours, travel_vals, c=status_colors, s=70, edgecolor=THEME["fig_bg"], linewidth=0.8)
        ax.scatter([selected_hour], [selected_forecast.predicted_travel_mins],
                    color=THEME["highlight"], s=160, zorder=5, edgecolor=THEME["text"],
                    label=f"Selected hour ({selected_hour}:00)")

    elif chart_type == "Area":
        ax.fill_between(hours, travel_vals, color=THEME["fill"])
        ax.plot(hours, travel_vals, color=THEME["primary"], linewidth=2)
        ax.axvline(selected_hour, color=THEME["highlight"], linestyle="--",
                    label=f"Selected hour ({selected_hour}:00)")

    elif chart_type == "Pie":
        status_counts = pd.Series([f.status_label for f in hourly_forecasts]).value_counts()
        status_color_map = {f.status_label: f.status_color for f in hourly_forecasts}
        colors = [status_color_map[label] for label in status_counts.index]
        ax.pie(status_counts.values, labels=status_counts.index, autopct="%1.0f%%",
               colors=colors, wedgeprops={"edgecolor": THEME["fig_bg"]},
               textprops={"color": THEME["text"]})
        ax.set_title(f"Traffic condition split — {selected_day} (24h)", color=THEME["text"])

    if chart_type != "Pie":
        ax.set_xlabel("Hour of day", color=THEME["text"])
        ax.set_ylabel("Travel duration (minutes)", color=THEME["text"])
        ax.tick_params(colors=THEME["text"])
        for spine in ax.spines.values():
            spine.set_color(THEME["grid"])
        ax.grid(True, alpha=0.4, color=THEME["grid"])
        if chart_type in ("Line", "Scatter", "Area"):
            ax.legend(facecolor=THEME["fig_bg"], edgecolor=THEME["grid"], labelcolor=THEME["text"])

    st.pyplot(fig)

    st.info(
        f"Estimated travel time at **{selected_hour}:00** on **{selected_day}**: "
        f"**{selected_forecast.predicted_travel_mins} min** "
        f"(90% range: {selected_forecast.travel_mins_low}–{selected_forecast.travel_mins_high} min) "
        f"— {selected_forecast.status_label}"
    )

    st.markdown("---")
    st.subheader("Best Time to Leave (Trip Optimizer)")

    future_hours = [(selected_hour + i) % 24 for i in range(5)]
    trip_predictions = {h: ml_engine.predict(h, selected_day, origin_node, dest_node).predicted_travel_mins
                         for h in future_hours}

    best_hour = min(trip_predictions, key=trip_predictions.get)
    time_saved = round(trip_predictions[selected_hour] - trip_predictions[best_hour], 1)

    if best_hour == selected_hour or time_saved <= 2:
        st.success("Optimal departure time — leaving right now gives you the fastest route.")
    else:
        st.warning(
            f"If you delay your departure to **{best_hour}:00**, "
            f"you will save approximately **{time_saved} minutes** in congestion delay on this route."
        )

# ------------------------------------------
# TAB 3: PARKING AVAILABILITY
# ------------------------------------------
with tab3:
    st.subheader("Local parking hubs")

    st.dataframe(
        df_parking[["city", "location_name", "available_spots", "capacity", "occupancy_pct", "status"]],
        use_container_width=True,
        hide_index=True,
    )

    parking_forecast = ml_engine.predict(selected_hour, selected_day)
    st.info(
        f"Predicted city-wide parking occupancy at **{selected_hour}:00** on **{selected_day}**: "
        f"**{parking_forecast.predicted_parking_pct}% occupied**"
    )

# ==========================================
# AUTO-REFRESH
# ==========================================
if auto_refresh:
    st.caption("Auto-refresh is on — this page will update every 60 seconds.")
    time.sleep(60)
    st.rerun()