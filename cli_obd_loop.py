#!/usr/bin/env python3
"""
Tiny, standalone CLI OBD reading loop.
Prints one JSON dictionary per second to stdout.

WHAT THIS DOES:
- Connects to your car's OBD-II adapter via /dev/rfcomm0
- Reads engine sensors (RPM, speed, coolant temp, throttle, load, MAF)
- Outputs one JSON line per second
- Falls back to simulation mode if adapter is not detected

HOW TO RUN:
    python3 cli_obd_loop.py

    Or make it executable:
    chmod +x cli_obd_loop.py
    ./cli_obd_loop.py

SIMULATION MODE:
- Triggers automatically if /dev/rfcomm0 is not found or python-obd is missing
- Prints a [warning] message at startup
- Generates realistic fake sensor values for testing

REQUIREMENTS:
    pip3 install obd pyserial --break-system-packages

    Then bind your Bluetooth ELM327 adapter:
    sudo rfcomm bind 0 00:1D:A5:09:2E:B3 1
"""

import json
import math
import os
import sys
import time
from datetime import datetime, timezone
import requests


# ---------------------------------------------------------------------------
# Helper function: Read a snapshot of OBD sensor data
# ---------------------------------------------------------------------------

def read_obd_snapshot(connection) -> dict:
    """
    Read current sensor values from the OBD connection.

    Returns a dictionary with normalized units:
    - timestamp: ISO8601 UTC string
    - rpm: int (revolutions per minute)
    - speed_mph: float (miles per hour)
    - coolant_temp_f: float (degrees Fahrenheit)
    - throttle_pct: float (percent, 0-100)
    - load_pct: float (calculated engine load, percent)
    - maf_gps: float (mass air flow, grams per second)

    If a sensor is unavailable, its value will be None.
    Never crashes the loop - handles all errors gracefully.
    """

    # If connection is None, we're in simulation mode
    if connection is None:
        return _generate_fake_snapshot()

    # Try to import obd module (should already be imported, but defensive)
    try:
        import obd
    except ImportError:
        # Shouldn't happen if connection exists, but be safe
        return _generate_fake_snapshot()

    # Helper: safely query a PID and return the raw value
    def safe_query(command):
        """Query a PID and return value or None if failed."""
        try:
            response = connection.query(command)
            if response is None or response.is_null():
                return None
            return response.value
        except Exception:
            # Silently handle query failures (adapter might be dropped)
            return None

    # Helper: extract numeric magnitude from pint Quantity objects
    def get_magnitude(value, target_unit=None):
        """
        Extract numeric value from OBD response.
        Optionally convert to target_unit (e.g., 'km/h', 'degC').
        Returns None if value is missing or conversion fails.
        """
        if value is None:
            return None

        # Convert to target unit if requested
        converted = value
        if target_unit is not None and hasattr(value, 'to'):
            try:
                converted = value.to(target_unit)
            except Exception:
                # Unit conversion failed, use original
                converted = value

        # Extract the numeric magnitude
        if hasattr(converted, 'magnitude'):
            return converted.magnitude

        # Fallback: try to cast to float
        try:
            return float(converted)
        except (TypeError, ValueError):
            return None

    # Query all PIDs
    rpm_value = safe_query(obd.commands.RPM)
    speed_value = safe_query(obd.commands.SPEED)
    coolant_value = safe_query(obd.commands.COOLANT_TEMP)
    throttle_value = safe_query(obd.commands.THROTTLE_POS)
    load_value = safe_query(obd.commands.ENGINE_LOAD)
    maf_value = safe_query(obd.commands.MAF)

    # Extract and normalize values

    # RPM: convert to int
    rpm_raw = get_magnitude(rpm_value)
    rpm = int(rpm_raw) if rpm_raw is not None else None

    # Speed: convert km/h to mph
    speed_kmh = get_magnitude(speed_value, 'km/h')
    speed_mph = round(speed_kmh * 0.621371, 1) if speed_kmh is not None else None

    # Coolant temp: convert Celsius to Fahrenheit
    coolant_c = get_magnitude(coolant_value, 'degC')
    coolant_temp_f = round((coolant_c * 9/5) + 32, 1) if coolant_c is not None else None

    # Throttle: percent (already correct unit)
    throttle_raw = get_magnitude(throttle_value, 'percent')
    throttle_pct = round(throttle_raw, 1) if throttle_raw is not None else None

    # Engine load: percent (already correct unit)
    load_raw = get_magnitude(load_value, 'percent')
    load_pct = round(load_raw, 1) if load_raw is not None else None

    # MAF: grams per second (already correct unit)
    maf_raw = get_magnitude(maf_value, 'grams_per_second')
    maf_gps = round(maf_raw, 2) if maf_raw is not None else None

    # Build the snapshot dictionary
    snapshot = {
        'timestamp': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'rpm': rpm,
        'speed_mph': speed_mph,
        'coolant_temp_f': coolant_temp_f,
        'throttle_pct': throttle_pct,
        'load_pct': load_pct,
        'maf_gps': maf_gps,
    }

    return snapshot


