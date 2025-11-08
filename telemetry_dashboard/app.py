import streamlit as st
import requests

st.set_page_config(page_title="Vehicle Telemetry Dashboard", layout="wide")

st.title("Vehicle Telemetry Dashboard")

st.sidebar.header("Connection Settings")
base_url = st.sidebar.text_input("Base API URL", "http://127.0.0.1:8000")
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

st.subheader("Live Data")
st.write("Coming soon...")

st.subheader("Trip Monitor")
st.write("Coming soon...")

st.subheader("System Status")
st.write("Coming soon...")
