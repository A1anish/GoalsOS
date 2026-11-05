"""Clean Visual Goal Explorer page for GoalOS."""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ui.app_controller import AppController
from ui.components.canvas_widgets import InteractiveGoalTreeCanvas


class GoalExplorerPage(tk.Frame):
    """Full-width Visual Goal Hierarchy Canvas."""

    def __init__(self, parent: tk.Widget, controller: AppController) -> None:
        self.controller = controller
        p = controller.colors
        super().__init__(parent, bg=p["bg"])

        self._goal_choices: list = []
        self.graph_canvas: Optional[InteractiveGoalTreeCanvas] = None
        self.render()

    def render(self) -> None:
        p = self.controller.colors
        self.configure(bg=p["bg"])
        for child in self.winfo_children():
            child.destroy()
        self.graph_canvas = None

        goals = [
            g
            for g in self.controller.goal_repo.list_all()
            if g.status != "archived"
        ]
        self._goal_choices = [(g.id, g.title) for g in goals]

        if not self.controller.selected_goal_id and goals:
            self.controller.selected_goal_id = goals[0].id

        cur_goal_id = self.controller.selected_goal_id
        hierarchy = (
            self.controller.goal_service.get_full_hierarchy(cur_goal_id)
            if cur_goal_id
            else None
        )

        # --- Clean Header with Goal Selector Only ---
        header = tk.Frame(self, bg=p["bg"], padx=32, pady=18)
        header.pack(fill="x")

        tk.Label(
            header,
            text="Goal Explorer",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).pack(side="left", padx=(0, 16))

        self.goal_combo = ttk.Combobox(
            header,
            values=[lbl for _, lbl in self._goal_choices],
            state="readonly",
            width=36,
            font=("Segoe UI", 10),
        )
        if self._goal_choices:
            idx = next(
                (
                    i
                    for i, (gid, _) in enumerate(self._goal_choices)
                    if gid == cur_goal_id
                ),
                0,
            )
            self.goal_combo.current(idx)
        self.goal_combo.pack(side="left")
        self.goal_combo.bind("<<ComboboxSelected>>", self._on_goal_selected)

        if not hierarchy:
            empty = tk.Frame(self, bg=p["surface"], padx=30, pady=50)
            empty.pack(fill="both", expand=True, padx=32, pady=20)
            tk.Label(
                empty,
                text="No active goal available to explore.",
                bg=p["surface"],
                fg=p["text"],
                font=("Segoe UI", 12, "bold"),
            ).pack()
            return

        # --- Full-Width Visual Canvas ---
        workspace = tk.Frame(self, bg=p["bg"], padx=32)
        workspace.pack(fill="both", expand=True, pady=(0, 24))

        canvas_panel = tk.Frame(
            workspace,
            bg=p["canvas_bg"],
            highlightbackground=p["border"],
            highlightthickness=1,
        )
        canvas_panel.pack(fill="both", expand=True)

        self.graph_canvas = InteractiveGoalTreeCanvas(
            canvas_panel,
            colors=p,
            on_double_click_node=self._on_double_click_node,
        )
        self.graph_canvas.pack(fill="both", expand=True)
        self.graph_canvas.set_hierarchy(hierarchy)

    def _on_goal_selected(self, _event: tk.Event) -> None:
        idx = self.goal_combo.current()
        if 0 <= idx < len(self._goal_choices):
            self.controller.selected_goal_id = self._goal_choices[idx][0]
            self.render()

    def _on_double_click_node(self, etype: str, eid: str) -> None:
        if etype == "task":
            self.controller.toggle_task_completion(eid)
