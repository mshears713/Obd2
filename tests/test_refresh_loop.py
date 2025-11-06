"""Tests for the Tkinter dashboard refresh loop and shutdown handling."""

from __future__ import annotations

import sys
import types
import time
from pathlib import Path
from typing import Callable, Dict

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

import data_manager
import tk_dashboard


def _build_root():
    """Create a Tk root or skip tests when no display is present."""

    import tkinter as tk

    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter GUI requires a display environment")
    root.withdraw()
    return root


def _spin(root, duration: float) -> None:
    """Pump the Tk event loop for ``duration`` seconds without blocking tests."""

    import tkinter as tk

    end_time = time.time() + duration
    while time.time() < end_time:
        root.update()
        root.update_idletasks()
        time.sleep(0.05)
    # One final update ensures pending callbacks finish.
    try:
        root.update()
        root.update_idletasks()
    except tk.TclError:
        # The root might already be destroyed by on_close(); that's fine.
        pass


def _make_app(
    monkeypatch: pytest.MonkeyPatch,
    reader: Callable[[], Dict[str, float | int | str]],
    fake_generator: Callable[[], Dict[str, float | int | str]] | None = None,
    data_source: str = "csv",
):
    """Create the dashboard app with patched data sources."""

    root = _build_root()
    def patched_reader(*_args, **_kwargs):
        return reader()

    monkeypatch.setattr(tk_dashboard, "get_latest_reading", patched_reader)
    if fake_generator is not None:
        monkeypatch.setattr(tk_dashboard, "generate_fake_reading", fake_generator)
    app = tk_dashboard.DashboardApp(root, data_source=data_source)
    app.start()
    return app, root


def test_refresh_updates_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure labels refresh every second when live data is available."""

    readings = [
        {
            "rpm": 1000,
            "vehicle_speed_mph": 12.3,
            "coolant_temp_f": 180.0,
            "throttle_position_pct": 15.0,
            "engine_load_pct": 40.0,
            "timing_advance_deg": 2.0,
        },
        {
            "rpm": 2200,
            "vehicle_speed_mph": 25.4,
            "coolant_temp_f": 182.0,
            "throttle_position_pct": 18.0,
            "engine_load_pct": 45.0,
            "timing_advance_deg": 3.0,
        },
    ]

    def fake_reader() -> Dict[str, float | int | str]:
        if fake_reader.calls < len(readings):
            result = readings[fake_reader.calls]
        else:
            result = readings[-1]
        fake_reader.calls += 1
        return result

    fake_reader.calls = 0  # type: ignore[attr-defined]

    app, root = _make_app(monkeypatch, fake_reader)

    try:
        _spin(root, 0.1)
        assert app.value_labels["RPM"].cget("text") == "1000"

        _spin(root, 1.2)
        assert app.value_labels["RPM"].cget("text") == "2200"
        assert app.frame_count >= 2
    finally:
        app.stop()
        if root.winfo_exists():
            root.destroy()


def test_error_switches_to_simulated_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulated mode should activate on errors then return to live data."""

    live_reading = {
        "rpm": 1500,
        "vehicle_speed_mph": 30.0,
        "coolant_temp_f": 185.0,
        "throttle_position_pct": 20.0,
    }

    def flaky_reader() -> Dict[str, float | int | str]:
        flaky_reader.calls += 1
        if flaky_reader.calls == 1:
            raise FileNotFoundError("missing csv")
        return live_reading

    flaky_reader.calls = 0  # type: ignore[attr-defined]

    def fake_generator() -> Dict[str, float | int | str]:
        return {
            "rpm": 999,
            "vehicle_speed_mph": 9.9,
            "coolant_temp_f": 160.0,
            "throttle_position_pct": 10.0,
            "engine_load_pct": 35.0,
            "timing_advance_deg": -1.0,
        }

    app, root = _make_app(monkeypatch, flaky_reader, fake_generator=fake_generator)

    try:
        _spin(root, 0.1)
        assert app.sim_label.cget("text") == "(Simulated Mode)"

        _spin(root, 1.2)
        assert app.sim_label.cget("text") == ""
        assert app.simulated_mode is False
    finally:
        app.stop()
        if root.winfo_exists():
            root.destroy()


