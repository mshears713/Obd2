import time
from typing import Dict, Optional, Tuple

import pandas as pd
import requests
import streamlit as st
from requests.exceptions import RequestException
import plotly.graph_objects as go
try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:  # Fallback if the helper is unavailable
    def st_autorefresh(*_, **__):
        return None


st.set_page_config(layout="centered", page_title="Telemetry Dashboard")

tv_mode = st.sidebar.toggle("🖥️ TV Mode", value=False)

if tv_mode:
    gauge_height = 350
    font_size = "22px"
    chart_height = 250
    padding = "<br><br>"
else:
    gauge_height = 200
    font_size = "16px"
    chart_height = 150
    padding = "<br>"

if "refresh_ttl" not in st.session_state:
    st.session_state.refresh_ttl = 3


REFRESH_TTL = max(2, int(st.session_state.refresh_ttl))


@st.cache_data(ttl=REFRESH_TTL, show_spinner=False)
def get_latest_data(base_url: str) -> Tuple[Optional[Dict[str, float]], float, float, Optional[float], Optional[float], Optional[float], Optional[float]]:
    try:
        response = requests.get(f"{base_url.rstrip('/')}/readings?limit=1", timeout=5)
        if response.ok:
            data = response.json()
            latest: Optional[Dict[str, float]] = None
            if isinstance(data, dict):
                latest = data
            elif isinstance(data, list) and len(data) > 0:
                latest = data[0]

            if isinstance(latest, dict):
                rpm_value = latest.get("rpm")
                throttle_value = latest.get("throttle_pct")
                engine_load_value = latest.get("load_pct")
                coolant_temp_value = latest.get("coolant_temp_f")
                maf_value = latest.get("maf_gps")
                speed_value = latest.get("speed_mph")

                if not isinstance(coolant_temp_value, (int, float)):
                    coolant_temp_value = latest.get("coolant_temp")

                if not isinstance(speed_value, (int, float)):
                    speed_value = latest.get("speed")

                if not isinstance(rpm_value, (int, float)):
                    rpm_value = 0
                if not isinstance(throttle_value, (int, float)):
                    throttle_value = 0
                if isinstance(engine_load_value, (int, float)):
                    engine_load_value = float(engine_load_value)
                else:
                    engine_load_value = None
                if isinstance(coolant_temp_value, (int, float)):
                    coolant_temp_value = float(coolant_temp_value)
                else:
                    coolant_temp_value = None
                if isinstance(maf_value, (int, float)):
                    maf_value = float(maf_value)
                else:
                    maf_value = None
                if isinstance(speed_value, (int, float)):
                    speed_value = float(speed_value)
                else:
                    speed_value = None

                return (
                    latest,
                    float(rpm_value),
                    float(throttle_value),
                    engine_load_value,
                    coolant_temp_value,
                    maf_value,
                    speed_value,
                )
    except RequestException:
        pass
    except ValueError:
        pass
    return None, 0.0, 0.0, None, None, None, None


@st.cache_data(ttl=120, show_spinner=False)
def get_range_data(base_url: str, minutes: int) -> Optional[pd.DataFrame]:
    try:
        resp = requests.get(f"{base_url.rstrip('/')}/range?minutes={minutes}", timeout=5)
        if resp.status_code == 200:
            return pd.DataFrame(resp.json())
        return None
    except RequestException:
        return None


