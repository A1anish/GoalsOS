"""Dashboard page implementation for GoalOS."""

from datetime import datetime
import tkinter as tk
from tkinter import ttk
from typing import Optional

from models.entities import Recommendation, Task
from ui.app_controller import AppController
from ui.components.canvas_widgets import (
    GoalCard,
    MetricCard,
    SmoothProgressBar,
)
from ui.components.dialogs import GoalFormDialog, TaskFormDialog
from ui.components.scrollable import ScrollableFrame
from utils.dates import format_duration, format_relative_deadline


class DashboardPage(tk.Frame):
    """Main landing dashboard displaying summary cards, Next Best Action,
    active goals, today's priorities, upcoming milestones, and activity log.
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

        # --- SECTION A: Welcome Header ---
        header = tk.Frame(container, bg=p["bg"], padx=26, pady=18)
        header.pack(fill="x")

        left_h = tk.Frame(header, bg=p["bg"])
        left_h.pack(side="left", fill="x", expand=True)

        today_str = datetime.now().strftime("%A, %B %d, %Y")
        tk.Label(
            left_h,
            text=f"{self._greeting()}  •  {today_str}",
            bg=p["bg"],
            fg=p["accent"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            left_h,
            text="Execution Command Center",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(2, 2))

        tk.Label(
            left_h,
            text=f"You have {summary['active_goals_count']} active goal(s), {summary['due_today_count']} task(s) scheduled or due today, and {overall_prog.percentage:.0f}% overall completion.",
            bg=p["bg"],
            fg=p["text_muted"],
            font=("Segoe UI", 10),
            anchor="w",
        ).pack(fill="x")

        right_h = tk.Frame(header, bg=p["bg"])
        right_h.pack(side="right")

        tk.Button(
            right_h,
            text="+ Quick Task",
            bg=p["surface"],
            fg=p["text"],
            highlightbackground=p["border"],
            highlightthickness=1,
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=7,
            cursor="hand2",
            command=lambda: TaskFormDialog(self, self.controller),
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            right_h,
            text="+ Create Goal",
            bg=p["accent"],
            fg="#FFFFFF",
            activebackground=p["accent_hover"],
            activeforeground="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=16,
            pady=7,
            cursor="hand2",
            command=lambda: GoalFormDialog(self, self.controller),
        ).pack(side="left")

        # --- SECTION B: 5 Summary Cards ---
        cards_row = tk.Frame(container, bg=p["bg"], padx=26)
        cards_row.pack(fill="x", pady=(0, 18))
        for i in range(5):
            cards_row.columnconfigure(i, weight=1, uniform="summary_cards")

        delta = summary["week_delta"]
        delta_str = (
            f"+{delta} vs last week"
            if delta > 0
            else (
                f"{delta} vs last week"
                if delta < 0
                else f"Same as last week ({summary['completed_last_week']})"
            )
        )

        card_configs = [
            (
                "Active Goals",
                str(summary["active_goals_count"]),
                f"{summary['completed_goals_count']} completed total",
                p["accent"],
                lambda: self.controller.navigate("goals"),
            ),
            (
                "Completed This Week",
                str(summary["completed_this_week"]),
                delta_str,
                p["positive"],
                lambda: self.controller.navigate("analytics"),
            ),
            (
                "Tasks Due Today",
                str(summary["due_today_count"]),
                f"~{format_duration(summary['due_today_minutes'])} est. workload",
                p["info"],
                lambda: self.controller.navigate(
                    "task_planner", planner_filter={"due": "today"}
                ),
            ),
            (
                "Overdue Tasks",
                str(summary["overdue_count"]),
                "Action required"
                if summary["overdue_count"] > 0
                else "Zero overdue work!",
                p["danger"] if summary["overdue_count"] > 0 else p["positive"],
                lambda: self.controller.navigate(
                    "task_planner", planner_filter={"due": "overdue"}
                ),
            ),
            (
                "Overall Progress",
                f"{overall_prog.percentage:.0f}%",
                overall_prog.status_label,
                p["warning"]
                if overall_prog.percentage < 50
                else p["positive"],
                lambda: self.controller.navigate("analytics"),
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
                padx=(0 if idx == 0 else 6, 0 if idx == 4 else 6),
            )

        # --- SECTION C: Next Best Action (Recommendation Engine) ---
        recs = self.controller.recommendation_service.get_recommendations(limit=3)
        rec_panel = tk.Frame(
            container,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=20,
            pady=14,
        )
        rec_panel.pack(fill="x", padx=26, pady=(0, 18))

        rec_header = tk.Frame(rec_panel, bg=p["surface"])
        rec_header.pack(fill="x", pady=(0, 10))
        tk.Label(
            rec_header,
            text="⚡ NEXT BEST ACTIONS (RECOMMENDATION ENGINE)",
            bg=p["surface"],
            fg=p["accent"],
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")
        tk.Label(
            rec_header,
            text="Scored by Deadline Urgency (40%) + Task Priority (30%) + Goal Importance (20%) + Readiness (10%)",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 8),
        ).pack(side="right")

        if not recs:
            tk.Label(
                rec_panel,
                text="All caught up! No active uncompleted tasks require immediate action right now.",
                bg=p["surface"],
                fg=p["text_muted"],
                font=("Segoe UI", 10),
                pady=8,
            ).pack(anchor="w")
        else:
            rec_grid = tk.Frame(rec_panel, bg=p["surface"])
            rec_grid.pack(fill="x")
            for i in range(len(recs)):
                rec_grid.columnconfigure(i, weight=1, uniform="recs")

            for idx, rec in enumerate(recs):
                self._build_recommendation_card(rec_grid, rec, idx)

        # --- SECTION D & E: Main Two-Column Workspace ---
        split = tk.Frame(container, bg=p["bg"], padx=26)
        split.pack(fill="both", expand=True, pady=(0, 24))
        split.columnconfigure(0, weight=5)
        split.columnconfigure(1, weight=4)

        left_col = tk.Frame(split, bg=p["bg"])
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        right_col = tk.Frame(split, bg=p["bg"])
        right_col.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # Left Column: Active Goals Overview
        g_head = tk.Frame(left_col, bg=p["bg"])
        g_head.pack(fill="x", pady=(0, 10))
        tk.Label(
            g_head,
            text="Active Goals Overview",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left")

        cats = ["All"] + self.controller.goal_repo.get_distinct_categories()
        cat_cb = ttk.Combobox(
            g_head,
            textvariable=self.category_filter,
            values=cats,
            state="readonly",
            width=18,
        )
        cat_cb.pack(side="right")
        cat_cb.bind("<<ComboboxSelected>>", lambda _e: self.render())

        tk.Label(
            g_head,
            text="Category:",
            bg=p["bg"],
            fg=p["text_muted"],
            font=("Segoe UI", 9),
        ).pack(side="right", padx=(0, 6))

        active_goals = self.controller.goal_repo.list_all(
            status="active",
            category=self.category_filter.get(),
        )

        if not active_goals:
            empty_g = tk.Frame(
                left_col,
                bg=p["surface"],
                highlightbackground=p["border"],
                highlightthickness=1,
                padx=24,
                pady=32,
            )
            empty_g.pack(fill="x")
            tk.Label(
                empty_g,
                text="No active goals match this filter.",
                bg=p["surface"],
                fg=p["text"],
                font=("Segoe UI", 11, "bold"),
            ).pack()
            tk.Label(
                empty_g,
                text="Create a long-term goal and break it down into milestones, projects, and actionable tasks.",
                bg=p["surface"],
                fg=p["text_muted"],
                font=("Segoe UI", 9),
                pady=6,
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
            ).pack(pady=(6, 0))
        else:
            for g in active_goals:
                g_stats = self.controller.progress_service.get_goal_progress(g.id)
                gc = GoalCard(
                    left_col,
                    goal=g,
                    progress=g_stats,
                    colors=p,
                    on_open_detail=self.controller.open_goal_detail,
                    on_open_explorer=self.controller.open_goal_explorer,
                )
                gc.pack(fill="x", pady=(0, 12))

        # Right Column Panel 1: Today's Priorities
        self._build_todays_priorities_panel(right_col)

        # Right Column Panel 2: Upcoming Milestones
        self._build_upcoming_milestones_panel(right_col)

        # Right Column Panel 3: Recent Activity Summary
        self._build_recent_activity_panel(right_col)

    def _build_recommendation_card(
        self, parent: tk.Widget, rec: Recommendation, col_idx: int
    ) -> None:
        p = self.controller.colors
        t = rec.task
        card = tk.Frame(
            parent,
            bg=p["surface_alt"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=14,
            pady=12,
        )
        card.grid(
            row=0,
            column=col_idx,
            sticky="nsew",
            padx=(0 if col_idx == 0 else 6, 0 if col_idx == 2 else 6),
        )

        top = tk.Frame(card, bg=p["surface_alt"])
        top.pack(fill="x")
        tk.Label(
            top,
            text=f"SCORE {rec.total_score:.0f}/100",
            bg=p["accent"],
            fg="#FFFFFF",
            font=("Segoe UI", 8, "bold"),
            padx=6,
            pady=1,
        ).pack(side="left")

        tk.Label(
            top,
            text=f"{format_duration(t.estimated_minutes)}",
            bg=p["surface_alt"],
            fg=p["text_muted"],
            font=("Segoe UI", 8, "bold"),
        ).pack(side="right")

        tk.Label(
            card,
            text=t.title,
            bg=p["surface_alt"],
            fg=p["text"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            justify="left",
            wraplength=290,
        ).pack(fill="x", pady=(6, 2))

        tk.Label(
            card,
            text=f"Goal: {t.goal_title}",
            bg=p["surface_alt"],
            fg=t.goal_color or p["accent"],
            font=("Segoe UI", 8, "bold"),
            anchor="w",
        ).pack(fill="x")

        why_text = "Why: " + ", ".join(rec.factors).capitalize() + "."
        tk.Label(
            card,
            text=why_text,
            bg=p["surface_alt"],
            fg=p["text_muted"],
            font=("Segoe UI", 8),
            anchor="w",
            justify="left",
            wraplength=290,
        ).pack(fill="x", pady=(4, 8))

        act_row = tk.Frame(card, bg=p["surface_alt"])
        act_row.pack(fill="x")

        tk.Button(
            act_row,
            text="✓ Complete",
            bg=p["positive"],
            fg="#FFFFFF",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=lambda tid=t.id: self.controller.toggle_task_completion(tid),
        ).pack(side="left")

        tk.Button(
            act_row,
            text="Open Goal →",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 8),
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=lambda gid=t.goal_id: self.controller.open_goal_detail(gid),
        ).pack(side="right")

    def _build_todays_priorities_panel(self, parent: tk.Widget) -> None:
        p = self.controller.colors
        panel = tk.Frame(
            parent,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=16,
            pady=14,
        )
        panel.pack(fill="x", pady=(0, 14))

        head = tk.Frame(panel, bg=p["surface"])
        head.pack(fill="x", pady=(0, 10))
        tk.Label(
            head,
            text="Today's Priorities & Overdue",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left")

        tk.Button(
            head,
            text="Open Planner →",
            bg=p["surface_alt"],
            fg=p["accent"],
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=lambda: self.controller.navigate("task_planner"),
        ).pack(side="right")

        tasks = self.controller.analytics_service.get_todays_priorities()
        if not tasks:
            tk.Label(
                panel,
                text="No tasks due or scheduled for today.",
                bg=p["surface"],
                fg=p["text_muted"],
                font=("Segoe UI", 9),
                pady=10,
            ).pack(anchor="w")
            return

        for t in tasks[:8]:
            self._build_priority_task_row(panel, t)

    def _build_priority_task_row(self, parent: tk.Widget, t: Task) -> None:
        p = self.controller.colors
        is_comp = t.status == "completed"
        row = tk.Frame(
            parent,
            bg=p["surface_alt"],
            padx=10,
            pady=7,
        )
        row.pack(fill="x", pady=3)

        chk_btn = tk.Button(
            row,
            text="☑" if is_comp else "☐",
            bg=p["surface_alt"],
            fg=p["positive"] if is_comp else p["text_muted"],
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            command=lambda tid=t.id: self.controller.toggle_task_completion(tid),
        )
        chk_btn.pack(side="left", padx=(0, 6))

        info = tk.Frame(row, bg=p["surface_alt"])
        info.pack(side="left", fill="x", expand=True)

        tk.Label(
            info,
            text=t.title,
            bg=p["surface_alt"],
            fg=p["text_muted"] if is_comp else p["text"],
            font=(
                "Segoe UI",
                9,
                "overstrike" if is_comp else "bold",
            ),
            anchor="w",
        ).pack(fill="x")

        dl_lbl, dl_state = format_relative_deadline(t.due_date, is_completed=is_comp)
        tk.Label(
            info,
            text=f"{t.goal_title} › {t.project_title}  •  {dl_lbl}",
            bg=p["surface_alt"],
            fg=p.get(dl_state, p["text_muted"])
            if dl_state == "danger"
            else p["text_muted"],
            font=("Segoe UI", 8),
            anchor="w",
        ).pack(fill="x")

        tk.Button(
            row,
            text="Edit",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 8),
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=lambda task_obj=t: TaskFormDialog(
                self, self.controller, task=task_obj
            ),
        ).pack(side="right")

    def _build_upcoming_milestones_panel(self, parent: tk.Widget) -> None:
        p = self.controller.colors
        panel = tk.Frame(
            parent,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=16,
            pady=14,
        )
        panel.pack(fill="x", pady=(0, 14))

        head = tk.Frame(panel, bg=p["surface"])
        head.pack(fill="x", pady=(0, 8))
        tk.Label(
            head,
            text="Upcoming Milestones",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left")

        tk.Button(
            head,
            text="Timeline →",
            bg=p["surface_alt"],
            fg=p["accent"],
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=lambda: self.controller.navigate("timeline"),
        ).pack(side="right")

        items = self.controller.analytics_service.get_upcoming_milestones(limit=5)
        if not items:
            tk.Label(
                panel,
                text="No upcoming active milestones.",
                bg=p["surface"],
                fg=p["text_muted"],
                font=("Segoe UI", 9),
                pady=8,
            ).pack(anchor="w")
            return

        for item in items:
            m = item["milestone"]
            g = item["goal"]
            stats = item["progress"]
            dl_text, dl_state = format_relative_deadline(m.deadline)

            m_box = tk.Frame(panel, bg=p["surface_alt"], padx=10, pady=8)
            m_box.pack(fill="x", pady=3)

            r1 = tk.Frame(m_box, bg=p["surface_alt"])
            r1.pack(fill="x")
            tk.Label(
                r1,
                text=m.title,
                bg=p["surface_alt"],
                fg=p["text"],
                font=("Segoe UI", 9, "bold"),
            ).pack(side="left")
            tk.Label(
                r1,
                text=dl_text,
                bg=p["surface_alt"],
                fg=p.get(dl_state, p["text_muted"]),
                font=("Segoe UI", 8, "bold"),
            ).pack(side="right")

            tk.Label(
                m_box,
                text=f"Goal: {g.title}  •  {stats.status_label}",
                bg=p["surface_alt"],
                fg=p["text_muted"],
                font=("Segoe UI", 8),
                anchor="w",
            ).pack(fill="x", pady=(2, 4))

            SmoothProgressBar(
                m_box,
                percentage=stats.percentage,
                height=5,
                bg_color=p["surface_alt"],
                track_color=p["track"],
                fill_color=g.color or p["accent"],
            ).pack(fill="x")

    def _build_recent_activity_panel(self, parent: tk.Widget) -> None:
        p = self.controller.colors
        panel = tk.Frame(
            parent,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=16,
            pady=14,
        )
        panel.pack(fill="x")

        tk.Label(
            panel,
            text="Recent Execution Activity",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        events = self.controller.activity_repo.list_recent(limit=6)
        if not events:
            tk.Label(
                panel,
                text="No activity recorded yet.",
                bg=p["surface"],
                fg=p["text_muted"],
                font=("Segoe UI", 9),
            ).pack(anchor="w")
            return

        for ev in events:
            erow = tk.Frame(panel, bg=p["surface"], pady=3)
            erow.pack(fill="x")
            dot_col = (
                p["positive"]
                if "completed" in ev.action
                else (p["accent"] if "created" in ev.action else p["info"])
            )
            tk.Label(
                erow,
                text="●",
                bg=p["surface"],
                fg=dot_col,
                font=("Segoe UI", 8),
            ).pack(side="left", padx=(0, 6))
            tk.Label(
                erow,
                text=ev.description,
                bg=p["surface"],
                fg=p["text"],
                font=("Segoe UI", 8),
                anchor="w",
            ).pack(side="left", fill="x", expand=True)
            tk.Label(
                erow,
                text=ev.created_at[:10],
                bg=p["surface"],
                fg=p["text_dim"],
                font=("Segoe UI", 8),
            ).pack(side="right")
