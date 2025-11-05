"""Stage 1 Tkinter dashboard showing live OBD-II data."""

from __future__ import annotations

import time
import tkinter as tk
from typing import Dict

from data_manager import get_latest_reading
from main import generate_fake_reading

COLORS = {"bg": "#1e1e1e", "fg": "#f5f5f5", "sim": "#ffcc66"}
FONT = "Consolas"
FIELDS = [
    ("RPM", "rpm", "{:.0f}"),
    ("Speed (mph)", "vehicle_speed_mph", "{:.1f}"),
    ("Coolant Temp (°F)", "coolant_temp_f", "{:.1f}"),
    ("Throttle (%)", "throttle_position_pct", "{:.1f}"),
]


class DashboardApp:
    """Create the window, keep the labels updated, and handle shutdown."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("OBD-II Live Dashboard")
        self.root.geometry("500x300")
        self.root.configure(bg=COLORS["bg"])

        self.value_labels: Dict[str, tk.Label] = {}
        self.sim_label: tk.Label
        self.after_id: str | None = None

        header = tk.Frame(root, bg=COLORS["bg"])
        header.pack(pady=(20, 10))
        tk.Label(
            header,
            text="Live OBD Data",
            font=(FONT, 20, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)
        self.sim_label = tk.Label(
            header,
            text="",
            font=(FONT, 12),
            bg=COLORS["bg"],
            fg=COLORS["sim"],
        )
        self.sim_label.pack(side=tk.LEFT, padx=(10, 0))

        body = tk.Frame(root, bg=COLORS["bg"])
        body.pack(fill=tk.BOTH, expand=True)
        for row, (title, _, _) in enumerate(FIELDS):
            tk.Label(
                body,
                text=title,
                font=(FONT, 14),
                bg=COLORS["bg"],
                fg=COLORS["fg"],
            ).grid(row=row, column=0, sticky="w", padx=20, pady=6)
            value = tk.Label(
                body,
                text="--",
                font=(FONT, 14, "bold"),
                bg=COLORS["bg"],
                fg=COLORS["fg"],
            )
            value.grid(row=row, column=1, sticky="e", padx=20, pady=6)
            self.value_labels[title] = value

    def start(self) -> None:
        """Hook up the close button and run the first refresh."""

        # protocol() lets us intercept the window manager close button.
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh()

    def refresh(self) -> None:
        """Fetch the latest data, update labels, and schedule the next refresh."""

        try:
            reading = get_latest_reading() or {}
            simulated = False
        except Exception as error:  # pragma: no cover - defensive log
            print(f"[GUI] Using simulated data: {error}")
            reading = generate_fake_reading()
            simulated = True

        for title, key, fmt in FIELDS:
            raw = reading.get(key, 0) or 0
            try:
                text = fmt.format(float(raw))
            except (TypeError, ValueError):
                text = "--"
            self.value_labels[title].configure(text=text)

        self.sim_label.configure(text="(Simulated)" if simulated else "")
        print(f"[GUI] {time.strftime('%H:%M:%S')} update (simulated={simulated})")
        # after() asks Tk to call refresh in 1000 ms without blocking the event loop.
        self.after_id = self.root.after(1000, self.refresh)

    def stop(self) -> None:
        """Cancel any pending Tk callbacks so shutdown stays quiet."""

        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
            print("[GUI] Cancelled scheduled updates.")

    def on_close(self) -> None:
        """Handle the window close event cleanly."""

        self.stop()
        print("[GUI] Dashboard closed; exiting Tkinter loop.")
        self.root.destroy()


def main() -> None:
    """Launch the dashboard when run as a script."""

    root = tk.Tk()
    app = DashboardApp(root)
    app.start()
    root.mainloop()


if __name__ == "__main__":
    main()
