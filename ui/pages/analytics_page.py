"""Analytics page for GoalOS."""

import tkinter as tk

from ui.app_controller import AppController
from ui.components.canvas_widgets import (
    BarChartCanvas,
    DonutChartCanvas,
)
from ui.components.scrollable import ScrollableFrame


class AnalyticsPage(tk.Frame):
    """Clean analytics page with 2 visual charts: 7-Day Completed Tasks and Goal Distribution by Category."""

    def __init__(self, parent: tk.Widget, controller: AppController) -> None:
        self.controller = controller
        p = controller.colors
        super().__init__(parent, bg=p["bg"])

        self.scroll = ScrollableFrame(self, bg=p["bg"])
        self.scroll.pack(fill="both", expand=True)
        self.render()

    def render(self) -> None:
        p = self.controller.colors
        self.configure(bg=p["bg"])
        self.scroll.set_bg(p["bg"])
        container = self.scroll.inner

        for child in container.winfo_children():
            child.destroy()

        # Simple Header (No adjectives or extra range buttons)
        header = tk.Frame(container, bg=p["bg"], padx=32, pady=20)
        header.pack(fill="x")

        tk.Label(
            header,
            text="Analytics",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).pack(side="left")

        # --- 2 Visual Charts Side by Side ---
        charts_row = tk.Frame(container, bg=p["bg"], padx=32)
        charts_row.pack(fill="x", pady=(0, 20))
        charts_row.columnconfigure(0, weight=1, uniform="ch")
        charts_row.columnconfigure(1, weight=1, uniform="ch")

        # Chart 1: Daily Completed Tasks (7 Days)
        hist_card = tk.Frame(
            charts_row,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=20,
            pady=16,
        )
        hist_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        tk.Label(
            hist_card,
            text="COMPLETED TASKS (LAST 7 DAYS)",
            bg=p["surface"],
            fg=p["accent"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x")

        hist_raw = self.controller.analytics_service.get_completion_history(
            days=7
        )
        hist_chart_data = []
        for d_iso, cnt, mins in hist_raw:
            short_lbl = d_iso[5:]  # MM-DD
            hist_chart_data.append((short_lbl, float(cnt), f"{cnt} tasks ({mins}m)"))

        hist_chart = BarChartCanvas(
            hist_card, colors=p, height=240, bar_color=p["positive"]
        )
        hist_chart.pack(fill="x", pady=(10, 4))
        hist_chart.set_data(hist_chart_data)

        # Chart 2: Goal Distribution by Category
        cat_card = tk.Frame(
            charts_row,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=20,
            pady=16,
        )
        cat_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        tk.Label(
            cat_card,
            text="GOAL DISTRIBUTION BY CATEGORY",
            bg=p["surface"],
            fg=p["accent"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x")

        cat_dist = self.controller.analytics_service.get_category_distribution()
        cat_donut = DonutChartCanvas(
            cat_card, colors=p, height=240, center_title="Goals"
        )
        cat_donut.pack(fill="x", pady=(10, 4))
        cat_donut.set_segments(cat_dist)

