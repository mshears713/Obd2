"""Stage 1 Tkinter dashboard showing live OBD-II data."""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import TclError
from typing import Dict, Tuple

from data_manager import get_latest_reading
from main import generate_fake_reading

COLORS = {
    "bg": "#1e1e1e",
    "fg": "#f5f5f5",
    "sim": "#ffcc66",
    "rpm": "#ff5555",
    "bar_bg": "#2a2a2a",
}
FONT = "Consolas"
REFRESH_MS = 1000
FIELDS = [
    ("RPM", "rpm", "{:.0f}"),
    ("Speed (mph)", "vehicle_speed_mph", "{:.1f}"),
    ("Coolant Temp (°F)", "coolant_temp_f", "{:.1f}"),
    ("Throttle (%)", "throttle_position_pct", "{:.1f}"),
]
BAR_CONFIG: Dict[str, Tuple[float, str]] = {
    "Speed (mph)": (120.0, "#8be9fd"),
    "Throttle (%)": (100.0, "#50fa7b"),
}


def _clamp(value: float, low: float, high: float) -> float:
    """Keep a numeric value between two bounds."""

    return max(low, min(high, value))


def _coolant_to_color(temp_f: float) -> str:
    """Map coolant temperature to a readable blue→orange gradient."""

    cold_rgb = (97, 174, 239)
    hot_rgb = (255, 184, 108)
    ratio = (_clamp(temp_f, 140.0, 230.0) - 140.0) / (230.0 - 140.0)
    blended = [
        int(cold + (hot - cold) * ratio)
        for cold, hot in zip(cold_rgb, hot_rgb)
    ]
    return "#" + "".join(f"{channel:02x}" for channel in blended)


