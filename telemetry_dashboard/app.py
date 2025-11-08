import time

import requests
from requests.exceptions import RequestException
import streamlit as st
import plotly.graph_objects as go
try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:  # Fallback if the helper is unavailable
    def st_autorefresh(*_, **__):
        return None


def get_latest_data(base_url: str):
    try:
        response = requests.get(f"{base_url.rstrip('/')}/readings?limit=1", timeout=5)
        if response.ok:
            data = response.json()
            latest = None
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

                # engine_load_value already set to load_pct above

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
                    rpm_value,
                    throttle_value,
                    engine_load_value,
                    coolant_temp_value,
                    maf_value,
                    speed_value,
                )
    except RequestException:
        pass
    except ValueError:
        pass
    return None, 0, 0, None, None, None, None

st.set_page_config(page_title="Vehicle Telemetry Dashboard", layout="wide")

st.markdown(
    "<h1 style='text-align:center;'>🚗 Vehicle Telemetry Dashboard</h1>",
    unsafe_allow_html=True,
)
st.markdown("---")

st.sidebar.header("Connection Settings")
base_url = st.sidebar.text_input("Base API URL", "http://127.0.0.1:8000")
refresh_rate = st.sidebar.number_input("Refresh Rate (seconds)", min_value=1, value=3)

st.sidebar.subheader("Backend")
check_health = st.sidebar.button("Check /health")
status_placeholder = st.sidebar.empty()

if check_health:
    try:
        response = requests.get(f"{base_url.rstrip('/')}/health", timeout=5)
        if response.ok:
            status_placeholder.success("API is reachable.")
        else:
            status_placeholder.error(f"API responded with status {response.status_code}.")
    except RequestException as error:
        status_placeholder.error(f"Connection failed: {error}")
else:
    status_placeholder.info("Press the button to test the API.")

live_container = st.container()

refresh_ms = max(int(refresh_rate * 1000), 1000)
st_autorefresh(interval=refresh_ms, key="refresh")

(
    latest_data,
    rpm_value,
    throttle_value,
    engine_load_value,
    coolant_temp_value,
    maf_value,
    speed_value,
) = get_latest_data(base_url)

with live_container:
    st.markdown("### Live Data")

    if latest_data is not None and isinstance(speed_value, (int, float)):
        speed_kmh = speed_value * 1.60934
        speed_display = f"{speed_kmh:.1f}"
    else:
        speed_display = "—"

    connection_text = "✅ Connected" if latest_data is not None else "❌ Disconnected"
    timestamp_text = (
        f"Last update: {time.strftime('%H:%M:%S')}"
        if latest_data is not None
        else "Last update: —"
    )

    status_cols = st.columns([1, 1])
    with status_cols[0]:
        st.markdown(connection_text)
    with status_cols[1]:
        st.caption(timestamp_text)

    speed_cols = st.columns([1, 1, 1])
    with speed_cols[1]:
        st.metric(label="Speed (km/h)", value=speed_display)

    gauge_col_left, gauge_col_right = st.columns(2)

    with gauge_col_left:
        fig_rpm = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=rpm_value if latest_data is not None else 0,
                title={"text": "RPM"},
                gauge={
                    "axis": {"range": [0, 2500]},
                    "bar": {"color": "orange"},
                    "steps": [
                        {"range": [0, 1000], "color": "lightgreen"},
                        {"range": [1000, 2000], "color": "yellow"},
                        {"range": [2000, 2500], "color": "red"},
                    ],
                },
            )
        )
        st.plotly_chart(fig_rpm, use_container_width=True)

    with gauge_col_right:
        fig_throttle = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=throttle_value if latest_data is not None else 0,
                title={"text": "Throttle (%)"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "skyblue"},
                },
            )
        )
        st.plotly_chart(fig_throttle, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

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

    st.write(f"Engine Load: {load_display}")
    st.progress(load_progress)

    if coolant_display != "N/A":
        st.markdown(
            f"**Coolant Temp:** {coolant_display} — {coolant_state}",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("**Coolant Temp:** N/A", unsafe_allow_html=True)

    st.caption(note_message)

st.markdown("<br>", unsafe_allow_html=True)

efficiency_container = st.container()

with efficiency_container:
    st.markdown("### Efficiency Metrics")

    maf_for_display = maf_value if isinstance(maf_value, (int, float)) else 0.0
    maf_progress = int(max(0, min((maf_for_display / 20) * 100, 100)))

    if isinstance(maf_value, (int, float)):
        st.write(f"Mass Airflow: {maf_for_display:.2f} g/s")
    else:
        st.write("Mass Airflow: N/A")
    st.progress(maf_progress)

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

    st.metric(label="Estimated MPG", value=mpg_display)
    st.markdown(
        f"<span style='color:{status_color};'>Status: {status_note}</span>",
        unsafe_allow_html=True,
    )

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

st.markdown("<br>", unsafe_allow_html=True)

with st.expander("Debug JSON"):
    if latest_data is not None:
        st.json(latest_data)
    else:
        st.write("No data received.")

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center; font-size:12px;'>© 2025 Vehicle Telemetry Dashboard</p>",
    unsafe_allow_html=True,
)
