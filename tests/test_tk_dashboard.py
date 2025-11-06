"""Tests for the Stage 1 Tkinter dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the project root is importable when tests run from another directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Tkinter must be importable, otherwise skip the GUI-specific tests.
tk = pytest.importorskip("tkinter")

import tk_dashboard


class _FakeWidget:
    """Minimal stand-in for Tkinter widgets used during headless tests."""

    def __init__(self, master=None, **kwargs):
        self.master = master
        self.options = dict(kwargs)

    def pack(self, **kwargs) -> None:  # pragma: no cover - trivial bookkeeping
        self.options.update({f"pack_{k}": v for k, v in kwargs.items()})

    def grid(self, **kwargs) -> None:  # pragma: no cover - trivial bookkeeping
        self.options.update({f"grid_{k}": v for k, v in kwargs.items()})

    def configure(self, **kwargs) -> None:
        self.options.update(kwargs)

    def cget(self, key: str) -> str:
        return self.options.get(key, "")


class _FakeRoot(_FakeWidget):
    """Fake root window providing the subset of Tk methods we rely on."""

    def __init__(self):
        super().__init__()
        self.protocols: dict[str, object] = {}
        self.after_calls: dict[str, tuple[int, object]] = {}
        self.destroyed = False

    def title(self, *_args) -> None:  # pragma: no cover - no-op for tests
        pass

    def geometry(self, *_args) -> None:  # pragma: no cover - no-op for tests
        pass

    def configure(self, **_kwargs) -> None:  # pragma: no cover - no-op for tests
        pass

    def protocol(self, name: str, callback) -> None:
        self.protocols[name] = callback

    def after(self, delay: int, callback):
        token = f"after-{len(self.after_calls)}"
        self.after_calls[token] = (delay, callback)
        return token

    def after_cancel(self, token: str) -> None:
        self.after_calls.pop(token, None)

    def destroy(self) -> None:
        self.destroyed = True

    def withdraw(self) -> None:  # pragma: no cover - no-op for tests
        pass


class _FakeTkModule:
    """Namespace mimicking the subset of tkinter accessed by the dashboard."""

    LEFT = "left"
    BOTH = "both"

    Frame = _FakeWidget
    Label = _FakeWidget
    Tk = _FakeRoot


def _create_root(monkeypatch: pytest.MonkeyPatch | None = None) -> object:
    """Build a Tk root, falling back to fakes when the GUI display is missing."""

    try:
        root = tk.Tk()
    except tk.TclError:
        if monkeypatch is None:
            pytest.skip("Tkinter display not available")
        fake_tk = _FakeTkModule()
        monkeypatch.setattr(tk_dashboard, "tk", fake_tk)
        return fake_tk.Tk()
    root.withdraw()
    return root


def test_module_import_only() -> None:
    """Importing the dashboard should expose the DashboardApp class."""

    assert hasattr(tk_dashboard, "DashboardApp")


def test_refresh_updates_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    """One refresh should push the latest data into the labels."""

    root = _create_root(monkeypatch)
    app = tk_dashboard.DashboardApp(root)

    fake_reading = {
        "rpm": 2000,
        "vehicle_speed_mph": 55.5,
        "coolant_temp_f": 188.2,
        "throttle_position_pct": 22.5,
        "engine_load_pct": 46.0,
        "timing_advance_deg": 4.5,
    }
    monkeypatch.setattr(
        tk_dashboard, "get_latest_reading", lambda source="csv": fake_reading
    )
    monkeypatch.setattr(tk_dashboard, "generate_fake_reading", lambda: fake_reading)

    try:
        app.refresh_dashboard()
        assert app.value_labels["RPM"].cget("text") == "2000"
        assert app.value_labels["Speed (mph)"].cget("text") == "55.5"
        assert app.value_labels["Coolant Temp (°F)"].cget("text") == "188.2"
        assert app.value_labels["Throttle (%)"].cget("text") == "22.5"
        assert app.sim_label.cget("text") == ""
    finally:
        app.stop()
        root.destroy()


def test_on_close_cancels_after(monkeypatch: pytest.MonkeyPatch) -> None:
    """Closing the window should cancel scheduled callbacks and destroy the root."""

    root = _create_root(monkeypatch)
    app = tk_dashboard.DashboardApp(root)

    fake_reading = {
        "rpm": 1500,
        "vehicle_speed_mph": 33.3,
        "coolant_temp_f": 185.0,
        "throttle_position_pct": 18.2,
        "engine_load_pct": 42.0,
        "timing_advance_deg": 1.5,
    }
    monkeypatch.setattr(
        tk_dashboard, "get_latest_reading", lambda source="csv": fake_reading
    )

    callback_state: dict[str, object] = {}

    def fake_after(delay: int, callback):
        callback_state["delay"] = delay
        callback_state["callback"] = callback
        callback_state["token"] = "after-token"
        return "after-token"

    def fake_after_cancel(token: str) -> None:
        callback_state["cancelled"] = token

    monkeypatch.setattr(app.root, "after", fake_after)
    monkeypatch.setattr(app.root, "after_cancel", fake_after_cancel)

    original_destroy = app.root.destroy
    destroy_calls: list[bool] = []

    def fake_destroy() -> None:
        destroy_calls.append(True)
        original_destroy()

    monkeypatch.setattr(app.root, "destroy", fake_destroy)

    app.start()
    assert callback_state["token"] == "after-token"

    app.on_close()
    assert callback_state.get("cancelled") == "after-token"
    assert destroy_calls


