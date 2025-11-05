# Raspberry Pi OBD-II Data Logger

Simple starter app for logging car data on a Raspberry Pi using an ELM327 adapter.

## Features tonight
- Fake mode simulates believable RPM, speed, coolant temperature, and throttle values.
- CLI flags: `--fake` enables the simulator, `--print-sample` prints a CSV header and one reading.
- Console logging keeps output friendly and easy to read.

## Requirements
- Python 3.10+

## Usage
1. Create a virtual environment (optional but recommended).
2. Install dependencies: `pip install -r requirements.txt`
3. Run fake mode: `python3 main.py --fake --print-sample`

The command above runs a tiny self-test and shows a single simulated reading.

## Next steps
- Tomorrow: plug into the ELM327 Bluetooth adapter and record real OBD-II frames.
- Later: expose a simple HTTP API endpoint and build a lightweight web dashboard for live data.
