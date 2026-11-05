"""Unified My Goals page displaying all goals on a single screen."""

import tkinter as tk
from tkinter import ttk

from ui.app_controller import AppController
from ui.components.canvas_widgets import GoalCard
from ui.components.dialogs import GoalFormDialog
from ui.components.scrollable import ScrollableFrame


class GoalsPage(tk.Frame):
    """Displays all goals together on one single page in a spacious 2-column grid."""

    def __init__(self, parent: tk.Widget, controller: AppController) -> None:
        self.controller = controller
        p = controller.colors
        super().__init__(parent, bg=p["bg"])

        self.category_filter = tk.StringVar(value="All")
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

        # Header + Category Filter
        header = tk.Frame(container, bg=p["bg"], padx=32, pady=20)
        header.pack(fill="x")

        tk.Label(
            header,
            text="My Goals",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).pack(side="left")

        cats = ["All"] + self.controller.goal_repo.get_distinct_categories()
        cat_cb = ttk.Combobox(
            header,
            textvariable=self.category_filter,
            values=cats,
            state="readonly",
            width=18,
            font=("Segoe UI", 9),
        )
        cat_cb.pack(side="right")
        cat_cb.bind("<<ComboboxSelected>>", lambda _e: self.render())

        # All Goals Together on One Page (2 columns)
        goals = self.controller.goal_repo.list_all(
            status="all",
            category=self.category_filter.get(),
        )

        grid_frame = tk.Frame(container, bg=p["bg"], padx=32)
        grid_frame.pack(fill="both", expand=True, pady=(0, 28))
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
                text="No goals created yet",
                bg=p["surface"],
                fg=p["text"],
                font=("Segoe UI", 12, "bold"),
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
            ).pack(pady=(12, 0))
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
            )
            card.grid(
                row=r,
                column=c,
                sticky="nsew",
                padx=(0 if c == 0 else 10, 10 if c == 0 else 0),
                pady=(0, 16),
            )
