import requests
import time
import streamlit as st
import plotly.graph_objects as go
from requests.exceptions import RequestException
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
            if data and len(data) > 0:
                latest = data[0]
                rpm_value = latest.get("rpm")
                throttle_value = latest.get("throttle")
                if not isinstance(rpm_value, (int, float)):
                    rpm_value = 0
                if not isinstance(throttle_value, (int, float)):
                    throttle_value = 0
                return latest, rpm_value, throttle_value
    except RequestException:
        pass
    except ValueError:
        pass
    return None, 0, 0

st.set_page_config(page_title="Vehicle Telemetry Dashboard", layout="wide")

header_container = st.container()
with header_container:
    st.markdown(
        "<h1 style='text-align: center;'>Vehicle Telemetry Dashboard</h1>",
        unsafe_allow_html=True,
    )

st.sidebar.header("Connection Settings")
base_url = st.sidebar.text_input("Base API URL", "http://127.0.0.1:8000")
refresh_rate = st.sidebar.number_input("Refresh Rate (seconds)", min_value=1, value=5)

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

with st.container():
    st.subheader("Live Data")
    refresh_ms = max(int(refresh_rate * 1000), 1000)
    st_autorefresh(interval=refresh_ms, key="refresh")
    metric_placeholder = st.empty()
    indicator_placeholder = st.empty()
    timestamp_placeholder = st.empty()

    latest_data, rpm_value, throttle_value = get_latest_data(base_url)

    if latest_data is not None:
        speed_value = latest_data.get("speed_mph")
        if isinstance(speed_value, (int, float)):
            # Convert mph to km/h
            speed_kmh = speed_value * 1.60934
            display_speed = f"{speed_kmh:.1f}"
        else:
            display_speed = "N/A"
        metric_placeholder.metric(label="Speed (km/h)", value=display_speed)
        indicator_placeholder.markdown("✅ Connected")
        timestamp_placeholder.caption(f"Last update: {time.strftime('%H:%M:%S')}")
    else:
        metric_placeholder.metric(label="Speed (km/h)", value="—")
        indicator_placeholder.markdown("❌ Disconnected")
        timestamp_placeholder.caption("Last update: —")

    col1, col2 = st.columns(2)

    with col1:
        fig_rpm = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=rpm_value if latest_data is not None else 0,
                title={"text": "RPM"},
                gauge={
                    "axis": {"range": [0, 8000]},
                    "bar": {"color": "orange"},
                    "steps": [
                        {"range": [0, 3000], "color": "lightgreen"},
                        {"range": [3000, 6000], "color": "yellow"},
                        {"range": [6000, 8000], "color": "red"},
                    ],
                },
            )
        )
        st.plotly_chart(fig_rpm, use_container_width=True)

    with col2:
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

    with st.expander("Debug JSON"):
        if latest_data is not None:
            st.json(latest_data)
        else:
            st.write("No data received.")


with st.container():
    st.subheader("Trip Monitor")
    st.write("Coming soon...")

with st.container():
    st.subheader("System Status")
    st.write("Coming soon...")

footer_container = st.container()
with footer_container:
    st.markdown("<p style='text-align: center;'>© 2025 Vehicle Telemetry Dashboard</p>", unsafe_allow_html=True)