# ---------------------------------------------------------------------------
# Simulation mode: generate fake but realistic sensor values
# ---------------------------------------------------------------------------

def _generate_fake_snapshot() -> dict:
    """
    Generate a simulated OBD snapshot with realistic values.
    Used when OBD adapter is not available.
    """

    # Use time-based sine waves to create realistic variation
    t = time.time()

    # RPM: oscillate between 750-1100 (realistic idle fluctuation)
    rpm = int(925 + 175 * math.sin(t * 0.5))

    # Speed: slow oscillation 0-45 mph
    speed_mph = round(22.5 + 22.5 * math.sin(t * 0.2), 1)

    # Coolant temp: warm engine, slight variation
    coolant_temp_f = round(185 + 5 * math.sin(t * 0.1), 1)

    # Throttle: gentle variation 0-25%
    throttle_pct = round(12.5 + 12.5 * math.sin(t * 0.7), 1)

    # Engine load: correlates with throttle
    load_pct = round(15 + 10 * math.sin(t * 0.7), 1)

    # MAF: correlates with RPM and load
    maf_gps = round(5 + 3 * math.sin(t * 0.5), 2)

    snapshot = {
        'timestamp': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'rpm': rpm,
        'speed_mph': speed_mph,
        'coolant_temp_f': coolant_temp_f,
        'throttle_pct': throttle_pct,
        'load_pct': load_pct,
        'maf_gps': maf_gps,
    }

    return snapshot


# ---------------------------------------------------------------------------
# OBD connection setup
# ---------------------------------------------------------------------------

