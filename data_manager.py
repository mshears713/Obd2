"""Stage 1 helper for loading and extending ``obd_readings.csv``."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

from main import generate_fake_reading

CSV_PATH = Path(__file__).with_name("obd_readings.csv")
EXPECTED_HEADERS = ["timestamp", "rpm", "coolant_temp_f", "vehicle_speed_mph", "throttle_position_pct"]
MIN_ROWS = 60


def _read_csv_rows() -> List[Dict[str, str]]:
    """Load any existing data, creating an empty list if the file is missing."""

    if not CSV_PATH.exists():
        print(f"[DATA] File '{CSV_PATH.name}' missing; new fake data will be created.")
        return []

    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV is missing a header row")
        missing = [h for h in EXPECTED_HEADERS if h not in reader.fieldnames]
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(missing)}")
        rows = list(reader)
        print(f"[DATA] Loaded {len(rows)} samples from '{CSV_PATH.name}'.")
        return rows


def _append_fake_rows(readings: List[Dict[str, float | int | str]]) -> bool:
    """Extend the data with gentle fake rows until we have one minute of samples."""

    if len(readings) >= MIN_ROWS:
        return False

    fake_added = False
    tick = len(readings)
    if readings:
        timestamp_cursor = datetime.fromisoformat(readings[-1]["timestamp"].replace("Z", "+00:00"))
    else:
        timestamp_cursor = datetime.now(timezone.utc) - timedelta(seconds=MIN_ROWS)

    while len(readings) < MIN_ROWS:
        fake_added = True
        tick += 1
        timestamp_cursor += timedelta(seconds=1)
        fake_row = generate_fake_reading(tick=tick)
        fake_row.update({"timestamp": timestamp_cursor.isoformat(timespec="seconds")})
        readings.append(fake_row)

    return fake_added


def _write_csv(readings: List[Dict[str, float | int | str]]) -> None:
    """Persist the extended readings so the dashboards can reuse them."""

    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPECTED_HEADERS)
        writer.writeheader()
        for row in readings:
            writer.writerow(row)


def _read_obd_live() -> Dict[str, float | int | str]:
    """Grab a fresh sample from the Bluetooth OBD-II adapter."""

    try:
        import obd
    except ImportError as exc:  # pragma: no cover - hardware dependency
        raise RuntimeError("python-OBD library not installed") from exc

    connection = obd.OBD("/dev/rfcomm0")

    if connection.status() != obd.OBDStatus.CAR_CONNECTED:
        status = connection.status()
        connection.close()
        raise RuntimeError(f"OBD not connected: {status}")

    reading: Dict[str, float | int | str] = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rpm": 0,
        "coolant_temp_f": 0.0,
        "vehicle_speed_mph": 0.0,
        "throttle_position_pct": 0.0,
    }

    try:
        response = connection.query(obd.commands.RPM)
        if not response.is_null():
            reading["rpm"] = int(response.value.magnitude)

        response = connection.query(obd.commands.SPEED)
        if not response.is_null():
            reading["vehicle_speed_mph"] = round(response.value.magnitude * 0.621371, 1)

        response = connection.query(obd.commands.COOLANT_TEMP)
        if not response.is_null():
            reading["coolant_temp_f"] = round(response.value.magnitude * 9 / 5 + 32, 1)

        response = connection.query(obd.commands.THROTTLE_POS)
        if not response.is_null():
            reading["throttle_position_pct"] = round(response.value.magnitude, 1)
    finally:
        connection.close()

    return reading


def get_latest_reading(source: str = "csv") -> Dict[str, float | int | str]:
    """Return the newest reading, either from CSV or the live adapter."""

    if source == "obd":
        return _read_obd_live()

    if source != "csv":
        raise ValueError(f"Unknown source '{source}'. Use 'csv' or 'obd'.")

    raw_rows = _read_csv_rows()
    readings = [
        {
            "timestamp": row["timestamp"],
            "rpm": int(float(row.get("rpm", 0) or 0)),
            "coolant_temp_f": float(row.get("coolant_temp_f", 0) or 0),
            "vehicle_speed_mph": float(row.get("vehicle_speed_mph", 0) or 0),
            "throttle_position_pct": float(row.get("throttle_position_pct", 0) or 0),
        }
        for row in raw_rows
    ]
    fake_added = _append_fake_rows(readings)

    if fake_added:
        _write_csv(readings)
        print(f"[DATA] Added fake rows to reach {len(readings)} samples.")
    else:
        print(f"[DATA] No fake rows needed; {len(readings)} samples ready.")

    return readings[-1]

