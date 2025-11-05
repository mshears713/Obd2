"""Lightweight terminal dashboard for monitoring the latest OBD-II readings.

Usage: run ``python text_dashboard.py`` to watch the data refresh every second.
Press ``Ctrl+C`` to exit without any scary traceback.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Dict, Tuple

from data_manager import get_latest_reading
from main import generate_fake_reading

# Refresh cadence (seconds between screen updates).
REFRESH_DELAY = 1.0
# Width of the ASCII progress bars. Keep it short for narrow Pi terminals.
BAR_WIDTH = 30
# Friendly banner displayed on each refresh to anchor the layout.
BANNER = "OBD-II TEXT DASHBOARD"


def _ascii_bar(value: float, maximum: float, label: str) -> str:
    """Return a formatted metric line with a simple ASCII bar."""

    safe_max = maximum if maximum > 0 else 1
    ratio = max(0.0, min(value / safe_max, 1.0))
    filled = int(ratio * BAR_WIDTH)
    empty = BAR_WIDTH - filled
    bar = "#" * filled + "." * empty
    return f" {label:<10}: {value:>7.1f} |[{bar}]"[:78]


def _safe_fetch() -> Tuple[Dict[str, float | int | str], str, str]:
    """Fetch the latest reading, falling back to fake data when needed."""

    try:
        reading = get_latest_reading()
        return reading, "CSV", ""
    except Exception as exc:  # pragma: no cover - exercised via tests
        reading = generate_fake_reading()
        note = f"Source failure: {exc}"[:55]
        return reading, "Simulated", note


def _print_dashboard(
    reading: Dict[str, float | int | str],
    source_label: str,
    note: str,
    update_count: int,
    start_time: float,
) -> None:
    """Clear the screen and paint the latest reading in an easy-to-read grid."""

    clear_cmd = "cls" if os.name == "nt" else "clear"
    if os.name == "nt" or os.getenv("TERM"):
        os.system(clear_cmd)
    else:
        print("\033c", end="")

    now_str = datetime.now(timezone.utc).isoformat(timespec="seconds")
    elapsed = int(time.time() - start_time)
    timestamp = reading.get("timestamp", now_str)

    print("=" * 40)
    print(f" {BANNER}")
    print("=" * 40)
    print(f" Update #{update_count:04d} | Elapsed: {elapsed:>4}s | Source: {source_label}")
    print(f" Last Sample : {timestamp}")

    rpm = float(reading.get("rpm", 0))
    speed = float(reading.get("vehicle_speed_mph", 0))
    coolant = float(reading.get("coolant_temp_f", 0))
    throttle = float(reading.get("throttle_position_pct", 0))

    print()
    print(_ascii_bar(rpm, 6000, "RPM"))
    print(_ascii_bar(speed, 120, "Speed mph"))
    print(_ascii_bar(coolant, 260, "Coolant F"))
    print(_ascii_bar(throttle, 100, "Throttle"))

    if note:
        print()
        print(f" NOTE: {note}")

    print()
    print(f" Timestamp: {now_str}")


def run_dashboard(iterations: int | None = None) -> None:
    """Run the live dashboard loop; iterations can be set for testing."""

    print("Starting text dashboard. Press Ctrl+C to exit.")
    start_time = time.time()
    update_count = 0

    try:
        while True:
            update_count += 1
            reading, source_label, note = _safe_fetch()
            _print_dashboard(reading, source_label, note, update_count, start_time)

            if iterations is not None and update_count >= iterations:
                break

            time.sleep(REFRESH_DELAY)
    except KeyboardInterrupt:
        print("\nStopping dashboard. Have a safe drive!")


if __name__ == "__main__":  # pragma: no cover - manual execution entry point
    run_dashboard()
