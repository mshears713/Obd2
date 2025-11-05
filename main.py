"""Entry point for the Raspberry Pi OBD-II data logger skeleton."""

from __future__ import annotations

import argparse
import math
import time
from datetime import datetime, timezone
from typing import Dict


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments used to control how the script runs."""

    parser = argparse.ArgumentParser(
        description="Prototype CLI for the Raspberry Pi OBD-II logger"
    )
    parser.add_argument(
        "--fake",
        action="store_true",
        help="Use simulated sensor values instead of connecting to hardware.",
    )
    parser.add_argument(
        "--print-sample",
        action="store_true",
        help="Print a sample CSV header and a single reading.",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Generate one fake reading, log it, and exit immediately.",
    )
    parser.add_argument(
        "--fake-run",
        type=int,
        metavar="COUNT",
        help="Run COUNT fake readings (about one per second) then exit.",
    )
    return parser.parse_args()


def log(prefix: str, message: str) -> None:
    """Print structured log messages so tests can verify behaviour."""

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[{prefix.upper()}][{timestamp}] {message}")


def generate_fake_reading(tick: float | None = None) -> Dict[str, float | int | str]:
    """Return a fake sensor reading using smooth sine waves."""

    if tick is None:
        tick = time.time()

    rpm_cycle = 750 + 350 * (1 + math.sin(tick / 2))
    throttle_cycle = 12 + 8 * (1 + math.sin(tick / 3))
    speed_cycle = 5 + 20 * (1 + math.sin(tick / 4))

    reading = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rpm": int(rpm_cycle),
        "coolant_temp_f": round(183 + 4 * math.sin(tick / 5), 1),
        "vehicle_speed_mph": round(speed_cycle, 1),
        "throttle_position_pct": round(throttle_cycle, 1),
    }
    return reading


def format_reading(reading: Dict[str, float | int | str]) -> str:
    """Make the reading easy to read during tests and manual runs."""

    return (
        f"RPM={reading['rpm']} | "
        f"Speed={reading['vehicle_speed_mph']} mph | "
        f"Coolant={reading['coolant_temp_f']}F | "
        f"Throttle={reading['throttle_position_pct']}%"
    )


def print_sample_output(reading: Dict[str, float | int | str]) -> None:
    """Keep the earlier CSV demo so beginners can see the structure."""

    headers = list(reading.keys())
    log("INFO", "Sample CSV header")
    print(",".join(headers))
    log("INFO", "Sample fake reading")
    print(",".join(str(reading[field]) for field in headers))


def run_fake_smoke_test() -> None:
    """Run a single fake reading then stop. Perfect for CI smoke tests."""

    log("fake", "Starting fake smoke test.")
    reading = generate_fake_reading()
    log("fake", format_reading(reading))
    log("fake", "Smoke test finished cleanly.")


def run_fake_cycles(count: int) -> None:
    """Run COUNT fake readings spaced roughly one second apart."""

    if count <= 0:
        log("WARN", "--fake-run COUNT must be greater than zero.")
        return

    log("fake", f"Running {count} fake cycle(s) with no hardware attached.")
    for index in range(1, count + 1):
        start = time.time()
        reading = generate_fake_reading(start)
        log("fake", f"Cycle {index}/{count}: {format_reading(reading)}")
        time.sleep(max(0, 1 - (time.time() - start)))

    log("fake", "Completed requested fake cycles.")


def run_fake_mode(args: argparse.Namespace) -> None:
    """Handle legacy fake options that pre-date the new modes."""

    log("fake", "Running in fake mode (no hardware required).")
    reading = generate_fake_reading()

    if args.print_sample:
        print_sample_output(reading)
        log("fake", "Self-test complete.")
    else:
        log("fake", "Fake mode ready. Use --print-sample to view a reading.")


def main() -> None:
    """Script entry point used by both manual runs and CI."""

    args = parse_args()
    log("INFO", "Starting OBD-II data logger skeleton.")

    if args.fake_run is not None:
        run_fake_cycles(args.fake_run)
        return

    if args.smoke_test:
        if not args.fake:
            log("INFO", "--smoke-test defaults to fake data until hardware arrives.")
        run_fake_smoke_test()
        return

    if args.fake:
        run_fake_mode(args)
        return

    if args.print_sample:
        log("WARN", "--print-sample requires fake data until hardware support is added.")

    # When the real Bluetooth / python-OBD integration lands, this is where we
    # will connect to the vehicle. The fake helpers above were built to make the
    # transition painless by keeping the logging format consistent.
    log("WARN", "Hardware mode not implemented yet. Try again with --fake.")


if __name__ == "__main__":
    main()