def get_live_obd_data() -> Tuple[Optional[Dict[str, float]], float, float, Optional[float], Optional[float], Optional[float], Optional[float]]:
    try:
        from data_manager import get_latest_reading
    except ImportError as error:
        raise RuntimeError("Local OBD helper is missing. Install python-OBD utilities on the Pi.") from error

    try:
        reading = get_latest_reading("obd")
    except RuntimeError as error:
        raise RuntimeError("Live adapter unavailable. Plug in the adapter and install python-OBD.") from error
    except ValueError as error:
        raise RuntimeError("Live adapter unsupported in the current data helper.") from error

    if not isinstance(reading, dict):
        raise RuntimeError("Live adapter returned unexpected data.")

    rpm_value = reading.get("rpm", 0)
    throttle_value = reading.get("throttle_position_pct") or reading.get("throttle_pct") or 0
    engine_load_value = reading.get("engine_load_pct") or reading.get("load_pct")
    coolant_temp_value = reading.get("coolant_temp_f") or reading.get("coolant_temp")
    maf_value = reading.get("maf_gps")
    speed_value = (
        reading.get("vehicle_speed_mph")
        or reading.get("speed_mph")
        or reading.get("speed")
    )

    rpm_number = float(rpm_value) if isinstance(rpm_value, (int, float)) else 0.0
    throttle_number = float(throttle_value) if isinstance(throttle_value, (int, float)) else 0.0
    engine_load = float(engine_load_value) if isinstance(engine_load_value, (int, float)) else None
    coolant_temp = float(coolant_temp_value) if isinstance(coolant_temp_value, (int, float)) else None
    maf_amount = float(maf_value) if isinstance(maf_value, (int, float)) else None
    speed_number = float(speed_value) if isinstance(speed_value, (int, float)) else None

    return (
        reading,
        rpm_number,
        throttle_number,
        engine_load,
        coolant_temp,
        maf_amount,
        speed_number,
    )


if "trip_active" not in st.session_state:
    st.session_state.trip_active = False
if "trip_start_time" not in st.session_state:
    st.session_state.trip_start_time = None
if "trip_data" not in st.session_state:
    st.session_state.trip_data = []
if "distance_miles" not in st.session_state:
    st.session_state.distance_miles = 0.0

st.markdown(
    f"<h1 style='text-align:center; font-size:{font_size};'>🚗 Vehicle Telemetry Dashboard</h1>",
    unsafe_allow_html=True,
)

if tv_mode:
    st.success("TV Mode Active — Display optimized for large screens.")

st.markdown(padding, unsafe_allow_html=True)

# Main page OBD status indicator
try:
    status_response = requests.get(f"http://127.0.0.1:8000/obd/status", timeout=2)
    if status_response.ok:
        status_data = status_response.json()
        if status_data.get("mode") == "real":
            st.markdown(
                "<div style='text-align:center; padding: 10px; background: linear-gradient(90deg, #00ff00, #00cc00); border-radius: 10px; margin: 10px auto; max-width: 400px;'>"
                "<strong style='color: #000; font-size: 18px;'>🟢 LIVE DATA FROM VEHICLE</strong>"
                f"<br><span style='color: #003300; font-size: 12px;'>Protocol: {status_data.get('protocol', 'Unknown')}</span>"
                "</div>",
                unsafe_allow_html=True
            )
        elif status_data.get("mode") == "simulated":
            st.markdown(
                "<div style='text-align:center; padding: 10px; background: linear-gradient(90deg, #ffaa00, #ff8800); border-radius: 10px; margin: 10px auto; max-width: 400px;'>"
                "<strong style='color: #000; font-size: 18px;'>🟡 SIMULATED DATA</strong>"
                "<br><span style='color: #331100; font-size: 12px;'>OBD adapter not connected</span>"
                "</div>",
                unsafe_allow_html=True
            )
except:
    pass

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(padding, unsafe_allow_html=True)

st.sidebar.header("Connection Settings")
base_url = st.sidebar.text_input("Base API URL", "http://127.0.0.1:8000")
refresh_rate = st.sidebar.number_input("Refresh Rate (seconds)", min_value=2, value=3, step=1)
st.session_state.refresh_ttl = max(2, int(refresh_rate))

st.sidebar.subheader("Data Source")
data_source = st.sidebar.selectbox(
    "Live data source",
    ("FastAPI (network)", "Live OBD adapter"),
    help="Use FastAPI while developing without the adapter.",
)
show_debug = st.sidebar.checkbox("Show Debug Panels")

st.sidebar.subheader("Backend")
check_health = st.sidebar.button("Check /health")
status_placeholder = st.sidebar.empty()