def connect_to_obd():
    """
    Attempt to connect to the OBD-II adapter at /dev/rfcomm0.

    Returns:
        - OBD connection object if successful
        - None if adapter not found or connection failed (triggers simulation mode)
    """

    # Check if the serial device exists
    device_path = '/dev/rfcomm0'
    if not os.path.exists(device_path):
        print('[warning] OBD adapter not detected — using simulation mode',
              file=sys.stderr)
        print(f'[info] To connect real adapter: sudo rfcomm bind 0 00:1D:A5:09:2E:B3 1',
              file=sys.stderr)
        return None

    # Try to import python-OBD
    try:
        import obd
    except ImportError:
        print('[warning] python-OBD not installed — using simulation mode',
              file=sys.stderr)
        print('[info] Install with: pip3 install obd pyserial --break-system-packages',
              file=sys.stderr)
        return None

    # Try to connect to the adapter
    try:
        print(f'[info] Connecting to OBD-II adapter at {device_path}...',
              file=sys.stderr)

        # fast=True skips full protocol search (quicker connection)
        # If connection fails, try fast=False for full protocol search
        connection = obd.OBD(device_path, fast=True, timeout=5)

        # Check connection status
        status = connection.status()

        if status == obd.OBDStatus.CAR_CONNECTED:
            protocol = connection.protocol_name() or 'unknown'
            print(f'[info] Connected! Protocol: {protocol}', file=sys.stderr)
            print(f'[info] {len(connection.supported_commands)} PIDs available',
                  file=sys.stderr)
            return connection

        elif status == obd.OBDStatus.ELM_CONNECTED:
            print('[warning] Adapter found, but car ignition is OFF', file=sys.stderr)
            print('[info] Turn ignition ON (engine can stay off) for full data',
                  file=sys.stderr)
            # Return connection anyway - some PIDs might still work
            return connection

        else:
            print(f'[warning] Connection failed (status: {status}) — using simulation mode',
                  file=sys.stderr)
            try:
                connection.close()
            except Exception:
                pass
            return None

    except Exception as e:
        print(f'[warning] Connection error: {e} — using simulation mode',
              file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Main CLI loop
# ---------------------------------------------------------------------------

def main():
    """
    Main entry point.
    Connect to OBD adapter once, then loop forever printing JSON snapshots.
    Also POSTs each reading to the FastAPI server for database storage.
    """

    print('[info] Starting OBD-II JSON logger...', file=sys.stderr)

    # Connect to OBD adapter (or fall back to simulation)
    connection = connect_to_obd()

    if connection is None:
        print('[info] Running in SIMULATION MODE', file=sys.stderr)

    print('[info] Outputting one JSON line per second (Ctrl-C to stop)',
          file=sys.stderr)
    print('[info] Sending readings to API at http://localhost:8000/readings',
          file=sys.stderr)
    print('', file=sys.stderr)  # Blank line before JSON output

    # API endpoint URL
    # This is where each reading gets sent to be stored in the database
    api_url = "http://localhost:8000/readings"

    # Track consecutive failures for reconnection logic
    consecutive_failures = 0
    max_failures = 5

    try:
        while True:
            try:
                # Read sensor snapshot
                snapshot = read_obd_snapshot(connection)

                # Print as single-line JSON to console (existing behavior)
                print(json.dumps(snapshot))

                # Flush stdout immediately (important for piping)
                sys.stdout.flush()

                # ============================================================
                # THIS IS THE LIVE TELEMETRY PIPELINE
                # ============================================================
                # Send the reading to FastAPI server for permanent storage.
                # This creates the connection between CLI OBD loop → API → Database.
                # If the POST fails (network issue, server down, etc.), we just
                # print a warning and continue collecting data. The loop should
                # never crash because of network problems.
                # ============================================================
                try:
                    response = requests.post(api_url, json=snapshot, timeout=2)
                    response.raise_for_status()  # Raise error if status code is 4xx or 5xx
                except requests.exceptions.RequestException as e:
                    # Network error, server down, or timeout - just warn and continue
                    print(f'[warning] Failed to send reading to API: {e}', file=sys.stderr)
                except Exception as e:
                    # Any other unexpected error - warn and continue
                    print(f'[warning] Unexpected error sending to API: {e}', file=sys.stderr)

                # Reset failure counter on success
                consecutive_failures = 0

            except Exception as e:
                # Something went wrong reading the snapshot
                consecutive_failures += 1
                print(f'[error] Failed to read snapshot: {e}', file=sys.stderr)

                # If too many failures, try to reconnect
                if consecutive_failures >= max_failures:
                    print('[info] Too many failures, attempting to reconnect...',
                          file=sys.stderr)

                    # Close old connection
                    if connection is not None:
                        try:
                            connection.close()
                        except Exception:
                            pass

                    # Wait a bit before reconnecting
                    time.sleep(2)

                    # Try to reconnect
                    connection = connect_to_obd()
                    consecutive_failures = 0

            # Wait 1 second before next reading
            time.sleep(1)

    except KeyboardInterrupt:
        print('', file=sys.stderr)
        print('[info] Shutting down...', file=sys.stderr)

        # Clean up connection
        if connection is not None:
            try:
                connection.close()
                print('[info] OBD connection closed', file=sys.stderr)
            except Exception:
                pass

        print('[info] Goodbye!', file=sys.stderr)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    main()
