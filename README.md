# Raspberry Pi OBD-II Data Logger

Simple starter app for logging car data on a Raspberry Pi using an ELM327 adapter.

## Features tonight
- Fake mode simulates believable RPM, speed, coolant temperature, and throttle values.
- Real mode scaffolding logs each step without touching hardware yet.
- CLI flags: `--fake` enables the simulator, `--print-sample` prints a CSV header and one reading.
- Console logging keeps output friendly and easy to read.

## Requirements
- Python 3.10+

## Usage
1. Create a virtual environment (optional but recommended).
2. Install dependencies: `pip install -r requirements.txt`
3. Run fake mode: `python3 main.py --fake --print-sample`

The command above runs a tiny self-test and shows a single simulated reading.

## Architecture snapshot
- `main.py` keeps all logic in simple functions so beginners can follow the flow.
- `run_fake_mode()` and `run_real_mode()` share the same log format, making it
  easy to swap fake data for real PIDs tomorrow.
- `connect_to_obd()` and `read_obd_pids()` are placeholders that describe how
  python-OBD and Bluetooth discovery will plug in.

## Shutdown & Reconnect system
- Banner logs wrap startup/shutdown so Ctrl-C testing is obvious.
- `handle_sigint()` sets a shutdown flag and lets the app finish gracefully.
- `CsvLogger` writes `obd_readings.csv` with auto headers and clean closes.
- `reconnect_obd()` is a TODO stub that fake mode already exercises.
- Fake runs simulate a reconnect log every few cycles without raising errors.

## Next steps
- Tomorrow: import python-OBD, auto-detect the Bluetooth adapter, and start a
  reconnect loop that feeds `read_obd_pids()`.
- Later: expose a simple HTTP API endpoint and build a lightweight web dashboard for live data.
