"""Entry point for the Raspberry Pi OBD-II data logger skeleton."""

from __future__ import annotations

import argparse
import math
import time
from datetime import datetime, timezone
from typing import Dict


def parse_args() -> argparse.Namespace:
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
    return parser.parse_args()


def log(prefix: str, message: str) -> None:
    print(f"{prefix}: {message}")


def generate_fake_reading(tick: float | None = None) -> Dict[str, str]:
    if tick is None:
        tick = time.time()

    rpm_cycle = 750 + 350 * (1 + math.sin(tick / 2))
    throttle_cycle = 12 + 8 * (1 + math.sin(tick / 3))
    speed_cycle = 5 + 20 * (1 + math.sin(tick / 4))

    reading = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rpm": f"{int(rpm_cycle):d}",
        "coolant_temp_f": f"{round(183 + 4 * math.sin(tick / 5), 1):.1f}",
        "vehicle_speed_mph": f"{round(speed_cycle, 1):.1f}",
        "throttle_position_pct": f"{round(throttle_cycle, 1):.1f}",
    }
    return reading


def print_sample_output(reading: Dict[str, str]) -> None:
    headers = list(reading.keys())
    log("INFO", "Sample CSV header")
    print(",".join(headers))
    log("INFO", "Sample fake reading")
    print(",".join(reading[field] for field in headers))


def run_fake_mode(args: argparse.Namespace) -> None:
    log("INFO", "Running in fake mode (no hardware required).")
    reading = generate_fake_reading()

    if args.print_sample:
        print_sample_output(reading)
        log("INFO", "Self-test complete.")
    else:
        log("INFO", "Fake mode ready. Use --print-sample to view a reading.")


def main() -> None:
    args = parse_args()
    log("INFO", "Starting OBD-II data logger skeleton.")

    if args.fake:
        run_fake_mode(args)
        return

    if args.print_sample:
        log("WARN", "--print-sample requires --fake until hardware support is added.")
    log("WARN", "Hardware mode not implemented yet. Try again with --fake.")


if __name__ == "__main__":
    main()
