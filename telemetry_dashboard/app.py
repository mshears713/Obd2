import streamlit as st
import requests

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
    except requests.RequestException as error:
        status_placeholder.error(f"Connection failed: {error}")
else:
    status_placeholder.info("Press the button to test the API.")

with st.container():
    st.subheader("Live Data")
    st.write("Coming soon...")

with st.container():
    st.subheader("Trip Monitor")
    st.write("Coming soon...")

with st.container():
    st.subheader("System Status")
    st.write("Coming soon...")

footer_container = st.container()
with footer_container:
    st.markdown("<p style='text-align: center;'>© 2025 Vehicle Telemetry Dashboard</p>", unsafe_allow_html=True)
