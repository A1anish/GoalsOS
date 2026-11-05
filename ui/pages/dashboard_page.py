"""Clean, spacious Dashboard page for GoalOS."""

from datetime import datetime
import tkinter as tk
from tkinter import ttk

from models.entities import Recommendation
from ui.app_controller import AppController
from ui.components.canvas_widgets import (
    GoalCard,
    MetricCard,
)
from ui.components.dialogs import GoalFormDialog
from ui.components.scrollable import ScrollableFrame
from utils.dates import format_duration


class DashboardPage(tk.Frame):
    """Streamlined landing dashboard combining summary cards, Next Best Actions,
    and active Goal cards without visual clutter.
    """

    def __init__(self, parent: tk.Widget, controller: AppController) -> None:
        self.controller = controller
        p = controller.colors
        super().__init__(parent, bg=p["bg"])

        self.category_filter = tk.StringVar(value="All")
        self.scroll = ScrollableFrame(self, bg=p["bg"])
        self.scroll.pack(fill="both", expand=True)
        self.render()

    def _greeting(self) -> str:
        hr = datetime.now().hour
        if hr < 12:
            return "Good morning"
        if hr < 17:
            return "Good afternoon"
        return "Good evening"

    def render(self) -> None:
        p = self.controller.colors
        self.configure(bg=p["bg"])
        self.scroll.set_bg(p["bg"])
        container = self.scroll.inner

        for child in container.winfo_children():
            child.destroy()

        summary = self.controller.analytics_service.get_dashboard_summary()
        overall_prog = summary["overall_progress"]

        # --- Clean Greeting Header ---
        header = tk.Frame(container, bg=p["bg"], padx=32, pady=22)
        header.pack(fill="x")

        today_str = datetime.now().strftime("%A, %B %d")
        tk.Label(
            header,
            text=f"{self._greeting()}  •  {today_str}",
            bg=p["bg"],
            fg=p["accent"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            header,
            text="Here is your execution focus for today.",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        # --- 4 Spacious Summary Cards ---
        cards_row = tk.Frame(container, bg=p["bg"], padx=32)
        cards_row.pack(fill="x", pady=(0, 24))
        for i in range(4):
            cards_row.columnconfigure(i, weight=1, uniform="summary_cards")

        delta = summary["week_delta"]
        delta_str = (
            f"+{delta} vs last week"
            if delta > 0
            else (
                f"{delta} vs last week"
                if delta < 0
                else f"{summary['completed_last_week']} completed last week"
            )
        )
        overdue_cnt = summary["overdue_count"]
        due_sub = (
            f"{overdue_cnt} overdue  •  ~{format_duration(summary['due_today_minutes'])} today"
            if overdue_cnt > 0
            else f"~{format_duration(summary['due_today_minutes'])} scheduled today"
        )

        card_configs = [
            (
                "Overall Progress",
                f"{overall_prog.percentage:.0f}%",
                overall_prog.status_label,
                p["accent"],
                lambda: self.controller.navigate("analytics"),
            ),
            (
                "Due Today",
                str(summary["due_today_count"]),
                due_sub,
                p["danger"] if overdue_cnt > 0 else p["info"],
                lambda: self.controller.navigate(
                    "task_planner", planner_filter={"due": "today"}
                ),
            ),
            (
                "Completed This Week",
                str(summary["completed_this_week"]),
                delta_str,
                p["positive"],
                lambda: self.controller.navigate("analytics"),
            ),
            (
                "Active Goals",
                str(summary["active_goals_count"]),
                f"{summary['completed_goals_count']} completed all-time",
                p["warning"],
                lambda: self.controller.navigate("goals"),
            ),
        ]

        for idx, (title, val, sub, col, cmd) in enumerate(card_configs):
            mc = MetricCard(
                cards_row,
                title=title,
                value=val,
                subtitle=sub,
                accent_color=col,
                colors=p,
                on_click=cmd,
            )
            mc.grid(
                row=0,
                column=idx,
                sticky="nsew",
                padx=(0 if idx == 0 else 8, 0 if idx == 3 else 8),
            )

        # --- Main Two-Column Workspace ---
        split = tk.Frame(container, bg=p["bg"], padx=32)
        split.pack(fill="both", expand=True, pady=(0, 32))
        split.columnconfigure(0, weight=11)
        split.columnconfigure(1, weight=9)

        left_col = tk.Frame(split, bg=p["bg"])
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 14))

        right_col = tk.Frame(split, bg=p["bg"])
        right_col.grid(row=0, column=1, sticky="nsew", padx=(14, 0))

        # --- LEFT COLUMN: Next Best Actions ---
        self._build_focus_workspace(left_col)

        # --- RIGHT COLUMN: Active Goals List ---
        self._build_active_goals_column(right_col)

    def _build_focus_workspace(self, parent: tk.Widget) -> None:
        p = self.controller.colors
        recs = self.controller.recommendation_service.get_recommendations(limit=3)

        head_bar = tk.Frame(parent, bg=p["bg"])
        head_bar.pack(fill="x", pady=(0, 12))

        tk.Label(
            head_bar,
            text=f"⚡ Next Best Actions ({len(recs)})",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left")

        panel = tk.Frame(
            parent,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=22,
            pady=20,
        )
        panel.pack(fill="both", expand=True)

        tk.Label(
            panel,
            text="Recommended tasks to work on right now based on urgency, priority, and readiness:",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill="x", pady=(0, 14))

        if not recs:
            tk.Label(
                panel,
                text="🎉 You're all caught up! No urgent tasks need immediate attention.",
                bg=p["surface"],
                fg=p["text"],
                font=("Segoe UI", 11),
                pady=24,
            ).pack()
        else:
            for rec in recs:
                self._build_clean_rec_row(panel, rec)

    def _build_clean_rec_row(
        self, parent: tk.Widget, rec: Recommendation
    ) -> None:
        p = self.controller.colors
        t = rec.task
        card = tk.Frame(
            parent,
            bg=p["surface_alt"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=16,
            pady=14,
        )
        card.pack(fill="x", pady=(0, 10))

        top = tk.Frame(card, bg=p["surface_alt"])
        top.pack(fill="x")

        tk.Label(
            top,
            text=t.goal_title,
            bg=p["surface_alt"],
            fg=t.goal_color or p["accent"],
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left")

        tk.Label(
            top,
            text=f"  •  {format_duration(t.estimated_minutes)}",
            bg=p["surface_alt"],
            fg=p["text_muted"],
            font=("Segoe UI", 8),
        ).pack(side="left")

        tk.Button(
            top,
            text="✓ Complete",
            bg=p["positive"],
            fg="#FFFFFF",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=12,
            pady=3,
            cursor="hand2",
            command=lambda tid=t.id: self.controller.toggle_task_completion(tid),
        ).pack(side="right")

        tk.Label(
            card,
            text=t.title,
            bg=p["surface_alt"],
            fg=p["text"],
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(4, 2))

        why = "Recommended: " + ", ".join(rec.factors).capitalize() + "."
        tk.Label(
            card,
            text=why,
            bg=p["surface_alt"],
            fg=p["text_muted"],
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill="x")

    def _build_active_goals_column(self, parent: tk.Widget) -> None:
        p = self.controller.colors
        g_head = tk.Frame(parent, bg=p["bg"])
        g_head.pack(fill="x", pady=(0, 12))

        tk.Label(
            g_head,
            text="Active Goals",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left")

        cats = ["All"] + self.controller.goal_repo.get_distinct_categories()
        if len(cats) > 2:
            cat_cb = ttk.Combobox(
                g_head,
                textvariable=self.category_filter,
                values=cats,
                state="readonly",
                width=16,
            )
            cat_cb.pack(side="right")
            cat_cb.bind("<<ComboboxSelected>>", lambda _e: self.render())

        active_goals = self.controller.goal_repo.list_all(
            status="active",
            category=self.category_filter.get(),
        )

        if not active_goals:
            empty_g = tk.Frame(
                parent,
                bg=p["surface"],
                highlightbackground=p["border"],
                highlightthickness=1,
                padx=24,
                pady=32,
            )
            empty_g.pack(fill="x")
            tk.Label(
                empty_g,
                text="No active goals yet.",
                bg=p["surface"],
                fg=p["text"],
                font=("Segoe UI", 11, "bold"),
            ).pack()
            tk.Button(
                empty_g,
                text="+ Create Your First Goal",
                bg=p["accent"],
                fg="#FFFFFF",
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                padx=14,
                pady=6,
                cursor="hand2",
                command=lambda: GoalFormDialog(self, self.controller),
            ).pack(pady=(10, 0))
        else:
            for g in active_goals:
                g_stats = self.controller.progress_service.get_goal_progress(g.id)
                gc = GoalCard(
                    parent,
                    goal=g,
                    progress=g_stats,
                    colors=p,
                    on_open_detail=self.controller.open_goal_detail,
                    show_percentage=False,
                )
                gc.pack(fill="x", pady=(0, 12))