if data_source == "FastAPI (network)" and check_health:
    try:
        response = requests.get(f"{base_url.rstrip('/')}/health", timeout=5)
        if response.ok:
            status_placeholder.success("API is reachable.")
        else:
            status_placeholder.error(f"API responded with status {response.status_code}.")
    except RequestException as error:
        status_placeholder.error(f"Connection failed: {error}")
elif data_source == "FastAPI (network)":
    status_placeholder.info("Press the button to test the API.")

# OBD Connection Status
st.sidebar.markdown("---")
st.sidebar.subheader("OBD Connection")

# Get OBD status
obd_status = None
try:
    response = requests.get(f"{base_url.rstrip('/')}/obd/status", timeout=5)
    if response.ok:
        obd_status = response.json()
except:
    pass

# Display status
if obd_status:
    if obd_status.get("mode") == "real":
        st.sidebar.success("🟢 Real OBD Data")
        if obd_status.get("protocol"):
            st.sidebar.caption(f"Protocol: {obd_status['protocol']}")
    elif obd_status.get("mode") == "simulated":
        st.sidebar.warning("🟡 Simulated Data")
        st.sidebar.caption("OBD adapter not connected")
    else:
        st.sidebar.error("🔴 Status Unknown")
else:
    st.sidebar.info("Status unavailable")

# Reconnect button
if st.sidebar.button("🔄 Reconnect to OBD"):
    with st.spinner("Attempting to reconnect..."):
        try:
            response = requests.post(f"{base_url.rstrip('/')}/obd/reconnect", timeout=15)
            if response.ok:
                result = response.json()
                if result.get("success"):
                    st.sidebar.success(result.get("message", "Reconnected!"))
                    time.sleep(1)
                    st.rerun()
                else:
                    st.sidebar.error(result.get("message", "Reconnection failed"))
            else:
                st.sidebar.error("Reconnection request failed")
        except Exception as e:
            st.sidebar.error(f"Error: {str(e)}")
else:
    status_placeholder.info("OBD checks run locally on the Pi.")

live_container = st.container()

refresh_ms = max(int(refresh_rate * 1000), 2000)
st_autorefresh(interval=refresh_ms, key="refresh")

empty_reading = (None, 0.0, 0.0, None, None, None, None)
data_error: Optional[str] = None

if data_source == "FastAPI (network)":
    (
        latest_data,
        rpm_value,
        throttle_value,
        engine_load_value,
        coolant_temp_value,
        maf_value,
        speed_value,
    ) = get_latest_data(base_url)
else:
    try:
        (
            latest_data,
            rpm_value,
            throttle_value,
            engine_load_value,
            coolant_temp_value,
            maf_value,
            speed_value,
        ) = get_live_obd_data()
    except RuntimeError as error:
        data_error = str(error)
    except Exception as error:  # Fallback for unexpected issues
        data_error = f"Live adapter error: {error}"
        (
            latest_data,
            rpm_value,
            throttle_value,
            engine_load_value,
            coolant_temp_value,
            maf_value,
            speed_value,
        ) = empty_reading

