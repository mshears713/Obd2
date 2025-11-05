"""Entry point for the Raspberry Pi OBD-II data logger skeleton."""

from __future__ import annotations

import argparse
import obd
import csv
import math
import signal
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# Configuration constants (tomorrow's real OBD hooks will reuse these values).
# ---------------------------------------------------------------------------
CSV_FILENAME = "obd_readings.csv"
FAKE_RECONNECT_EVERY = 3
LOG_PREFIX_SYSTEM = "SYSTEM"
LOG_PREFIX_FAKE = "FAKE"
LOG_PREFIX_REAL = "REAL"
LOG_PREFIX_CSV = "CSV"
LOG_PREFIX_WARN = "WARN"
LOG_PREFIX_ERROR = "ERROR"

# TODO (tomorrow):
# - Import python-OBD and open a Bluetooth serial connection automatically.
# - Add a reconnect loop that keeps trying when the adapter momentarily drops.
# - Replace NotImplementedError with real PID queries feeding read_obd_pids().


_shutdown_requested = False


def parse_args() -> argparse.Namespace:
    """Parse user-friendly command-line arguments for the prototype."""

    parser = argparse.ArgumentParser(
        description="Simple CLI shell for the Raspberry Pi OBD-II logger prototype",
    )
    # Tomorrow we will add real OBD connection options (Bluetooth port, baud, etc.).
    parser.add_argument(
        "--fake",
        action="store_true",
        help="Use gentle sine-wave readings instead of real hardware.",
    )
    parser.add_argument(
        "--print-sample",
        action="store_true",
        help="Show the CSV header plus one fake reading.",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Log one fake reading then exit (great for CI).",
    )
    parser.add_argument(
        "--fake-run",
        type=int,
        metavar="COUNT",
        help="Write COUNT fake readings (about one per second) then exit.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print extra scaffolding logs while experimenting.",
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
    log(LOG_PREFIX_CSV, "Sample CSV header")
    print(",".join(headers))
    log(LOG_PREFIX_CSV, "Sample fake reading")
    print(",".join(str(reading[field]) for field in headers))


def run_fake_smoke_test() -> None:
    """Run a single fake reading then stop. Perfect for CI smoke tests."""

    log(LOG_PREFIX_FAKE, "Starting fake smoke test.")
    reading = generate_fake_reading()
    log(LOG_PREFIX_FAKE, format_reading(reading))
    log(LOG_PREFIX_FAKE, "Smoke test finished cleanly.")


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
        log(LOG_PREFIX_SYSTEM, "Ctrl-C received; requesting graceful shutdown.")
    else:  # pragma: no cover - defensive in case of repeated Ctrl-C
        log(LOG_PREFIX_WARN, "Second Ctrl-C received; forcing immediate shutdown.")
    raise KeyboardInterrupt


def reconnect_obd(connection: Optional[obd.OBD]) -> Optional[obd.OBD]:
    """Close the old handle, wait briefly, and return a fresh connection."""

    try:
        if connection is not None:
            connection.close()
    except Exception as exc:  # pragma: no cover - defensive cleanup
        log(LOG_PREFIX_WARN, f"Problem while closing OBD connection: {exc}")

    log(LOG_PREFIX_REAL, "Reconnecting to OBD-II adapter after short pause.")
    time.sleep(2)
    return connect_to_obd()


def run_fake_cycles(count: int, csv_logger: CsvLogger | None = None) -> None:
    """Run COUNT fake readings spaced roughly one second apart."""

    if count <= 0:
        log(LOG_PREFIX_WARN, "--fake-run COUNT must be greater than zero.")
        return

    log(LOG_PREFIX_FAKE, f"Running {count} fake cycle(s) with no hardware attached.")
    completed = False
    try:
        for index in range(1, count + 1):
            if shutdown_requested():
                log(LOG_PREFIX_FAKE, "Shutdown requested; ending fake cycles early.")
                break

            start = time.time()
            reading = generate_fake_reading(start)
            if csv_logger is not None:
                csv_logger.write(reading)
            log(LOG_PREFIX_FAKE, f"Cycle {index}/{count}: {format_reading(reading)}")

            if index % FAKE_RECONNECT_EVERY == 0:
                log(LOG_PREFIX_REAL, "Lost connection, will retry…")
                reconnect_obd(None)

            elapsed = time.time() - start
            if elapsed < 1:
                time.sleep(1 - elapsed)
        else:
            completed = True
    finally:
        if completed:
            log(LOG_PREFIX_FAKE, "Completed requested fake cycles.")
        elif shutdown_requested():
            log(LOG_PREFIX_FAKE, "Fake cycles stopped due to shutdown request.")


def run_fake_mode(args: argparse.Namespace) -> None:
    """Handle legacy fake options that pre-date the new modes."""

    log(LOG_PREFIX_FAKE, "Running in fake mode (no hardware required).")
    reading = generate_fake_reading()

    if args.print_sample:
        print_sample_output(reading)
        log(LOG_PREFIX_FAKE, "Self-test complete.")
    else:
        log(
            LOG_PREFIX_FAKE,
            "Fake mode ready. Use --print-sample to view a reading.",
        )


def connect_to_obd() -> Optional[obd.OBD]:
    """Connect to the bluetooth adapter and return the python-OBD handle."""

    try:
        log(LOG_PREFIX_REAL, "Connecting to OBD-II adapter on /dev/rfcomm0…")
        connection = obd.OBD("/dev/rfcomm0", fast=False)
        status = connection.status()

        if status == obd.OBDStatus.CAR_CONNECTED:
            protocol = connection.protocol_name() or "unknown"
            supported_commands = connection.supported_commands
            if supported_commands is None:
                supported = 0
            else:
                try:
                    supported = len(supported_commands)
                except TypeError:
                    supported = len(list(supported_commands))
            log(
                LOG_PREFIX_REAL,
                f"Connected (protocol {protocol}; {supported} commands available).",
            )
            return connection

        if status == obd.OBDStatus.ELM_CONNECTED:
            protocol = connection.protocol_name() or "unknown"
            supported_commands = connection.supported_commands
            if supported_commands is None:
                supported = 0
            else:
                try:
                    supported = len(supported_commands)
                except TypeError:
                    supported = len(list(supported_commands))
            log(
                LOG_PREFIX_WARN,
                "Adapter paired but ignition seems off. Reading may be limited.",
            )
            log(
                LOG_PREFIX_REAL,
                f"ELM ready (protocol {protocol}; {supported} commands available).",
            )
            return connection

        log(
            LOG_PREFIX_ERROR,
            f"Unable to talk to vehicle (status: {status.name if status else status}).",
        )
    except Exception as exc:
        log(LOG_PREFIX_ERROR, f"Failed to connect to OBD adapter: {exc}")

    return None


def read_obd_pids(connection: Optional[obd.OBD]) -> Dict[str, float | int | str]:
    """Query a handful of PIDs and return them in CSV-friendly form."""

    if connection is None:
        raise ValueError("No OBD connection available.")

    def safe_query(command):
        try:
            response = connection.query(command)
        except Exception as exc:  # pragma: no cover - defensive logging
            log(LOG_PREFIX_WARN, f"PID query {command.name} failed: {exc}")
            return None
        if response is None or response.is_null():
            return None
        return response.value

    rpm_value = safe_query(obd.commands.RPM)
    speed_value = safe_query(obd.commands.SPEED)
    coolant_value = safe_query(obd.commands.COOLANT_TEMP)
    throttle_value = safe_query(obd.commands.THROTTLE_POS)

    def extract_magnitude(value, unit: str | None = None) -> Optional[float]:
        if value is None:
            return None
        converted = value
        if unit is not None and hasattr(value, "to"):
            try:
                converted = value.to(unit)
            except Exception:
                converted = value
        magnitude = getattr(converted, "magnitude", None)
        if magnitude is None:
            try:
                magnitude = float(converted)
            except (TypeError, ValueError):
                return None
        return magnitude

    rpm_magnitude = extract_magnitude(rpm_value)
    rpm = int(rpm_magnitude) if rpm_magnitude is not None else None

    speed_kmh = extract_magnitude(speed_value, "km/h")
    speed_mph = round(speed_kmh * 0.621371, 1) if speed_kmh is not None else None

    coolant_c = extract_magnitude(coolant_value, "degC")
    coolant_temp_f = (
        round((coolant_c * 9 / 5) + 32, 1) if coolant_c is not None else None
    )

    throttle_raw = extract_magnitude(throttle_value, "percent")
    throttle_pct = round(throttle_raw, 1) if throttle_raw is not None else None

    reading: Dict[str, float | int | str] = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rpm": rpm,
        "coolant_temp_f": coolant_temp_f,
        "vehicle_speed_mph": speed_mph,
        "throttle_position_pct": throttle_pct,
    }
    return reading


