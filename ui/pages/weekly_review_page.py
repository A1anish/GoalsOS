"""Streamlined Weekly Review and Planning workflow page with sub-tabs."""

import tkinter as tk
from typing import Dict

from models.entities import WeeklyReview
from ui.app_controller import AppController
from ui.components.dialogs import TaskFormDialog
from ui.components.scrollable import ScrollableFrame


class WeeklyReviewPage(tk.Frame):
    """Spacious Weekly Review workflow with a dedicated Past Reviews Archive tab."""

    def __init__(self, parent: tk.Widget, controller: AppController) -> None:
        self.controller = controller
        p = controller.colors
        super().__init__(parent, bg=p["bg"])

        self.active_tab = tk.StringVar(value="new")  # 'new' or 'archive'
        self.goal_check_vars: Dict[str, tk.BooleanVar] = {}
        self.scroll = ScrollableFrame(self, bg=p["bg"])
        self.scroll.pack(fill="both", expand=True)
        self.render()

    def _set_tab(self, tab_key: str) -> None:
        self.active_tab.set(tab_key)
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
        reviews = self.controller.review_service.list_reviews()

        # Header + Tab Switcher
        header = tk.Frame(container, bg=p["bg"], padx=32, pady=20)
        header.pack(fill="x")

        left_h = tk.Frame(header, bg=p["bg"])
        left_h.pack(side="left")
        tk.Label(
            left_h,
            text="Weekly Review",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            left_h,
            text=f"Period: {summary['period_start']}  →  {summary['period_end']}",
            bg=p["bg"],
            fg=p["text_muted"],
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(anchor="w")

        tab_bar = tk.Frame(header, bg=p["surface"], padx=4, pady=4)
        tab_bar.pack(side="right")

        cur_tab = self.active_tab.get()
        for key, lbl in [
            ("new", "✦ Current Week Review"),
            ("archive", f"📂 Past Reviews ({len(reviews)})"),
        ]:
            is_sel = cur_tab == key
            tk.Button(
                tab_bar,
                text=lbl,
                bg=p["accent"] if is_sel else p["surface_alt"],
                fg="#FFFFFF" if is_sel else p["text_muted"],
                font=("Segoe UI", 9, "bold" if is_sel else "normal"),
                relief="flat",
                padx=14,
                pady=5,
                cursor="hand2",
                command=lambda k=key: self._set_tab(k),
            ).pack(side="left", padx=2)

        if cur_tab == "archive":
            arch_wrap = tk.Frame(container, bg=p["bg"], padx=32)
            arch_wrap.pack(fill="both", expand=True, pady=(0, 28))
            if not reviews:
                tk.Label(
                    arch_wrap,
                    text="No saved weekly reviews yet.",
                    bg=p["bg"],
                    fg=p["text_muted"],
                    font=("Segoe UI", 10),
                    pady=24,
                ).pack()
            else:
                for rev in reviews:
                    self._build_review_history_card(arch_wrap, rev)
            return

        # --- Step 1: Past 7 Days Snapshot ---
        step1 = tk.Frame(
            container,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=22,
            pady=18,
        )
        step1.pack(fill="x", padx=32, pady=(0, 18))

        tk.Label(
            step1,
            text="1. PAST 7 DAYS SNAPSHOT",
            bg=p["surface"],
            fg=p["accent"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 12))

        stats_grid = tk.Frame(step1, bg=p["surface"])
        stats_grid.pack(fill="x")
        for i in range(4):
            stats_grid.columnconfigure(i, weight=1, uniform="rev_stat")

        stat_items = [
            ("Tasks Completed", len(summary["completed_tasks"]), p["positive"]),
            ("Milestones Finished", len(summary["completed_milestones"]), p["accent"]),
            ("Still Open", len(summary["incomplete_tasks"]), p["info"]),
            ("Missed Deadlines", len(summary["missed_deadlines"]), p["danger"]),
        ]
        for idx, (lbl, val, col) in enumerate(stat_items):
            box = tk.Frame(stats_grid, bg=p["surface_alt"], padx=14, pady=10)
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

        # --- Step 2 & 3: Reflection & Next Week Priorities ---
        form_card = tk.Frame(
            container,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=24,
            pady=20,
        )
        form_card.pack(fill="x", padx=32, pady=(0, 28))

        tk.Label(
            form_card,
            text="2. REFLECT & PLAN NEXT WEEK",
            bg=p["surface"],
            fg=p["accent"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 10))

        grid_prompts = tk.Frame(form_card, bg=p["surface"])
        grid_prompts.pack(fill="x")
        grid_prompts.columnconfigure(0, weight=1, uniform="pr")
        grid_prompts.columnconfigure(1, weight=1, uniform="pr")

        c_left = tk.Frame(grid_prompts, bg=p["surface"])
        c_left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        c_right = tk.Frame(grid_prompts, bg=p["surface"])
        c_right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self.txt_well = self._add_prompt(c_left, "What went well this week?")
        self.txt_diff = self._add_prompt(
            c_right, "What was difficult or blocked progress?"
        )
        self.txt_learn = self._add_prompt(c_left, "What did I learn?")
        self.txt_change = self._add_prompt(
            c_right, "What should change next week?"
        )

        # Priority Goals Checkboxes
        tk.Label(
            form_card,
            text="Focus Goals for Next Week:",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(14, 6))

        goals_row = tk.Frame(form_card, bg=p["surface"])
        goals_row.pack(fill="x")
        for g in self.controller.goal_repo.list_all(status="active"):
            var = tk.BooleanVar(value=True)
            self.goal_check_vars[g.id] = var
            tk.Checkbutton(
                goals_row,
                text=f" {g.title}",
                variable=var,
                bg=p["surface"],
                fg=p["text"],
                selectcolor=p["surface_alt"],
                activebackground=p["surface"],
                activeforeground=p["text"],
                font=("Segoe UI", 9),
            ).pack(side="left", padx=(0, 16))

        self.txt_priorities = self._add_prompt(
            form_card, "Top 3 concrete commitments for next week:"
        )

        footer_btns = tk.Frame(form_card, bg=p["surface"], pady=10)
        footer_btns.pack(fill="x")

        tk.Button(
            footer_btns,
            text="+ Schedule New Task",
            bg=p["surface_alt"],
            fg=p["text"],
            font=("Segoe UI", 9),
            relief="flat",
            padx=14,
            pady=7,
            cursor="hand2",
            command=lambda: TaskFormDialog(self, self.controller),
        ).pack(side="left")

        tk.Button(
            footer_btns,
            text="✦ Save Weekly Review",
            bg=p["accent"],
            fg="#FFFFFF",
            activebackground=p["accent_hover"],
            activeforeground="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=20,
            pady=7,
            cursor="hand2",
            command=lambda s=summary: self._save_review(s),
        ).pack(side="right")

    def _add_prompt(self, parent: tk.Widget, label: str) -> tk.Text:
        p = self.controller.colors
        tk.Label(
            parent,
            text=label,
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(8, 4))
        txt = tk.Text(
            parent,
            height=3,
            bg=p["input_bg"],
            fg=p["text"],
            insertbackground=p["text"],
            highlightbackground=p["border"],
            highlightcolor=p["accent"],
            highlightthickness=1,
            relief="flat",
            font=("Segoe UI", 9),
            padx=8,
            pady=6,
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
        self.controller.show_toast("Saved Weekly Review!", "positive")
        self.active_tab.set("archive")
        self.controller.notify_data_changed("review_saved")

    def _build_review_history_card(
        self, parent: tk.Widget, rev: WeeklyReview
    ) -> None:
        p = self.controller.colors
        box = tk.Frame(
            parent,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=20,
            pady=16,
        )
        box.pack(fill="x", pady=(0, 12))

        tk.Label(
            box,
            text=f"Week of {rev.period_start}  →  {rev.period_end}",
            bg=p["surface"],
            fg=p["accent"],
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        for label, text in [
            ("Went well:", rev.went_well),
            ("Challenges:", rev.challenges),
            ("Lessons:", rev.lessons_learned),
            ("Next week adjustments:", rev.next_week_changes),
            ("Priorities:", rev.planned_priorities),
        ]:
            if text:
                tk.Label(
                    box,
                    text=f"{label}  {text}",
                    bg=p["surface"],
                    fg=p["text"],
                    font=("Segoe UI", 9),
                    anchor="w",
                    justify="left",
                    wraplength=880,
                ).pack(fill="x", pady=2)
