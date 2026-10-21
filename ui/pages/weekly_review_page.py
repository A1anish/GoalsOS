"""Weekly Review and Planning workflow page for GoalOS."""

import tkinter as tk
from typing import Dict

from models.entities import WeeklyReview
from ui.app_controller import AppController
from ui.components.dialogs import TaskFormDialog
from ui.components.scrollable import ScrollableFrame


class WeeklyReviewPage(tk.Frame):
    """Guided 5-step Weekly Review workflow and historical review viewer."""

    def __init__(self, parent: tk.Widget, controller: AppController) -> None:
        self.controller = controller
        p = controller.colors
        super().__init__(parent, bg=p["bg"])

        self.goal_check_vars: Dict[str, tk.BooleanVar] = {}
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
        self.goal_check_vars.clear()

        summary = self.controller.review_service.get_past_week_summary()

        # Header
        header = tk.Frame(container, bg=p["bg"], padx=26, pady=18)
        header.pack(fill="x")

        tk.Label(
            header,
            text="Weekly Review & Next-Week Planning",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            header,
            text=f"Review Period: {summary['period_start']}  to  {summary['period_end']}   •   Evaluate outcomes, reflect, and lock in next week's priorities.",
            bg=p["bg"],
            fg=p["text_muted"],
            font=("Segoe UI", 10),
            anchor="w",
        ).pack(anchor="w")

        # --- STEP 1: Review the Previous Week (Summary Metrics) ---
        step1 = tk.Frame(
            container,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=20,
            pady=16,
        )
        step1.pack(fill="x", padx=26, pady=(0, 16))

        tk.Label(
            step1,
            text="STEP 1: PAST 7 DAYS EXECUTION SNAPSHOT",
            bg=p["surface"],
            fg=p["accent"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 10))

        stats_grid = tk.Frame(step1, bg=p["surface"])
        stats_grid.pack(fill="x")
        for i in range(5):
            stats_grid.columnconfigure(i, weight=1, uniform="rev_stat")

        stat_items = [
            ("Tasks Completed", len(summary["completed_tasks"]), p["positive"]),
            ("Still Incomplete", len(summary["incomplete_tasks"]), p["info"]),
            ("Milestones Finished", len(summary["completed_milestones"]), p["accent"]),
            ("Missed Deadlines", len(summary["missed_deadlines"]), p["danger"]),
            ("Stagnant Goals", len(summary["stagnant_goals"]), p["warning"]),
        ]
        for idx, (lbl, val, col) in enumerate(stat_items):
            box = tk.Frame(stats_grid, bg=p["surface_alt"], padx=12, pady=10)
            box.grid(row=0, column=idx, sticky="nsew", padx=4)
            tk.Label(
                box,
                text=str(val),
                bg=p["surface_alt"],
                fg=col,
                font=("Segoe UI", 18, "bold"),
            ).pack(anchor="w")
            tk.Label(
                box,
                text=lbl,
                bg=p["surface_alt"],
                fg=p["text_muted"],
                font=("Segoe UI", 8, "bold"),
            ).pack(anchor="w")

        if summary["stagnant_goals"] or summary["missed_deadlines"]:
            notes_row = tk.Frame(step1, bg=p["surface"], pady=8)
            notes_row.pack(fill="x")
            if summary["stagnant_goals"]:
                stag_names = ", ".join(g.title for g in summary["stagnant_goals"])
                tk.Label(
                    notes_row,
                    text=f"• Goals with 0 completed tasks this week: {stag_names}",
                    bg=p["surface"],
                    fg=p["warning"],
                    font=("Segoe UI", 9),
                    anchor="w",
                ).pack(fill="x")
            if summary["missed_deadlines"]:
                missed_names = ", ".join(
                    t.title for t in summary["missed_deadlines"][:4]
                )
                tk.Label(
                    notes_row,
                    text=f"• Overdue tasks needing attention: {missed_names}",
                    bg=p["surface"],
                    fg=p["danger"],
                    font=("Segoe UI", 9),
                    anchor="w",
                ).pack(fill="x")

        # --- Main Two-Column Area: Left = Steps 2–5 Form, Right = Past Reviews History ---
        split = tk.Frame(container, bg=p["bg"], padx=26)
        split.pack(fill="both", expand=True, pady=(0, 26))
        split.columnconfigure(0, weight=6)
        split.columnconfigure(1, weight=4)

        form_card = tk.Frame(
            split,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=20,
            pady=16,
        )
        form_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        hist_card = tk.Frame(
            split,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=20,
            pady=16,
        )
        hist_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # --- STEP 2: Reflect ---
        tk.Label(
            form_card,
            text="STEP 2: WEEKLY REFLECTION",
            bg=p["surface"],
            fg=p["accent"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        self.txt_well = self._add_prompt(
            form_card, "1. What went well this week?"
        )
        self.txt_diff = self._add_prompt(
            form_card, "2. What was difficult or blocked progress?"
        )
        self.txt_learn = self._add_prompt(
            form_card, "3. What did I learn?"
        )
        self.txt_change = self._add_prompt(
            form_card, "4. What should change next week?"
        )

        # --- STEP 3: Select Priority Goals for Next Week ---
        tk.Label(
            form_card,
            text="STEP 3: SELECT PRIORITY GOALS FOR NEXT WEEK",
            bg=p["surface"],
            fg=p["accent"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(14, 6))

        active_goals = self.controller.goal_repo.list_all(status="active")
        if not active_goals:
            tk.Label(
                form_card,
                text="No active goals available.",
                bg=p["surface"],
                fg=p["text_muted"],
                font=("Segoe UI", 9),
            ).pack(anchor="w")
        else:
            for g in active_goals:
                var = tk.BooleanVar(value=True)
                self.goal_check_vars[g.id] = var
                cb = tk.Checkbutton(
                    form_card,
                    text=f" {g.title} ({g.category} • {g.priority.upper()})",
                    variable=var,
                    bg=p["surface"],
                    fg=p["text"],
                    selectcolor=p["surface_alt"],
                    activebackground=p["surface"],
                    activeforeground=p["text"],
                    font=("Segoe UI", 9),
                    anchor="w",
                )
                cb.pack(fill="x", pady=1)

        # --- STEP 4: Plan Tasks & Commitments ---
        step4_head = tk.Frame(form_card, bg=p["surface"])
        step4_head.pack(fill="x", pady=(14, 4))
        tk.Label(
            step4_head,
            text="STEP 4: NEXT WEEK'S KEY COMMITMENTS & TASKS",
            bg=p["surface"],
            fg=p["accent"],
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")

        tk.Button(
            step4_head,
            text="+ Schedule New Task",
            bg=p["surface_alt"],
            fg=p["accent"],
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=lambda: TaskFormDialog(self, self.controller),
        ).pack(side="right")

        self.txt_priorities = self._add_prompt(
            form_card, "Outline your top 3 concrete outcomes for next week:"
        )

        # --- STEP 5: Save Review ---
        tk.Button(
            form_card,
            text="✦ Save Weekly Review",
            bg=p["accent"],
            fg="#FFFFFF",
            activebackground=p["accent_hover"],
            activeforeground="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2",
            command=lambda s=summary: self._save_review(s),
        ).pack(anchor="e", pady=(14, 0))

        # --- Right Column: Previous Weekly Reviews ---
        tk.Label(
            hist_card,
            text="PAST WEEKLY REVIEWS ARCHIVE",
            bg=p["surface"],
            fg=p["accent"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 10))

        reviews = self.controller.review_service.list_reviews()
        if not reviews:
            tk.Label(
                hist_card,
                text="No saved weekly reviews yet.",
                bg=p["surface"],
                fg=p["text_muted"],
                font=("Segoe UI", 9),
            ).pack(anchor="w")
        else:
            for rev in reviews:
                self._build_review_history_card(hist_card, rev)

    def _add_prompt(self, parent: tk.Widget, label: str) -> tk.Text:
        p = self.controller.colors
        tk.Label(
            parent,
            text=label,
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(6, 3))
        txt = tk.Text(
            parent,
            height=2,
            bg=p["input_bg"],
            fg=p["text"],
            insertbackground=p["text"],
            highlightbackground=p["border"],
            highlightcolor=p["accent"],
            highlightthickness=1,
            relief="flat",
            font=("Segoe UI", 9),
            padx=6,
            pady=5,
        )
        txt.pack(fill="x")
        return txt

    def _save_review(self, summary: Dict) -> None:
        selected_gids = [
            gid for gid, var in self.goal_check_vars.items() if var.get()
        ]
        self.controller.review_service.save_weekly_review(
            period_start=summary["period_start"],
            period_end=summary["period_end"],
            went_well=self.txt_well.get("1.0", "end"),
            challenges=self.txt_diff.get("1.0", "end"),
            lessons_learned=self.txt_learn.get("1.0", "end"),
            next_week_changes=self.txt_change.get("1.0", "end"),
            planned_priorities=self.txt_priorities.get("1.0", "end"),
            selected_goal_ids=selected_gids,
        )
        self.controller.show_toast(
            "Saved Weekly Review to local database!", "positive"
        )
        self.controller.notify_data_changed("review_saved")

    def _build_review_history_card(
        self, parent: tk.Widget, rev: WeeklyReview
    ) -> None:
        p = self.controller.colors
        box = tk.Frame(
            parent,
            bg=p["surface_alt"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=14,
            pady=10,
        )
        box.pack(fill="x", pady=(0, 10))

        tk.Label(
            box,
            text=f"Week: {rev.period_start} → {rev.period_end}",
            bg=p["surface_alt"],
            fg=p["accent"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x")

        if rev.went_well:
            tk.Label(
                box,
                text=f"✓ Went well: {rev.went_well}",
                bg=p["surface_alt"],
                fg=p["text"],
                font=("Segoe UI", 8),
                anchor="w",
                justify="left",
                wraplength=340,
            ).pack(fill="x", pady=(4, 2))

        if rev.challenges:
            tk.Label(
                box,
                text=f"⚠ Challenges: {rev.challenges}",
                bg=p["surface_alt"],
                fg=p["text_muted"],
                font=("Segoe UI", 8),
                anchor="w",
                justify="left",
                wraplength=340,
            ).pack(fill="x", pady=2)

        if rev.next_week_changes:
            tk.Label(
                box,
                text=f"↻ Adjustments: {rev.next_week_changes}",
                bg=p["surface_alt"],
                fg=p["text_muted"],
                font=("Segoe UI", 8),
                anchor="w",
                justify="left",
                wraplength=340,
            ).pack(fill="x", pady=2)

        if rev.planned_priorities:
            tk.Label(
                box,
                text=f"★ Priorities:\n{rev.planned_priorities}",
                bg=p["surface_alt"],
                fg=p["positive"],
                font=("Segoe UI", 8, "bold"),
                anchor="w",
                justify="left",
                wraplength=340,
            ).pack(fill="x", pady=(4, 0))
