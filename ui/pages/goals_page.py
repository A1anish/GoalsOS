"""My Goals list and filter page for GoalOS."""

import tkinter as tk
from tkinter import ttk

from ui.app_controller import AppController
from ui.components.canvas_widgets import GoalCard
from ui.components.dialogs import GoalFormDialog
from ui.components.scrollable import ScrollableFrame


class GoalsPage(tk.Frame):
    """Displays active, paused, completed, and archived goals in a responsive card grid."""

    def __init__(self, parent: tk.Widget, controller: AppController) -> None:
        self.controller = controller
        p = controller.colors
        super().__init__(parent, bg=p["bg"])

        self.status_filter = tk.StringVar(value="active")
        self.category_filter = tk.StringVar(value="All")
        self.search_var = tk.StringVar(value="")

        self.scroll = ScrollableFrame(self, bg=p["bg"])
        self.scroll.pack(fill="both", expand=True)
        self.render()

    def _set_status_tab(self, status: str) -> None:
        self.status_filter.set(status)
        self.render()

    def render(self) -> None:
        p = self.controller.colors
        self.configure(bg=p["bg"])
        self.scroll.set_bg(p["bg"])
        container = self.scroll.inner

        for child in container.winfo_children():
            child.destroy()

        # Header
        header = tk.Frame(container, bg=p["bg"], padx=26, pady=18)
        header.pack(fill="x")

        left_h = tk.Frame(header, bg=p["bg"])
        left_h.pack(side="left", fill="x", expand=True)
        tk.Label(
            left_h,
            text="My Goals Portfolio",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            left_h,
            text="Manage long-term outcomes, track progress across milestones, or pause and archive goals.",
            bg=p["bg"],
            fg=p["text_muted"],
            font=("Segoe UI", 10),
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        tk.Button(
            header,
            text="+ Create New Goal",
            bg=p["accent"],
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
            command=lambda: GoalFormDialog(self, self.controller),
        ).pack(side="right")

        # Filter & Status Tabs Bar
        filter_bar = tk.Frame(
            container,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=16,
            pady=10,
        )
        filter_bar.pack(fill="x", padx=26, pady=(0, 18))

        tabs_frame = tk.Frame(filter_bar, bg=p["surface"])
        tabs_frame.pack(side="left")

        all_goals_unfiltered = self.controller.goal_repo.list_all()
        counts = {
            "active": sum(1 for g in all_goals_unfiltered if g.status == "active"),
            "paused": sum(1 for g in all_goals_unfiltered if g.status == "paused"),
            "completed": sum(1 for g in all_goals_unfiltered if g.status == "completed"),
            "archived": sum(1 for g in all_goals_unfiltered if g.status == "archived"),
            "all": len(all_goals_unfiltered),
        }

        cur_status = self.status_filter.get()
        for key, label in [
            ("active", f"Active ({counts['active']})"),
            ("paused", f"Paused ({counts['paused']})"),
            ("completed", f"Completed ({counts['completed']})"),
            ("archived", f"Archived ({counts['archived']})"),
            ("all", f"All ({counts['all']})"),
        ]:
            is_sel = cur_status == key
            tk.Button(
                tabs_frame,
                text=label,
                bg=p["accent"] if is_sel else p["surface_alt"],
                fg="#FFFFFF" if is_sel else p["text_muted"],
                font=("Segoe UI", 9, "bold" if is_sel else "normal"),
                relief="flat",
                padx=12,
                pady=5,
                cursor="hand2",
                command=lambda k=key: self._set_status_tab(k),
            ).pack(side="left", padx=(0, 6))

        # Right side filters: Search & Category
        right_f = tk.Frame(filter_bar, bg=p["surface"])
        right_f.pack(side="right")

        cats = ["All"] + self.controller.goal_repo.get_distinct_categories()
        cat_cb = ttk.Combobox(
            right_f,
            textvariable=self.category_filter,
            values=cats,
            state="readonly",
            width=18,
        )
        cat_cb.pack(side="right")
        cat_cb.bind("<<ComboboxSelected>>", lambda _e: self.render())

        tk.Label(
            right_f,
            text="Category:",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 9),
        ).pack(side="right", padx=(12, 6))

        search_ent = tk.Entry(
            right_f,
            textvariable=self.search_var,
            bg=p["input_bg"],
            fg=p["text"],
            insertbackground=p["text"],
            highlightbackground=p["border"],
            highlightthickness=1,
            relief="flat",
            width=22,
            font=("Segoe UI", 9),
        )
        search_ent.pack(side="right", ipady=4)
        search_ent.bind("<Return>", lambda _e: self.render())

        tk.Label(
            right_f,
            text="Search:",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 9),
        ).pack(side="right", padx=(0, 6))

        # Goal Cards Grid (2 columns)
        goals = self.controller.goal_repo.list_all(
            status=cur_status,
            category=self.category_filter.get(),
            search=self.search_var.get(),
        )

        grid_frame = tk.Frame(container, bg=p["bg"], padx=26)
        grid_frame.pack(fill="both", expand=True, pady=(0, 24))
        grid_frame.columnconfigure(0, weight=1, uniform="gcards")
        grid_frame.columnconfigure(1, weight=1, uniform="gcards")

        if not goals:
            empty = tk.Frame(
                grid_frame,
                bg=p["surface"],
                highlightbackground=p["border"],
                highlightthickness=1,
                padx=30,
                pady=40,
            )
            empty.grid(row=0, column=0, columnspan=2, sticky="ew")
            tk.Label(
                empty,
                text="No goals found in this view",
                bg=p["surface"],
                fg=p["text"],
                font=("Segoe UI", 12, "bold"),
            ).pack()
            tk.Label(
                empty,
                text="Try switching status tabs or create a new long-term goal to start planning.",
                bg=p["surface"],
                fg=p["text_muted"],
                font=("Segoe UI", 9),
                pady=6,
            ).pack()
            tk.Button(
                empty,
                text="+ Create Goal",
                bg=p["accent"],
                fg="#FFFFFF",
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                padx=14,
                pady=6,
                cursor="hand2",
                command=lambda: GoalFormDialog(self, self.controller),
            ).pack(pady=(8, 0))
            return

        for idx, g in enumerate(goals):
            r = idx // 2
            c = idx % 2
            prog = self.controller.progress_service.get_goal_progress(g.id)
            card = GoalCard(
                grid_frame,
                goal=g,
                progress=prog,
                colors=p,
                on_open_detail=self.controller.open_goal_detail,
                on_open_explorer=self.controller.open_goal_explorer,
            )
            card.grid(
                row=r,
                column=c,
                sticky="nsew",
                padx=(0 if c == 0 else 8, 8 if c == 0 else 0),
                pady=(0, 14),
            )
