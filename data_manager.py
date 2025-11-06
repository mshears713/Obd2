"""Stage 1 helper for loading and extending ``obd_readings.csv``."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, TYPE_CHECKING

from main import generate_fake_reading

CSV_PATH = Path(__file__).with_name("obd_readings.csv")
EXPECTED_HEADERS = [
    "timestamp",
    "rpm",
    "coolant_temp_f",
    "vehicle_speed_mph",
    "throttle_position_pct",
    "engine_load_pct",
    "timing_advance_deg",
]
MIN_ROWS = 60

if TYPE_CHECKING:  # pragma: no cover - import only for type hints
    import obd

# ``_LAST_OBD_READING`` keeps the most recent live values so we can reuse them
# when a PID is unavailable on the adapter. This prevents the dashboard from
# blanking fields during temporary hiccups.
_LAST_OBD_READING: Dict[str, float | int | str | None] = {
    "rpm": 0,
    "coolant_temp_f": 0.0,
    "vehicle_speed_mph": 0.0,
    "throttle_position_pct": 0.0,
    "engine_load_pct": None,
    "timing_advance_deg": None,
}


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
        rows = list(reader)
        if missing:
            print(
                "[DATA] CSV missing newer columns: "
                + ", ".join(missing)
                + "; filling with blanks."
            )
            for row in rows:
                for field in missing:
                    row[field] = ""
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
        fake_row.setdefault("engine_load_pct", 0.0)
        fake_row.setdefault("timing_advance_deg", 0.0)
        readings.append(fake_row)

    return fake_added


def _write_csv(readings: List[Dict[str, float | int | str]]) -> None:
    """Persist the extended readings so the dashboards can reuse them."""

    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPECTED_HEADERS)
        writer.writeheader()
        for row in readings:
            writer.writerow({field: row.get(field, "") for field in EXPECTED_HEADERS})


def _read_obd_live(
    connection: "obd.OBD | None" = None,
) -> Dict[str, float | int | str]:
    """Grab a fresh sample from the Bluetooth OBD-II adapter.

    A persistent ``connection`` can be provided by the caller so repeated reads
    avoid the expensive connect/close cycle that originally caused 6–10 second
    refresh delays. When ``connection`` is ``None`` we fall back to opening a
    one-shot handle for backwards compatibility.
    """

    try:
        import obd
    except ImportError as exc:  # pragma: no cover - hardware dependency
        raise RuntimeError("python-OBD library not installed") from exc

    owns_connection = connection is None
    if owns_connection:
        connection = obd.OBD("/dev/rfcomm0")

    assert connection is not None  # for type checkers only

    status = connection.status() if hasattr(connection, "status") else None
    is_connected = getattr(connection, "is_connected", lambda: True)()
    if not is_connected:
        if owns_connection:
            connection.close()
        message = (
            f"OBD not connected: {status}"
            if status is not None
            else "OBD adapter not connected"
        )
        raise RuntimeError(message)

    reading: Dict[str, float | int | str] = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rpm": int(_LAST_OBD_READING.get("rpm", 0) or 0),
        "coolant_temp_f": float(_LAST_OBD_READING.get("coolant_temp_f", 0.0) or 0.0),
        "vehicle_speed_mph": float(
            _LAST_OBD_READING.get("vehicle_speed_mph", 0.0) or 0.0
        ),
        "throttle_position_pct": float(
            _LAST_OBD_READING.get("throttle_position_pct", 0.0) or 0.0
        ),
        "engine_load_pct": _LAST_OBD_READING.get("engine_load_pct"),
        "timing_advance_deg": _LAST_OBD_READING.get("timing_advance_deg"),
    }

    try:
        response = connection.query(obd.commands.RPM)
        if not response.is_null():
            reading["rpm"] = int(response.value.magnitude)

        response = connection.query(obd.commands.SPEED)
        if not response.is_null():
            reading["vehicle_speed_mph"] = round(
                response.value.magnitude * 0.621371, 1
            )

        response = connection.query(obd.commands.COOLANT_TEMP)
        if not response.is_null():
            reading["coolant_temp_f"] = round(
                response.value.magnitude * 9 / 5 + 32, 1
            )

        response = connection.query(obd.commands.THROTTLE_POS)
        if not response.is_null():
            reading["throttle_position_pct"] = round(response.value.magnitude, 1)

        response = connection.query(obd.commands.ENGINE_LOAD)
        if not response.is_null():
            reading["engine_load_pct"] = round(response.value.magnitude, 1)

        response = connection.query(obd.commands.TIMING_ADVANCE)
        if not response.is_null():
            reading["timing_advance_deg"] = round(response.value.magnitude, 1)
    finally:
        if owns_connection:
            connection.close()

    _LAST_OBD_READING.update(
        {
            "rpm": reading["rpm"],
            "coolant_temp_f": reading["coolant_temp_f"],
            "vehicle_speed_mph": reading["vehicle_speed_mph"],
            "throttle_position_pct": reading["throttle_position_pct"],
            "engine_load_pct": reading["engine_load_pct"],
            "timing_advance_deg": reading["timing_advance_deg"],
        }
    )

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
            "timestamp": row.get("timestamp", ""),
            "rpm": int(float(row.get("rpm", 0) or 0)),
            "coolant_temp_f": float(row.get("coolant_temp_f", 0) or 0),
            "vehicle_speed_mph": float(row.get("vehicle_speed_mph", 0) or 0),
            "throttle_position_pct": float(row.get("throttle_position_pct", 0) or 0),
            "engine_load_pct": (
                float(row.get("engine_load_pct", 0) or 0)
                if row.get("engine_load_pct") not in (None, "")
                else None
            ),
            "timing_advance_deg": (
                float(row.get("timing_advance_deg", 0) or 0)
                if row.get("timing_advance_deg") not in (None, "")
                else None
            ),
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