class DashboardApp:
    """Create the window, keep the labels updated, and handle shutdown."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("OBD-II Live Dashboard")
        self.root.geometry("540x360")
        self.root.configure(bg=COLORS["bg"])
        if hasattr(self.root, "minsize"):
            self.root.minsize(520, 340)
        if hasattr(self.root, "grid_rowconfigure"):
            self.root.grid_rowconfigure(1, weight=1)
        if hasattr(self.root, "grid_columnconfigure"):
            self.root.grid_columnconfigure(0, weight=1)

        self.value_labels: Dict[str, tk.Label] = {}
        self.bars: Dict[str, Tuple[object, int | None, float]] = {}
        self.sim_label: tk.Label
        self.status_label: tk.Label
        self.after_id: str | None = None
        self.frame_count = 0
        self.simulated_mode = False

        header = tk.Frame(root, bg=COLORS["bg"])
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        if hasattr(header, "grid_columnconfigure"):
            header.grid_columnconfigure(0, weight=1)
        tk.Label(
            header,
            text="Live OBD Data",
            font=(FONT, 20, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["fg"],
        ).grid(row=0, column=0, sticky="w")
        self.sim_label = tk.Label(
            header,
            text="",
            font=(FONT, 12),
            bg=COLORS["bg"],
            fg=COLORS["sim"],
        )
        self.sim_label.grid(row=0, column=1, sticky="e")

        body = tk.Frame(root, bg=COLORS["bg"])
        body.grid(row=1, column=0, sticky="nsew", padx=20)
        if hasattr(body, "grid_columnconfigure"):
            body.grid_columnconfigure(0, weight=1)
            body.grid_columnconfigure(1, weight=1)

        row_index = 0
        for title, _, _ in FIELDS:
            tk.Label(
                body,
                text=title,
                font=(FONT, 16),
                bg=COLORS["bg"],
                fg=COLORS["fg"],
            ).grid(row=row_index, column=0, sticky="w", pady=(0, 4))
            value = tk.Label(
                body,
                text="--",
                font=(FONT, 16, "bold"),
                bg=COLORS["bg"],
                fg=COLORS["fg"],
            )
            value.grid(row=row_index, column=1, sticky="e", pady=(0, 4))
            self.value_labels[title] = value

            if title in BAR_CONFIG:
                canvas_class = getattr(tk, "Canvas", None)
                if canvas_class is None:
                    canvas = tk.Frame(
                        body,
                        height=18,
                        bg=COLORS["bar_bg"],
                    )
                    bar_id = None
                else:
                    canvas = canvas_class(
                        body,
                        height=18,
                        bg=COLORS["bar_bg"],
                        highlightthickness=0,
                    )
                    bar_id = canvas.create_rectangle(
                        0, 0, 0, 18, fill=BAR_CONFIG[title][1], width=0
                    )
                canvas.grid(
                    row=row_index + 1,
                    column=0,
                    columnspan=2,
                    sticky="ew",
                    pady=(0, 12),
                )
                self.bars[title] = (canvas, bar_id, BAR_CONFIG[title][0])
                row_index += 2
            else:
                row_index += 1

        footer = tk.Frame(root, bg=COLORS["bg"])
        footer.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 20))
        if hasattr(footer, "grid_columnconfigure"):
            footer.grid_columnconfigure(0, weight=1)
        self.status_label = tk.Label(
            footer,
            text="Last update: -- | Source: -- | Refresh: -- ms",
            font=(FONT, 12),
            bg=COLORS["bg"],
            fg=COLORS["fg"],
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="ew")

        self._center_window()

    def start(self) -> None:
        """Hook up the close button and run the first refresh."""

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh_dashboard()

    def refresh_dashboard(self) -> None:
        """Refresh the labels once a second while keeping errors non-fatal."""

        self.frame_count += 1
        reading: Dict[str, float | int | str]
        simulated = False
        error: Exception | None = None
        source_hint = "CSV Replay"

        try:
            latest = get_latest_reading()
            if not latest:
                raise ValueError("No reading available from data manager.")
            reading = latest
            if isinstance(latest, dict) and isinstance(latest.get("source"), str):
                source_hint = latest["source"].title()
        except Exception as exc:  # pragma: no cover - relies on specific failure
            error = exc
            simulated = True
            try:
                reading = generate_fake_reading()
            except Exception as fallback_error:  # pragma: no cover - defensive
                print(f"[GUI] Fake data generator failed: {fallback_error}")
                reading = {
                    "rpm": 0,
                    "vehicle_speed_mph": 0.0,
                    "coolant_temp_f": 0.0,
                    "throttle_position_pct": 0.0,
                }
        else:
            reading = dict(reading)

        if simulated and not self.simulated_mode:
            print(f"[GUI] Switching to simulated mode: {error}")
        if not simulated and self.simulated_mode:
            print("[GUI] Live data restored; returning to real readings.")

        self.simulated_mode = simulated

        for title, key, fmt in FIELDS:
            raw = reading.get(key, 0) or 0
            try:
                value = float(raw)
                text = fmt.format(value)
            except (TypeError, ValueError):
                text = "--"
                value = 0.0
            label = self.value_labels[title]
            label.configure(text=text)

            if title == "RPM":
                label.configure(fg=COLORS["rpm"])
            elif title == "Coolant Temp (°F)":
                try:
                    label.configure(fg=_coolant_to_color(value))
                except (TypeError, ValueError):
                    label.configure(fg=COLORS["fg"])
            else:
                label.configure(fg=COLORS["fg"])

            if title in self.bars:
                self._update_bar(title, value)

        self.sim_label.configure(text="(Simulated Mode)" if simulated else "")
        data_source = "Simulated" if simulated else source_hint
        timestamp = time.strftime("%H:%M:%S")
        self.status_label.configure(
            text=(
                f"Last update: {timestamp} | "
                f"Source: {data_source} | "
                f"Refresh: {REFRESH_MS} ms"
            )
        )
        print(
            f"[GUI] Frame {self.frame_count} at {timestamp} (simulated={simulated})"
        )
        self.after_id = self.root.after(REFRESH_MS, self.refresh_dashboard)

    def stop(self) -> None:
        """Cancel any pending Tk callbacks so shutdown stays quiet."""

        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
            print("[GUI] Cancelled scheduled updates.")

    def on_close(self) -> None:
        """Handle the window close event cleanly."""

        self.stop()
        print("Dashboard closed cleanly.")
        self.root.destroy()

    def _update_bar(self, title: str, value: float) -> None:
        """Resize the simple bar to match the new sensor value."""

        canvas, bar_id, max_value = self.bars[title]
        if bar_id is None:
            return
        update = getattr(canvas, "update_idletasks", None)
        width_getter = getattr(canvas, "winfo_width", None)
        height_getter = getattr(canvas, "winfo_height", None)
        if not all(callable(fn) for fn in (update, width_getter, height_getter)):
            return
        update()
        width = max(width_getter(), 1)
        height = max(height_getter(), 1)
        fraction = _clamp(float(value), 0.0, max_value) / max_value
        canvas.coords(bar_id, 0, 0, fraction * width, height)

    def _center_window(self) -> None:
        """Place the window near the middle of the screen for readability."""

        try:
            self.root.update_idletasks()
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            x_pos = (self.root.winfo_screenwidth() - width) // 2
            y_pos = (self.root.winfo_screenheight() - height) // 3
            self.root.geometry(f"{width}x{height}+{x_pos}+{y_pos}")
        except (TclError, AttributeError):  # pragma: no cover - headless fallbacks
            pass


def main() -> None:
    """Launch the dashboard when run as a script."""

    root = tk.Tk()
    app = DashboardApp(root)
    app.start()
    root.mainloop()


if __name__ == "__main__":
    main()