with live_container:
    st.markdown("### Live Data")

    if data_error:
        st.error(data_error)

    source_label = "FastAPI" if data_source == "FastAPI (network)" else "Live OBD"
    if latest_data is not None and isinstance(speed_value, (int, float)):
        speed_kmh = speed_value * 1.60934
        speed_display = f"{speed_kmh:.1f}"
        mph_display = f"{speed_value:.1f}"
    else:
        speed_display = "—"
        mph_display = "—"

    if isinstance(latest_data, dict) and latest_data.get("timestamp"):
        timestamp_display = str(latest_data.get("timestamp"))
    elif latest_data is not None:
        timestamp_display = time.strftime("%H:%M:%S")
    else:
        timestamp_display = "—"

    if latest_data is not None:
        status_display = "✅ Connected"
    elif data_error:
        status_display = "⚠️ Adapter issue"
    else:
        status_display = "⏳ Waiting"

    st.markdown(
        f"""
        <div style='text-align: center; background: linear-gradient(135deg, rgba(46,139,87,0.35), rgba(14,17,23,0.95));
                    border-radius: 16px; padding: 16px; margin: 10px 0;
                    box-shadow: 0 6px 20px rgba(0,0,0,0.35); font-size: {font_size};'>
            <div style='color: #8EF9D0; font-family: "Orbitron", monospace; font-size: 0.75em;
                        text-transform: uppercase; letter-spacing: 2px; margin-bottom: 8px;'>
                🏁 Speed Telemetry
            </div>
            <div style='display: flex; justify-content: center; gap: 24px; align-items: center;'>
                <div>
                    <div style='color: #FAFAFA; font-size: 40px; font-weight: bold;'>
                        {speed_display}
                    </div>
                    <div style='color: #8EF9D0; font-size: 14px;'>KM/H</div>
                </div>
                <div style='border-left: 1px solid rgba(143, 249, 208, 0.4); padding-left: 16px;'>
                    <div style='color: #FAFAFA; font-size: 1.2em; font-weight: bold;'>
                        {mph_display}
                    </div>
                    <div style='color: #8EF9D0; font-size: 0.75em;'>MPH</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(padding, unsafe_allow_html=True)

    gauge_col_left, gauge_col_right = st.columns(2)

    with gauge_col_left:
        # Digital LED-Style RPM Display
        rpm_display_value = rpm_value if latest_data is not None else 0
        rpm_color = "#ff0000" if rpm_display_value > 2000 else "#ffff00" if rpm_display_value > 1000 else "#00ff00"
        rpm_blocks = max(0, min(10, int(rpm_display_value / 250)))

        st.markdown(
            f"""
            <div style='text-align: center; background: rgba(14,17,23,0.9); border: 2px solid {rpm_color};
                        border-radius: 12px; padding: 16px; margin: 10px 0;
                        box-shadow: 0 8px 16px rgba(0,0,0,0.35);'>
                <div style='color: {rpm_color}; font-family: "Digital-7", monospace;
                            font-size: {1.8 if tv_mode else 1.4}em; font-weight: bold;
                            letter-spacing: 3px;'>
                    {rpm_display_value:04.0f}
                </div>
                <div style='color: {rpm_color}; font-size: {1.0 if tv_mode else 0.85}em; font-family: "Orbitron", monospace;
                            letter-spacing: 2px; margin-top: 5px;'>
                    ▲ RPM ▲
                </div>
                <div style='margin-top: 10px;'>
                    {'🔴' * rpm_blocks + '⚫' * (10 - rpm_blocks)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with gauge_col_right:
        # Classic Speedometer-Style Throttle Gauge
        fig_throttle = go.Figure(
            go.Indicator(
                mode="gauge+number+delta",
                value=throttle_value if latest_data is not None else 0,
                title={"text": "Throttle Position", "font": {"size": 18, "color": "white"}},
                number={"font": {"size": 28, "color": "white"}},
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 2, "tickcolor": "white"},
                    "bar": {"color": "rgba(255, 255, 255, 0.8)", "thickness": 0.8},
                    "bgcolor": "rgba(0, 0, 0, 0.8)",
                    "borderwidth": 3,
                    "bordercolor": "gold",
                    "steps": [
                        {"range": [0, 25], "color": "rgba(0, 255, 0, 0.3)"},
                        {"range": [25, 50], "color": "rgba(255, 255, 0, 0.3)"},
                        {"range": [50, 75], "color": "rgba(255, 165, 0, 0.3)"},
                        {"range": [75, 100], "color": "rgba(255, 0, 0, 0.3)"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 90,
                    },
                },
            )
        )
        fig_throttle.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "white", "family": "Arial Black"},
            height=gauge_height,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(fig_throttle, use_container_width=True)

st.markdown(padding, unsafe_allow_html=True)

engine_container = st.container()

