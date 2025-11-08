import requests
import time
import streamlit as st
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
                return data[0]  # Return the most recent reading
    except RequestException:
        pass
    except ValueError:
        pass
    return None

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

    latest_data = get_latest_data(base_url)

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
