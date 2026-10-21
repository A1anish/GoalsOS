"""Progress Analytics and visual insights page for GoalOS."""

from datetime import datetime
import tkinter as tk

from ui.app_controller import AppController
from ui.components.canvas_widgets import (
    BarChartCanvas,
    DonutChartCanvas,
    SmoothProgressBar,
)
from ui.components.scrollable import ScrollableFrame
from utils.dates import format_duration


class AnalyticsPage(tk.Frame):
    """Visual analytics dashboard featuring pure Tkinter Canvas charts."""

    def __init__(self, parent: tk.Widget, controller: AppController) -> None:
        self.controller = controller
        p = controller.colors
        super().__init__(parent, bg=p["bg"])

        self.history_days = tk.IntVar(value=14)
        self.scroll = ScrollableFrame(self, bg=p["bg"])
        self.scroll.pack(fill="both", expand=True)
        self.render()

    def _set_days(self, days: int) -> None:
        self.history_days.set(days)
        self.render()

    def render(self) -> None:
        p = self.controller.colors
        self.configure(bg=p["bg"])
        self.scroll.set_bg(p["bg"])
        container = self.scroll.inner

        for child in container.winfo_children():
            child.destroy()

        # Header + Date Range Filter
        header = tk.Frame(container, bg=p["bg"], padx=26, pady=18)
        header.pack(fill="x")

        left_h = tk.Frame(header, bg=p["bg"])
        left_h.pack(side="left")
        tk.Label(
            left_h,
            text="Progress Analytics & Execution Insights",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            left_h,
            text="All metrics are computed live from your SQLite task completion timestamps and hierarchy.",
            bg=p["bg"],
            fg=p["text_muted"],
            font=("Segoe UI", 10),
            anchor="w",
        ).pack(anchor="w")

        range_bar = tk.Frame(header, bg=p["surface"], padx=4, pady=4)
        range_bar.pack(side="right")

        cur_days = self.history_days.get()
        for d_val, lbl in [(7, "7 Days"), (14, "14 Days"), (21, "21 Days")]:
            is_sel = cur_days == d_val
            tk.Button(
                range_bar,
                text=lbl,
                bg=p["accent"] if is_sel else p["surface_alt"],
                fg="#FFFFFF" if is_sel else p["text_muted"],
                font=("Segoe UI", 9, "bold" if is_sel else "normal"),
                relief="flat",
                padx=12,
                pady=4,
                cursor="hand2",
                command=lambda d=d_val: self._set_days(d),
            ).pack(side="left", padx=2)

        # --- Row 1: Goal Progress Leaderboard (Full Width) ---
        g_panel = tk.Frame(
            container,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=20,
            pady=16,
        )
        g_panel.pack(fill="x", padx=26, pady=(0, 16))

        mode_note = (
            "Effort-Weighted (by estimated task duration)"
            if self.controller.progress_service.is_effort_weighted()
            else "Equal Task Weighting (by completed eligible tasks)"
        )
        top_gp = tk.Frame(g_panel, bg=p["surface"])
        top_gp.pack(fill="x", pady=(0, 10))
        tk.Label(
            top_gp,
            text="A. ACTIVE GOAL PROGRESS BREAKDOWN",
            bg=p["surface"],
            fg=p["accent"],
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")
        tk.Label(
            top_gp,
            text=f"Calculation Mode: {mode_note}",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 8),
        ).pack(side="right")

        active_goals = self.controller.goal_repo.list_all(status="active")
        if not active_goals:
            tk.Label(
                g_panel,
                text="No active goals to analyze.",
                bg=p["surface"],
                fg=p["text_muted"],
                font=("Segoe UI", 9),
            ).pack(anchor="w")
        else:
            for g in active_goals:
                stats = self.controller.progress_service.get_goal_progress(g.id)
                feas = self.controller.analytics_service.analyze_goal_feasibility(g)

                r_frame = tk.Frame(g_panel, bg=p["surface"], pady=6)
                r_frame.pack(fill="x")

                lbl_row = tk.Frame(r_frame, bg=p["surface"])
                lbl_row.pack(fill="x", pady=(0, 4))
                tk.Label(
                    lbl_row,
                    text=f"{g.title}  ({g.category})",
                    bg=p["surface"],
                    fg=p["text"],
                    font=("Segoe UI", 10, "bold"),
                ).pack(side="left")

                tk.Label(
                    lbl_row,
                    text=f"{stats.status_label}   •   {feas['label']}",
                    bg=p["surface"],
                    fg=p["text_muted"],
                    font=("Segoe UI", 9, "bold"),
                ).pack(side="right")

                SmoothProgressBar(
                    r_frame,
                    percentage=stats.percentage,
                    height=8,
                    bg_color=p["surface"],
                    track_color=p["track"],
                    fill_color=g.color or p["accent"],
                ).pack(fill="x")

        # --- Row 2: Completion History Bar Chart + Workload Distribution Bar Chart ---
        charts_row1 = tk.Frame(container, bg=p["bg"], padx=26)
        charts_row1.pack(fill="x", pady=(0, 16))
        charts_row1.columnconfigure(0, weight=1, uniform="ch1")
        charts_row1.columnconfigure(1, weight=1, uniform="ch1")

        # B. Task Completion History
        hist_card = tk.Frame(
            charts_row1,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=18,
            pady=14,
        )
        hist_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        tk.Label(
            hist_card,
            text=f"B. DAILY COMPLETED TASKS (PAST {cur_days} DAYS)",
            bg=p["surface"],
            fg=p["accent"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x")

        hist_raw = self.controller.analytics_service.get_completion_history(
            days=cur_days
        )
        hist_chart_data = []
        for d_iso, cnt, mins in hist_raw:
            short_lbl = d_iso[5:]  # MM-DD
            hist_chart_data.append((short_lbl, float(cnt), f"{cnt} tasks ({mins}m)"))

        hist_chart = BarChartCanvas(
            hist_card, colors=p, height=220, bar_color=p["positive"]
        )
        hist_chart.pack(fill="x", pady=(8, 4))
        hist_chart.set_data(hist_chart_data)

        total_period_tasks = sum(cnt for _, cnt, _ in hist_raw)
        total_period_mins = sum(mins for _, _, mins in hist_raw)
        tk.Label(
            hist_card,
            text=f"Total completed in window: {total_period_tasks} task(s) ({format_duration(total_period_mins)} actual work)",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 8),
            anchor="w",
        ).pack(fill="x")

        # E. Daily Estimated Workload Distribution (Next 7 Days)
        work_card = tk.Frame(
            charts_row1,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=18,
            pady=14,
        )
        work_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        tk.Label(
            work_card,
            text="E. PLANNED WORKLOAD DISTRIBUTION (NEXT 7 DAYS, MINUTES)",
            bg=p["surface"],
            fg=p["accent"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x")

        workload = self.controller.analytics_service.get_workload_distribution(
            days=7
        )
        work_chart_data = []
        for d_iso, mins in workload["daily"]:
            dt_obj = datetime.strptime(d_iso, "%Y-%m-%d")
            lbl = dt_obj.strftime("%a %d")
            work_chart_data.append((lbl, float(mins), f"{mins}m"))

        work_chart = BarChartCanvas(
            work_card,
            colors=p,
            height=220,
            bar_color=p["info"],
            unit_suffix="m",
        )
        work_chart.pack(fill="x", pady=(8, 4))
        work_chart.set_data(work_chart_data)

        tk.Label(
            work_card,
            text=f"Overdue backlog: {format_duration(workload['overdue_minutes'])}   •   Unscheduled backlog: {format_duration(workload['unscheduled_minutes'])}   •   Later (>7d): {format_duration(workload['later_minutes'])}",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 8),
            anchor="w",
        ).pack(fill="x")

        # --- Row 3: Category Distribution Donut + Deadline Performance Donut ---
        charts_row2 = tk.Frame(container, bg=p["bg"], padx=26)
        charts_row2.pack(fill="x", pady=(0, 26))
        charts_row2.columnconfigure(0, weight=1, uniform="ch2")
        charts_row2.columnconfigure(1, weight=1, uniform="ch2")

        # C. Goal Distribution by Category
        cat_card = tk.Frame(
            charts_row2,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=18,
            pady=14,
        )
        cat_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        tk.Label(
            cat_card,
            text="C. GOAL DISTRIBUTION BY CATEGORY",
            bg=p["surface"],
            fg=p["accent"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x")

        cat_dist = self.controller.analytics_service.get_category_distribution()
        cat_donut = DonutChartCanvas(
            cat_card, colors=p, height=220, center_title="Goals"
        )
        cat_donut.pack(fill="x", pady=6)
        cat_donut.set_segments(cat_dist)

        # D. Deadline Performance
        dl_card = tk.Frame(
            charts_row2,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=18,
            pady=14,
        )
        dl_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        tk.Label(
            dl_card,
            text="D. DEADLINE PERFORMANCE & COMPLIANCE",
            bg=p["surface"],
            fg=p["accent"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x")

        perf = self.controller.analytics_service.get_deadline_performance()
        perf_items = [
            ("Completed On Time", perf["completed_on_time"]),
            ("Completed Late", perf["completed_late"]),
            ("Currently Overdue", perf["currently_overdue"]),
            ("On Track / Upcoming", perf["on_track"]),
        ]
        perf_colors = [
            p["positive"],
            p["warning"],
            p["danger"],
            p["info"],
        ]
        dl_donut = DonutChartCanvas(
            dl_card, colors=p, height=220, center_title="Tasks"
        )
        dl_donut.pack(fill="x", pady=6)
        dl_donut.set_segments(perf_items, custom_colors=perf_colors)