with engine_container:
    st.markdown("### Engine Health")

    load_display = "N/A"
    load_progress = 0
    coolant_display = "N/A"
    coolant_state = "<span style='color:gray;'>N/A</span>"
    note_message = "Data unavailable."

    if latest_data is not None:
        if isinstance(engine_load_value, (int, float)):
            load_display = f"{engine_load_value:.1f}%"
            load_progress = int(max(0, min(engine_load_value, 100)))

        if isinstance(coolant_temp_value, (int, float)):
            if coolant_temp_value < 160:
                coolant_state = "<span style='color:blue;'>🧊 Cool</span>"
                note_message = "Engine warming up."
            elif coolant_temp_value <= 210:
                coolant_state = "<span style='color:green;'>✅ Normal</span>"
                note_message = "Engine operating normally."
            else:
                coolant_state = "<span style='color:red;'>🔥 Hot</span>"
                note_message = "Monitor cooling system."
            coolant_display = f"{coolant_temp_value:.1f}°F"

    engine_metrics = st.columns(2)
    engine_metrics[0].metric("Engine Load", load_display)
    engine_metrics[1].metric("Coolant Temp", coolant_display if coolant_display != "N/A" else "N/A")
    st.progress(load_progress)

    if coolant_display != "N/A":
        st.markdown(coolant_state, unsafe_allow_html=True)

    st.caption(note_message)

st.markdown(padding, unsafe_allow_html=True)

efficiency_container = st.container()

with efficiency_container:
    st.markdown("### Efficiency Metrics")

    maf_for_display = maf_value if isinstance(maf_value, (int, float)) else 0.0
    maf_progress = int(max(0, min((maf_for_display / 20) * 100, 100)))

    mpg_display = "N/A"
    status_color = "gray"
    status_note = "Data needed"
    mpg_est = 0.0

    if (
        isinstance(maf_value, (int, float))
        and maf_value > 0
        and isinstance(speed_value, (int, float))
    ):
        mpg_est = speed_value / (maf_value * 0.08)
        mpg_display = f"{mpg_est:.1f}"
        if mpg_est > 30:
            status_color = "green"
            status_note = "Efficient"
        elif mpg_est >= 15:
            status_color = "orange"
            status_note = "Average"
        else:
            status_color = "red"
            status_note = "Inefficient"

    efficiency_metrics = st.columns(2)
    airflow_display = f"{maf_for_display:.2f}" if isinstance(maf_value, (int, float)) else "N/A"
    efficiency_metrics[0].metric("Mass Airflow (g/s)", airflow_display)
    efficiency_metrics[1].metric("Estimated MPG", mpg_display)
    st.progress(maf_progress)

    st.markdown(
        f"<span style='color:{status_color};'>Status: {status_note}</span>",
        unsafe_allow_html=True,
    )

    if show_debug:
        with st.expander("Efficiency Debug"):
            speed_debug = (
                f"{speed_value:.1f}" if isinstance(speed_value, (int, float)) else "N/A"
            )
            maf_debug = (
                f"{maf_for_display:.2f}" if isinstance(maf_value, (int, float)) else "N/A"
            )
            mpg_debug = f"{mpg_est:.1f}" if mpg_est > 0 else "N/A"
            st.write(f"Speed (mph): {speed_debug}")
            st.write(f"Mass Airflow (g/s): {maf_debug}")
            st.write(f"Estimated MPG: {mpg_debug}")

st.markdown(padding, unsafe_allow_html=True)

trip_container = st.container()

