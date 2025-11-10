"""Streamlit dashboard providing a gentle telemetry overview."""

from __future__ import annotations

import csv
from datetime import datetime
from typing import Dict, List

import pandas as pd
import streamlit as st

from data_manager import CSV_PATH, EXPECTED_HEADERS, get_latest_reading


st.set_page_config(layout="centered", page_title="Telemetry Dashboard")

DEFAULT_REFRESH_RATE = 5
MAX_HISTORY_ROWS = 180


@st.cache_data(ttl=DEFAULT_REFRESH_RATE)
def _load_history_from_csv(limit: int = MAX_HISTORY_ROWS) -> pd.DataFrame:
    """Return recent CSV samples as a tidy DataFrame for charts."""

    if not CSV_PATH.exists():
        return pd.DataFrame(columns=EXPECTED_HEADERS)

    rows: List[Dict[str, str]] = []
    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(row)

    if not rows:
        return pd.DataFrame(columns=EXPECTED_HEADERS)

    frame = pd.DataFrame(rows)
    frame = frame.tail(limit).reset_index(drop=True)

    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    numeric_columns = [
        "rpm",
        "coolant_temp_f",
        "vehicle_speed_mph",
        "throttle_position_pct",
        "engine_load_pct",
        "timing_advance_deg",
    ]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    return frame


def _build_cached_reader(ttl_seconds: int):
    """Create a cached function using the requested TTL."""

    @st.cache_data(ttl=ttl_seconds)
    def _inner(source: str) -> Dict[str, float | int | str]:
        return get_latest_reading(source=source)

    return _inner


def _format_timestamp(value: str | datetime | None) -> str:
    """Return a friendly timestamp string for headers and metrics."""

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return value
    return "No samples yet"


def _build_metric(label: str, value: float | int | None, suffix: str = "") -> None:
    """Render a compact metric widget with a safe default."""

    if value is None:
        display_value = "--"
    elif isinstance(value, float):
        display_value = f"{value:.1f}{suffix}"
    else:
        display_value = f"{value}{suffix}"
    st.metric(label, display_value)


# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
st.sidebar.header("Controls")
refresh_rate = st.sidebar.slider(
    "Refresh every (seconds)", min_value=2, max_value=15, value=DEFAULT_REFRESH_RATE
)
source_choice = st.sidebar.selectbox(
    "Data source", ("CSV history", "Live OBD adapter"), index=0
)
show_debug = st.sidebar.checkbox("Show Debug Panels", value=False)

source_key = "csv" if source_choice == "CSV history" else "obd"
read_latest = _build_cached_reader(refresh_rate)
latest_data = read_latest(source_key)

history_frame = _load_history_from_csv()

st.title("Vehicle Telemetry Dashboard")
st.caption("Clean layout tuned for phones and tablets.")

st.markdown("### Live Data")
cols = st.columns(3)
with cols[0]:
    _build_metric("RPM", latest_data.get("rpm"), suffix=" rpm")
with cols[1]:
    _build_metric("Speed", latest_data.get("vehicle_speed_mph"), suffix=" mph")
with cols[2]:
    _build_metric("Coolant", latest_data.get("coolant_temp_f"), suffix=" °F")

cols = st.columns(2)
with cols[0]:
    _build_metric("Throttle", latest_data.get("throttle_position_pct"), suffix=" %")
with cols[1]:
    _build_metric("Engine Load", latest_data.get("engine_load_pct"), suffix=" %")

st.markdown(f"Last sample: {_format_timestamp(latest_data.get('timestamp'))}")

st.markdown("<br>", unsafe_allow_html=True)

st.markdown("### Engine Health")
if history_frame.empty:
    st.info("No history yet. Start the logger to populate the charts.")
else:
    engine_cols = st.columns(2)
    with engine_cols[0]:
        st.line_chart(history_frame, x="timestamp", y="rpm", height=140)
    with engine_cols[1]:
        st.line_chart(history_frame, x="timestamp", y="coolant_temp_f", height=140)

st.markdown("<br>", unsafe_allow_html=True)

st.markdown("### Efficiency Metrics")
if history_frame.empty:
    st.info("Efficiency charts will appear after a few samples.")
else:
    efficiency_cols = st.columns(2)
    with efficiency_cols[0]:
        st.line_chart(history_frame, x="timestamp", y="throttle_position_pct", height=140)
    with efficiency_cols[1]:
        st.line_chart(history_frame, x="timestamp", y="engine_load_pct", height=140)

st.markdown("<br>", unsafe_allow_html=True)

st.markdown("### Trip Monitor")
trip_cols = st.columns(2)
with trip_cols[0]:
    _build_metric("Timing Advance", latest_data.get("timing_advance_deg"), suffix=" °")
with trip_cols[1]:
    _build_metric("Samples Stored", None if history_frame.empty else len(history_frame))

if not history_frame.empty:
    start_time = history_frame["timestamp"].min()
    st.write(
        f"Trip window: {_format_timestamp(start_time)} — {_format_timestamp(history_frame['timestamp'].max())}"
    )

st.markdown("<br>", unsafe_allow_html=True)

st.markdown("### History")
if history_frame.empty:
    st.info("History table will populate once data exists.")
else:
    st.dataframe(history_frame.tail(30), use_container_width=True)

if show_debug:
    with st.expander("Debug JSON"):
        st.write(latest_data)
    if not history_frame.empty:
        with st.expander("History Preview"):
            st.write(history_frame.tail(5))

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center; color:gray; font-size:12px;'>© 2025 Vehicle Telemetry Dashboard</p>",
    unsafe_allow_html=True,
)