def run_real_mode(args: argparse.Namespace) -> None:
    """Poll real hardware until shutdown is requested."""

    log(LOG_PREFIX_REAL, "Starting real OBD-II capture loop.")

    connection = connect_to_obd()
    if connection is None:
        log(LOG_PREFIX_ERROR, "No OBD connection available; aborting real mode.")
        return

    try:
        with CsvLogger() as csv_logger:
            while not shutdown_requested():
                start = time.time()
                try:
                    reading = read_obd_pids(connection)
                except Exception as exc:
                    log(LOG_PREFIX_WARN, f"Read failed: {exc}; attempting reconnect.")
                    connection = reconnect_obd(connection)
                    if connection is None:
                        log(
                            LOG_PREFIX_ERROR,
                            "Reconnect failed; waiting before next attempt.",
                        )
                        time.sleep(2)
                    continue

                csv_logger.write(reading)
                log(LOG_PREFIX_REAL, format_reading(reading))

                elapsed = time.time() - start
                if elapsed < 1:
                    time.sleep(1 - elapsed)
    finally:
        try:
            connection.close()
        except Exception:  # pragma: no cover - defensive cleanup
            pass


def main() -> None:
    """Script entry point used by both manual runs and CI."""

    global _shutdown_requested
    _shutdown_requested = False

    args = parse_args()
    signal.signal(signal.SIGINT, handle_sigint)

    log(LOG_PREFIX_SYSTEM, "===== Starting OBD-II data logger skeleton =====")
    if args.debug:
        log(LOG_PREFIX_SYSTEM, "Debug hooks enabled (no additional behaviour yet).")

    try:
        if args.fake_run is not None:
            with CsvLogger() as csv_logger:
                run_fake_cycles(args.fake_run, csv_logger=csv_logger)
            return

        if args.smoke_test:
            if not args.fake:
                log(
                    LOG_PREFIX_SYSTEM,
                    "--smoke-test defaults to fake data until hardware arrives.",
                )
            run_fake_smoke_test()
            return

        if args.fake:
            run_fake_mode(args)
            return

        if args.print_sample:
            log(
                LOG_PREFIX_WARN,
                "--print-sample requires fake data until hardware support is added.",
            )

        log(
            LOG_PREFIX_REAL,
            "Switching to hardware scaffolding. No bluetooth/python-OBD actions tonight.",
        )
        run_real_mode(args)
    except KeyboardInterrupt:
        log(LOG_PREFIX_SYSTEM, "KeyboardInterrupt caught; finishing cleanup.")
    finally:
        log(LOG_PREFIX_SYSTEM, "===== Shutdown complete =====")


if __name__ == "__main__":
    main()