with trip_container:
    st.markdown("### Trip Monitor")

    col1, col2, col3 = st.columns(3)
    start = col1.button("▶️ Start Trip")
    stop = col2.button("⏹️ Stop Trip")
    reset = col3.button("🔄 Reset")

    if start and not st.session_state.trip_active:
        st.session_state.trip_active = True
        st.session_state.trip_start_time = time.time()
    if stop and st.session_state.trip_active:
        st.session_state.trip_active = False
    if reset:
        st.session_state.trip_active = False
        st.session_state.trip_start_time = None
        st.session_state.trip_data = []
        st.session_state.distance_miles = 0.0

    current_time = time.time()
    if st.session_state.trip_active and isinstance(speed_value, (int, float)):
        st.session_state.trip_data.append((current_time, speed_value))
        st.session_state.trip_data = st.session_state.trip_data[-300:]
        st.session_state.distance_miles += (speed_value / 3600.0) * refresh_rate

    elapsed_seconds = 0.0
    if st.session_state.trip_start_time is not None:
        if st.session_state.trip_active:
            elapsed_seconds = current_time - st.session_state.trip_start_time
        elif st.session_state.trip_data:
            last_time = st.session_state.trip_data[-1][0]
            elapsed_seconds = last_time - st.session_state.trip_start_time

    elapsed_minutes = int(elapsed_seconds // 60)
    elapsed_remain = int(elapsed_seconds % 60)
    elapsed_display = f"{elapsed_minutes:02d}:{elapsed_remain:02d}"

    avg_speed = 0.0
    if st.session_state.trip_data:
        speeds = [speed for _, speed in st.session_state.trip_data]
        avg_speed = sum(speeds) / len(speeds)

    metric_cols = st.columns(3)
    metric_cols[0].metric("Elapsed Time", elapsed_display)
    metric_cols[1].metric("Distance (mi)", f"{st.session_state.distance_miles:.1f}")
    metric_cols[2].metric("Avg Speed (mph)", f"{avg_speed:.1f}")

    if st.session_state.trip_data:
        df = pd.DataFrame(st.session_state.trip_data, columns=["time", "speed"])
        df["time"] = pd.to_datetime(df["time"], unit="s")

        fig_speed_history = go.Figure()
        fig_speed_history.add_trace(
            go.Scatter(
                x=df["time"],
                y=df["speed"],
                mode="lines",
                name="Speed",
                line=dict(color="#00ffff", width=2)
            )
        )
        fig_speed_history.update_layout(
            title="Speed History",
            xaxis_title="Time",
            yaxis_title="Speed (mph)",
            yaxis=dict(
                range=[0, 88],
                dtick=10,
                gridcolor="rgba(255,255,255,0.2)",
                showgrid=True
            ),
            xaxis=dict(
                gridcolor="rgba(255,255,255,0.1)",
                showgrid=True
            ),
            height=chart_height,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0.1)",
            font=dict(color="white"),
            showlegend=False,
            margin=dict(l=50, r=20, t=40, b=40)
        )
        st.plotly_chart(fig_speed_history, use_container_width=True)
    else:
        st.caption("Start a trip to see recent speed history.")

st.markdown(padding, unsafe_allow_html=True)
st.markdown("### History")
timeframe = st.selectbox("Select Time Range", ["Last 5 min", "Last 15 min", "Last 30 min", "Last 60 min"])
window_minutes = int(timeframe.split()[1])

history_df = get_range_data(base_url, window_minutes)

if history_df is not None and not history_df.empty:
    if "speed" not in history_df.columns and "speed_mph" in history_df.columns:
        history_df["speed"] = history_df["speed_mph"]
    if "coolant_temp_f" not in history_df.columns and "coolant_temp" in history_df.columns:
        history_df["coolant_temp_f"] = history_df["coolant_temp"]

    required_columns = {"timestamp", "speed", "rpm", "coolant_temp_f"}

    if required_columns.issubset(history_df.columns):
        history_df["timestamp"] = pd.to_datetime(history_df["timestamp"])
        history_df.set_index("timestamp", inplace=True)

        st.line_chart(history_df["speed"], height=chart_height)
        st.line_chart(history_df["rpm"], height=chart_height)
        st.line_chart(history_df["coolant_temp_f"], height=chart_height)
    else:
        st.warning("No data available for this range.")
else:
    st.warning("No data available for this range.")

st.markdown(padding, unsafe_allow_html=True)

if show_debug:
    with st.expander("Debug JSON"):
        if latest_data is not None:
            st.json(latest_data)
        else:
            st.write("No data received.")

st.markdown(padding, unsafe_allow_html=True)

# Data Source and Status at bottom
st.markdown("---")
status_cols = st.columns([1, 1, 1])
status_cols[0].metric("Source", source_label)
status_cols[1].metric("Status", status_display)
status_cols[2].metric("Last Update", timestamp_display)

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center; color:gray; font-size:12px;'>© 2025 Vehicle Telemetry Dashboard</p>",
    unsafe_allow_html=True,
)
