"""Entry point for the Raspberry Pi OBD-II data logger skeleton."""

from __future__ import annotations

import argparse
import csv
import math
import signal
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional

# TODO (tomorrow):
# - Import python-OBD and open a Bluetooth serial connection automatically.
# - Add a reconnect loop that keeps trying when the adapter momentarily drops.
# - Replace NotImplementedError with real PID queries feeding read_obd_pids().


CSV_FILENAME = "obd_readings.csv"
FAKE_RECONNECT_EVERY = 3
_shutdown_requested = False


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
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable extra debug hooks (placeholder for tomorrow's features).",
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


@dataclass
class CsvLogger:
    """Simple CSV writer that auto-writes headers and flushes each row."""

    filename: str = CSV_FILENAME
    _file: Optional[object] = None
    _writer: Optional[csv.DictWriter] = None

    def __enter__(self) -> "CsvLogger":
        self._file = open(self.filename, "w", newline="", encoding="utf-8")
        self._writer = None
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None
            self._writer = None

    def write(self, reading: Dict[str, float | int | str]) -> None:
        if self._file is None:
            return

        if self._writer is None:
            headers = list(reading.keys())
            self._writer = csv.DictWriter(self._file, fieldnames=headers)
            self._writer.writeheader()

        assert self._writer is not None
        self._writer.writerow(reading)
        self._file.flush()


def shutdown_requested() -> bool:
    """Return True if the signal handler asked for a graceful shutdown."""

    return _shutdown_requested


def handle_sigint(signum, frame) -> None:
    """Log the intent to shut down and raise KeyboardInterrupt for cleanup."""

    global _shutdown_requested
    if not _shutdown_requested:
        _shutdown_requested = True
        log("INFO", "Ctrl-C received; requesting graceful shutdown.")
    else:  # pragma: no cover - defensive in case of repeated Ctrl-C
        log("WARN", "Second Ctrl-C received; forcing immediate shutdown.")
    raise KeyboardInterrupt


def reconnect_obd(connection: Optional[object]) -> Optional[object]:
    """Return a fresh OBD-II connection.

    TODO: Tomorrow we will close the stale handle, wait briefly, and call
    python-OBD to reconnect automatically. The fake mode already exercises this
    hook so the control flow is ready when real hardware arrives.
    """

    log("reconnect", "reconnect_obd() placeholder invoked; no hardware actions.")
    return connection


def run_fake_cycles(count: int, csv_logger: CsvLogger | None = None) -> None:
    """Run COUNT fake readings spaced roughly one second apart."""

    if count <= 0:
        log("WARN", "--fake-run COUNT must be greater than zero.")
        return

    log("fake", f"Running {count} fake cycle(s) with no hardware attached.")
    completed = False
    try:
        for index in range(1, count + 1):
            if shutdown_requested():
                log("fake", "Shutdown requested; ending fake cycles early.")
                break

            start = time.time()
            reading = generate_fake_reading(start)
            if csv_logger is not None:
                csv_logger.write(reading)
            log("fake", f"Cycle {index}/{count}: {format_reading(reading)}")

            if index % FAKE_RECONNECT_EVERY == 0:
                log("reconnect", "Lost connection, will retry…")
                reconnect_obd(None)

            elapsed = time.time() - start
            if elapsed < 1:
                time.sleep(1 - elapsed)
        else:
            completed = True
    finally:
        if completed:
            log("fake", "Completed requested fake cycles.")
        elif shutdown_requested():
            log("fake", "Fake cycles stopped due to shutdown request.")


def run_fake_mode(args: argparse.Namespace) -> None:
    """Handle legacy fake options that pre-date the new modes."""

    log("fake", "Running in fake mode (no hardware required).")
    reading = generate_fake_reading()

    if args.print_sample:
        print_sample_output(reading)
        log("fake", "Self-test complete.")
    else:
        log("fake", "Fake mode ready. Use --print-sample to view a reading.")


def connect_to_obd() -> Optional[object]:
    """Return a python-OBD connection object once the library is wired up."""

    # Tomorrow we will import python-OBD here, detect available Bluetooth serial
    # ports, and call obd.OBD() to open the best match. Until then we simply
    # return None so the rest of the flow can be written and logged.
    log("real", "connect_to_obd() placeholder called; no hardware actions taken.")
    return None


def read_obd_pids(connection: Optional[object]) -> Dict[str, float | int | str]:
    """Read key PIDs from an OBD-II connection once a real library is wired."""

    # Tomorrow's logic will look like:
    # 1. Use connection.query(obd.commands.RPM) and other PID commands.
    # 2. Convert the returned Unit types into plain numbers.
    # 3. Return the values in the same shape as generate_fake_reading().
    # For now we simply raise NotImplementedError so our control flow knows this
    # branch is unfinished, but callers can catch it and continue running.
    raise NotImplementedError("Real PID reading arrives tomorrow.")


def run_real_mode(args: argparse.Namespace) -> None:
    """Placeholder real hardware flow that will be completed tomorrow."""

    # All real hardware runs will come through this function. By separating it
    # out, we can grow reconnect logic and error handling without cluttering the
    # fake path that beginners use for quick experiments.
    log("real", "Attempting hardware mode setup (design scaffold only).")

    try:
        connection = connect_to_obd()
        # TODO: Add reconnect loop here once bluetooth/python-OBD is wired up.
        reading = read_obd_pids(connection)
        log("real", format_reading(reading))
    except NotImplementedError:
        log(
            "real",
            "Real OBD-II support lands tomorrow. Tonight only scaffolding runs.",
        )
    except Exception as exc:  # pragma: no cover - defensive logging for tomorrow
        # When the full implementation lands we will reconnect instead of
        # exiting. Keeping the placeholder log ensures the control flow is
        # visible today without touching serial ports.
        log("ERROR", f"Unexpected error in real mode scaffold: {exc}")


def main() -> None:
    """Script entry point used by both manual runs and CI."""

    global _shutdown_requested
    _shutdown_requested = False

    args = parse_args()
    signal.signal(signal.SIGINT, handle_sigint)

    log("INFO", "===== Starting OBD-II data logger skeleton =====")
    if args.debug:
        log("INFO", "Debug hooks enabled (no additional behaviour yet).")

    try:
        if args.fake_run is not None:
            with CsvLogger() as csv_logger:
                run_fake_cycles(args.fake_run, csv_logger=csv_logger)
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
            log(
                "WARN",
                "--print-sample requires fake data until hardware support is added.",
            )

        log(
            "real",
            "Switching to hardware scaffolding. No bluetooth/python-OBD actions tonight.",
        )
        run_real_mode(args)
    except KeyboardInterrupt:
        log("INFO", "KeyboardInterrupt caught; finishing cleanup.")
    finally:
        log("INFO", "===== Shutdown complete =====")


if __name__ == "__main__":
    main()
