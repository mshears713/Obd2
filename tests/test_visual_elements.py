"""Sanity checks ensuring the styled dashboard builds its widgets."""

from __future__ import annotations

import tkinter as tk

import pytest

from tk_dashboard import BAR_CONFIG, DashboardApp, FIELDS


def test_dashboard_widgets_exist() -> None:
    """Ensure labels and bar canvases are present after init."""

    try:
        root = tk.Tk()
    except tk.TclError:  # pragma: no cover - depends on CI display support
        pytest.skip("Tkinter display is not available in this environment.")

    app = DashboardApp(root)

    for title, _, _ in FIELDS:
        assert title in app.value_labels
        assert isinstance(app.value_labels[title], tk.Label)

    for title in BAR_CONFIG:
        assert title in app.bars

    root.destroy()
