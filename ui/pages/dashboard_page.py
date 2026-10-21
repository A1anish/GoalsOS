"""Clean, spacious Dashboard page for GoalOS with segmented Focus tabs."""

from datetime import datetime
import tkinter as tk
from tkinter import ttk

from models.entities import Recommendation, Task
from ui.app_controller import AppController
from ui.components.canvas_widgets import (
    GoalCard,
    MetricCard,
    SmoothProgressBar,
)
from ui.components.dialogs import GoalFormDialog, TaskFormDialog
from ui.components.scrollable import ScrollableFrame
from utils.dates import format_duration, format_relative_deadline, today_iso


class DashboardPage(tk.Frame):
    """Streamlined landing dashboard combining summary cards, a tabbed Focus workspace,
    and active Goal cards without visual clutter.
    """

    def __init__(self, parent: tk.Widget, controller: AppController) -> None:
        self.controller = controller
        p = controller.colors
        super().__init__(parent, bg=p["bg"])

        self.focus_tab = tk.StringVar(value="recommended")  # 'recommended', 'today', 'milestones'
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

    def _switch_focus_tab(self, tab_key: str) -> None:
        self.focus_tab.set(tab_key)
        self.render()

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

        # --- LEFT COLUMN: Unified Focus Panel with Clean Segmented Tabs ---
        self._build_focus_workspace(left_col)

        # --- RIGHT COLUMN: Active Goals List ---
        self._build_active_goals_column(right_col)

    def _build_focus_workspace(self, parent: tk.Widget) -> None:
        p = self.controller.colors
        cur_tab = self.focus_tab.get()

        # Segmented Tab Header
        tab_bar = tk.Frame(parent, bg=p["bg"])
        tab_bar.pack(fill="x", pady=(0, 12))

        priorities = self.controller.analytics_service.get_todays_priorities()
        recs = self.controller.recommendation_service.get_recommendations(limit=3)

        tabs = [
            ("recommended", f"⚡ Next Best Actions ({len(recs)})"),
            ("today", f"☑ Today's Checklist ({len(priorities)})"),
            ("milestones", "◷ Milestones & Activity"),
        ]
        for key, label in tabs:
            is_sel = cur_tab == key
            tk.Button(
                tab_bar,
                text=label,
                bg=p["accent"] if is_sel else p["surface"],
                fg="#FFFFFF" if is_sel else p["text_muted"],
                font=("Segoe UI", 9, "bold" if is_sel else "normal"),
                relief="flat",
                padx=14,
                pady=6,
                cursor="hand2",
                command=lambda k=key: self._switch_focus_tab(k),
            ).pack(side="left", padx=(0, 8))

        panel = tk.Frame(
            parent,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=22,
            pady=20,
        )
        panel.pack(fill="both", expand=True)

        if cur_tab == "recommended":
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

        elif cur_tab == "today":
            # Quick Inline Add Task Bar
            self._build_quick_add_task_bar(panel)

            if not priorities:
                tk.Label(
                    panel,
                    text="No tasks due or scheduled for today.",
                    bg=p["surface"],
                    fg=p["text_muted"],
                    font=("Segoe UI", 10),
                    pady=24,
                ).pack()
            else:
                for t in priorities:
                    self._build_clean_task_row(panel, t)

        else:  # 'milestones'
            tk.Label(
                panel,
                text="UPCOMING MILESTONES",
                bg=p["surface"],
                fg=p["accent"],
                font=("Segoe UI", 9, "bold"),
                anchor="w",
            ).pack(fill="x", pady=(0, 8))

            ms = self.controller.analytics_service.get_upcoming_milestones(limit=4)
            if not ms:
                tk.Label(
                    panel,
                    text="No upcoming active milestones.",
                    bg=p["surface"],
                    fg=p["text_muted"],
                    font=("Segoe UI", 9),
                    pady=6,
                ).pack(anchor="w")
            else:
                for item in ms:
                    m = item["milestone"]
                    g = item["goal"]
                    stats = item["progress"]
                    dl_text, dl_state = format_relative_deadline(m.deadline)

                    m_box = tk.Frame(panel, bg=p["surface_alt"], padx=14, pady=10)
                    m_box.pack(fill="x", pady=(0, 8))

                    r1 = tk.Frame(m_box, bg=p["surface_alt"])
                    r1.pack(fill="x")
                    tk.Label(
                        r1,
                        text=m.title,
                        bg=p["surface_alt"],
                        fg=p["text"],
                        font=("Segoe UI", 10, "bold"),
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
                        text=f"{g.title}  •  {stats.status_label}",
                        bg=p["surface_alt"],
                        fg=p["text_muted"],
                        font=("Segoe UI", 8),
                        anchor="w",
                    ).pack(fill="x", pady=(2, 6))

                    SmoothProgressBar(
                        m_box,
                        percentage=stats.percentage,
                        height=5,
                        bg_color=p["surface_alt"],
                        track_color=p["track"],
                        fill_color=g.color or p["accent"],
                    ).pack(fill="x")

            tk.Label(
                panel,
                text="RECENT ACTIVITY",
                bg=p["surface"],
                fg=p["accent"],
                font=("Segoe UI", 9, "bold"),
                anchor="w",
            ).pack(fill="x", pady=(14, 8))

            for ev in self.controller.activity_repo.list_recent(limit=5):
                erow = tk.Frame(panel, bg=p["surface"], pady=3)
                erow.pack(fill="x")
                tk.Label(
                    erow,
                    text=f"•  {ev.description}",
                    bg=p["surface"],
                    fg=p["text_muted"],
                    font=("Segoe UI", 9),
                    anchor="w",
                ).pack(side="left")
                tk.Label(
                    erow,
                    text=ev.created_at[:10],
                    bg=p["surface"],
                    fg=p["text_dim"],
                    font=("Segoe UI", 8),
                ).pack(side="right")

    def _build_quick_add_task_bar(self, parent: tk.Widget) -> None:
        p = self.controller.colors
        projects = self.controller.goal_service.list_all_projects_with_context()
        if not projects:
            return

        bar = tk.Frame(parent, bg=p["surface_alt"], padx=10, pady=8)
        bar.pack(fill="x", pady=(0, 14))

        ent = tk.Entry(
            bar,
            bg=p["input_bg"],
            fg=p["text"],
            insertbackground=p["text"],
            highlightbackground=p["border"],
            highlightthickness=1,
            relief="flat",
            font=("Segoe UI", 9),
        )
        ent.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 8))
        ent.insert(0, "")

        def _quick_create(_e=None) -> None:
            title = ent.get().strip()
            if not title:
                return
            pid = projects[0][0]
            self.controller.task_service.create_task(
                project_id=pid,
                title=title,
                due_date=today_iso(),
                scheduled_date=today_iso(),
            )
            self.controller.show_toast(f"Added '{title}' for today!", "positive")
            self.controller.notify_data_changed("quick_task_added")

        ent.bind("<Return>", _quick_create)

        tk.Button(
            bar,
            text="+ Add for Today",
            bg=p["accent"],
            fg="#FFFFFF",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=_quick_create,
        ).pack(side="right")

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

    def _build_clean_task_row(self, parent: tk.Widget, t: Task) -> None:
        p = self.controller.colors
        is_comp = t.status == "completed"
        row = tk.Frame(parent, bg=p["surface_alt"], padx=12, pady=10)
        row.pack(fill="x", pady=(0, 6))

        chk = tk.Button(
            row,
            text="☑" if is_comp else "☐",
            bg=p["surface_alt"],
            fg=p["positive"] if is_comp else p["text_muted"],
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            command=lambda tid=t.id: self.controller.toggle_task_completion(tid),
        )
        chk.pack(side="left", padx=(0, 10))

        info = tk.Frame(row, bg=p["surface_alt"])
        info.pack(side="left", fill="x", expand=True)

        tk.Label(
            info,
            text=t.title,
            bg=p["surface_alt"],
            fg=p["text_muted"] if is_comp else p["text"],
            font=("Segoe UI", 10, "overstrike" if is_comp else "bold"),
            anchor="w",
        ).pack(fill="x")

        dl_lbl, dl_state = format_relative_deadline(t.due_date, is_completed=is_comp)
        tk.Label(
            info,
            text=f"{t.goal_title}   •   {dl_lbl}",
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
            padx=8,
            pady=2,
            cursor="hand2",
            command=lambda task_obj=t: TaskFormDialog(
                self, self.controller, task=task_obj
            ),
        ).pack(side="right")

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
                )
                gc.pack(fill="x", pady=(0, 12))