def test_shutdown_cancels_after(monkeypatch: pytest.MonkeyPatch) -> None:
    """Closing the window should cancel scheduled callbacks and destroy the root."""

    def steady_reader() -> Dict[str, float | int | str]:
        return {
            "rpm": 800,
            "vehicle_speed_mph": 0.0,
            "coolant_temp_f": 170.0,
            "throttle_position_pct": 12.0,
            "engine_load_pct": 32.0,
            "timing_advance_deg": 0.0,
        }

    app, root = _make_app(monkeypatch, steady_reader)

    try:
        _spin(root, 0.1)
        scheduled = app.after_id
        assert scheduled is not None

        app.on_close()
        assert app.after_id is None
        try:
            exists = root.winfo_exists()
        except Exception:
            exists = False
        assert not exists, "Root window should be destroyed"
    finally:
        try:
            if root.winfo_exists():
                root.destroy()
        except Exception:
            pass


def test_refresh_interval_uses_one_second(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure the dashboard schedules refreshes around the 1 Hz target."""

    def steady_reader() -> Dict[str, float | int | str]:
        return {
            "rpm": 900,
            "vehicle_speed_mph": 5.0,
            "coolant_temp_f": 175.0,
            "throttle_position_pct": 14.0,
            "engine_load_pct": 38.0,
            "timing_advance_deg": 1.0,
        }

    app, root = _make_app(monkeypatch, steady_reader)

    recorded: Dict[str, int] = {}

    def fake_after(delay: int, callback):
        recorded["delay"] = delay
        return "fake-after"

    monkeypatch.setattr(app.root, "after", fake_after)
    monkeypatch.setattr(app.root, "after_cancel", lambda _id: recorded.update(cancelled=_id))

    try:
        app.refresh_dashboard()
        assert recorded["delay"] == tk_dashboard.REFRESH_MS
    finally:
        app.stop()
        if root.winfo_exists():
            root.destroy()


def test_read_obd_live_accepts_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    """``_read_obd_live`` should reuse an injected OBD connection without closing it."""

    class FakeValue:
        def __init__(self, magnitude: float) -> None:
            self.magnitude = magnitude

    class FakeResponse:
        def __init__(self, magnitude: float) -> None:
            self.value = FakeValue(magnitude)

        def is_null(self) -> bool:
            return False

    class FakeCommands:
        RPM = "rpm"
        SPEED = "speed"
        COOLANT_TEMP = "coolant"
        THROTTLE_POS = "throttle"
        ENGINE_LOAD = "load"
        TIMING_ADVANCE = "timing"

    class FakeStatus:
        CAR_CONNECTED = "car-connected"

    class FakeConnection:
        def __init__(self) -> None:
            self.closed = False

        def status(self):
            return FakeStatus.CAR_CONNECTED

        def is_connected(self) -> bool:
            return True

        def query(self, command):
            mapping = {
                FakeCommands.RPM: FakeResponse(1500),
                FakeCommands.SPEED: FakeResponse(60 / 0.621371),
                FakeCommands.COOLANT_TEMP: FakeResponse((185 - 32) * 5 / 9),
                FakeCommands.THROTTLE_POS: FakeResponse(22.5),
                FakeCommands.ENGINE_LOAD: FakeResponse(48.8),
                FakeCommands.TIMING_ADVANCE: FakeResponse(6.4),
            }
            return mapping[command]

        def close(self) -> None:
            self.closed = True

    def _unused_obd(*_args, **_kwargs):
        raise AssertionError("OBD factory should not be used during tests")

    fake_obd = types.SimpleNamespace(
        commands=FakeCommands,
        OBDStatus=FakeStatus,
        OBD=_unused_obd,
    )

    monkeypatch.setitem(sys.modules, "obd", fake_obd)  # type: ignore[arg-type]

    connection = FakeConnection()

    result = data_manager._read_obd_live(connection)

    assert connection.closed is False
    assert result["engine_load_pct"] == pytest.approx(48.8, rel=1e-3)
    assert result["timing_advance_deg"] == pytest.approx(6.4, rel=1e-3)
