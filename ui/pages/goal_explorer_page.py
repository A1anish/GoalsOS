"""Hierarchical Goal Builder & Visual Explorer page (Treeview + Interactive Canvas)."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, Optional, Tuple

from ui.app_controller import AppController
from ui.components.canvas_widgets import InteractiveGoalTreeCanvas
from ui.components.dialogs import (
    GoalFormDialog,
    MilestoneFormDialog,
    ProjectFormDialog,
    TaskFormDialog,
)


class GoalExplorerPage(tk.Frame):
    """Synchronized Treeview and Interactive Canvas node hierarchy builder."""

    def __init__(self, parent: tk.Widget, controller: AppController) -> None:
        self.controller = controller
        p = controller.colors
        super().__init__(parent, bg=p["bg"])

        self.selected_entity: Optional[Tuple[str, str]] = None  # (type, id)
        self._goal_choices: list = []
        self._tree_item_map: Dict[str, Tuple[str, str]] = {}
        self.render()

    def render(self) -> None:
        p = self.controller.colors
        self.configure(bg=p["bg"])
        for child in self.winfo_children():
            child.destroy()
        self._tree_item_map.clear()

        goals = [
            g
            for g in self.controller.goal_repo.list_all()
            if g.status != "archived"
        ]
        self._goal_choices = [(g.id, f"{g.title} ({g.status.upper()})") for g in goals]

        if not self.controller.selected_goal_id and goals:
            self.controller.selected_goal_id = goals[0].id

        cur_goal_id = self.controller.selected_goal_id
        hierarchy = (
            self.controller.goal_service.get_full_hierarchy(cur_goal_id)
            if cur_goal_id
            else None
        )

        # --- Top Control Header ---
        header = tk.Frame(self, bg=p["bg"], padx=24, pady=14)
        header.pack(fill="x")

        left_h = tk.Frame(header, bg=p["bg"])
        left_h.pack(side="left")

        tk.Label(
            left_h,
            text="Hierarchical Goal Explorer & Builder",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 16, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            left_h,
            text="Synchronized Tree Editor & Interactive Node-Graph Canvas (Goal → Milestone → Project → Task)",
            bg=p["bg"],
            fg=p["text_muted"],
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(anchor="w")

        right_h = tk.Frame(header, bg=p["bg"])
        right_h.pack(side="right")

        tk.Label(
            right_h,
            text="Select Goal:",
            bg=p["bg"],
            fg=p["text_muted"],
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(0, 8))

        self.goal_combo = ttk.Combobox(
            right_h,
            values=[lbl for _, lbl in self._goal_choices],
            state="readonly",
            width=34,
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
        self.goal_combo.pack(side="left", padx=(0, 10))
        self.goal_combo.bind("<<ComboboxSelected>>", self._on_goal_selected)

        tk.Button(
            right_h,
            text="+ New Goal",
            bg=p["accent"],
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: GoalFormDialog(
                self,
                self.controller,
                on_saved=lambda g: self.controller.open_goal_explorer(g.id),
            ),
        ).pack(side="left")

        if not hierarchy:
            empty = tk.Frame(self, bg=p["surface"], padx=30, pady=50)
            empty.pack(fill="both", expand=True, padx=24, pady=20)
            tk.Label(
                empty,
                text="No active goal available to explore.",
                bg=p["surface"],
                fg=p["text"],
                font=("Segoe UI", 12, "bold"),
            ).pack()
            return

        # --- Action Toolbar for Adding / Reordering Entities ---
        action_bar = tk.Frame(
            self,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=16,
            pady=8,
        )
        action_bar.pack(fill="x", padx=24, pady=(0, 12))

        tk.Button(
            action_bar,
            text="+ Add Milestone",
            bg=p["accent"],
            fg="#FFFFFF",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._add_milestone,
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            action_bar,
            text="+ Add Project",
            bg=p["surface_alt"],
            fg=p["text"],
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._add_project,
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            action_bar,
            text="+ Add Task",
            bg=p["surface_alt"],
            fg=p["text"],
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._add_task,
        ).pack(side="left", padx=(0, 14))

        tk.Button(
            action_bar,
            text="↑ Move Up",
            bg=p["surface_alt"],
            fg=p["text_muted"],
            font=("Segoe UI", 8),
            relief="flat",
            padx=8,
            pady=4,
            command=lambda: self._reorder_selected(-1),
        ).pack(side="left", padx=(0, 4))

        tk.Button(
            action_bar,
            text="↓ Move Down",
            bg=p["surface_alt"],
            fg=p["text_muted"],
            font=("Segoe UI", 8),
            relief="flat",
            padx=8,
            pady=4,
            command=lambda: self._reorder_selected(1),
        ).pack(side="left", padx=(0, 12))

        tk.Button(
            action_bar,
            text="Expand All",
            bg=p["surface_alt"],
            fg=p["text_muted"],
            font=("Segoe UI", 8),
            relief="flat",
            padx=8,
            pady=4,
            command=lambda: self._set_tree_expansion(True),
        ).pack(side="left", padx=(0, 4))

        tk.Button(
            action_bar,
            text="Collapse All",
            bg=p["surface_alt"],
            fg=p["text_muted"],
            font=("Segoe UI", 8),
            relief="flat",
            padx=8,
            pady=4,
            command=lambda: self._set_tree_expansion(False),
        ).pack(side="left")

        # Right side of Action Bar: Selected Node Inspector Actions
        self.inspector_lbl = tk.Label(
            action_bar,
            text="Select any node in the Tree or Canvas to inspect",
            bg=p["surface"],
            fg=p["accent"],
            font=("Segoe UI", 9, "bold"),
        )
        self.inspector_lbl.pack(side="right", padx=(10, 0))

        tk.Button(
            action_bar,
            text="✕ Delete",
            bg=p["surface_alt"],
            fg=p["danger"],
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=4,
            cursor="hand2",
            command=self._delete_selected,
        ).pack(side="right", padx=3)

        tk.Button(
            action_bar,
            text="✎ Edit Selected",
            bg=p["surface_alt"],
            fg=p["text"],
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=4,
            cursor="hand2",
            command=self._edit_selected,
        ).pack(side="right", padx=3)

        tk.Button(
            action_bar,
            text="✓ Complete / Reopen Task",
            bg=p["positive"],
            fg="#FFFFFF",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._toggle_selected_task,
        ).pack(side="right", padx=3)

        # --- Synchronized Split Workspace (Left: Treeview, Right: Interactive Canvas) ---
        split = tk.Frame(self, bg=p["bg"], padx=24)
        split.pack(fill="both", expand=True, pady=(0, 18))
        split.columnconfigure(0, weight=4)
        split.columnconfigure(1, weight=6)
        split.rowconfigure(0, weight=1)

        # Left Pane: ttk.Treeview
        tree_panel = tk.Frame(
            split,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
        )
        tree_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        tree_head = tk.Frame(tree_panel, bg=p["surface_alt"], padx=12, pady=6)
        tree_head.pack(fill="x")
        tk.Label(
            tree_head,
            text="HIERARCHY TREE VIEW",
            bg=p["surface_alt"],
            fg=p["text_muted"],
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left")

        tree_body = tk.Frame(tree_panel, bg=p["surface"])
        tree_body.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            tree_body,
            columns=("type", "progress", "due"),
            show="tree headings",
            selectmode="browse",
        )
        self.tree.heading("#0", text="Entity Title", anchor="w")
        self.tree.heading("type", text="Level", anchor="w")
        self.tree.heading("progress", text="Progress / Status", anchor="w")
        self.tree.heading("due", text="Deadline", anchor="w")

        self.tree.column("#0", width=230, minwidth=160)
        self.tree.column("type", width=75, stretch=False)
        self.tree.column("progress", width=110, stretch=False)
        self.tree.column("due", width=85, stretch=False)

        vsb = ttk.Scrollbar(
            tree_body, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._populate_tree(hierarchy)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", lambda _e: self._on_tree_double_click())

        # Right Pane: Interactive Canvas Node Graph
        canvas_panel = tk.Frame(
            split,
            bg=p["canvas_bg"],
            highlightbackground=p["border"],
            highlightthickness=1,
        )
        canvas_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.graph_canvas = InteractiveGoalTreeCanvas(
            canvas_panel,
            colors=p,
            on_select_node=self._on_canvas_select_node,
            on_double_click_node=self._on_canvas_double_click_node,
        )
        self.graph_canvas.pack(fill="both", expand=True)
        self.graph_canvas.set_hierarchy(hierarchy, self.selected_entity)

    def _populate_tree(self, hierarchy: Dict) -> None:
        g = hierarchy["goal"]
        g_prog = hierarchy["progress"]
        g_iid = f"goal:{g.id}"
        self._tree_item_map[g_iid] = ("goal", g.id)

        self.tree.insert(
            "",
            "end",
            iid=g_iid,
            text=f"◎ {g.title}",
            values=("Goal", f"{g_prog.percentage:.0f}%", g.deadline or "—"),
            open=True,
        )

        for m_node in hierarchy["milestones"]:
            m = m_node["milestone"]
            m_prog = m_node["progress"]
            m_iid = f"milestone:{m.id}"
            self._tree_item_map[m_iid] = ("milestone", m.id)

            self.tree.insert(
                g_iid,
                "end",
                iid=m_iid,
                text=f"◆ {m.title}",
                values=(
                    "Milestone",
                    f"{m_prog.percentage:.0f}% ({m_prog.completed_tasks}/{m_prog.total_eligible_tasks})",
                    m.deadline or "—",
                ),
                open=True,
            )

            for p_node in m_node["projects"]:
                proj = p_node["project"]
                p_prog = p_node["progress"]
                p_iid = f"project:{proj.id}"
                self._tree_item_map[p_iid] = ("project", proj.id)

                self.tree.insert(
                    m_iid,
                    "end",
                    iid=p_iid,
                    text=f"▣ {proj.title}",
                    values=(
                        "Project",
                        f"{p_prog.percentage:.0f}% ({p_prog.completed_tasks}/{p_prog.total_eligible_tasks})",
                        proj.deadline or "—",
                    ),
                    open=True,
                )

                for t in p_node["tasks"]:
                    t_iid = f"task:{t.id}"
                    self._tree_item_map[t_iid] = ("task", t.id)
                    icon = "☑" if t.status == "completed" else "☐"
                    self.tree.insert(
                        p_iid,
                        "end",
                        iid=t_iid,
                        text=f"{icon} {t.title}",
                        values=(
                            "Task",
                            t.status.replace("_", " ").title(),
                            t.due_date or "—",
                        ),
                    )

    def _on_goal_selected(self, _event: tk.Event) -> None:
        idx = self.goal_combo.current()
        if 0 <= idx < len(self._goal_choices):
            self.controller.selected_goal_id = self._goal_choices[idx][0]
            self.selected_entity = ("goal", self.controller.selected_goal_id)
            self.render()

    def _on_tree_select(self, _event: tk.Event) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        if iid in self._tree_item_map:
            etype, eid = self._tree_item_map[iid]
            self.selected_entity = (etype, eid)
            self._update_inspector_label(etype, eid)
            self.graph_canvas.selected_key = (etype, eid)
            self.graph_canvas.render()

    def _on_canvas_select_node(self, etype: str, eid: str) -> None:
        self.selected_entity = (etype, eid)
        self._update_inspector_label(etype, eid)
        iid = f"{etype}:{eid}"
        if self.tree.exists(iid):
            self.tree.selection_set(iid)
            self.tree.see(iid)

    def _on_canvas_double_click_node(self, etype: str, eid: str) -> None:
        self.selected_entity = (etype, eid)
        if etype == "task":
            self.controller.toggle_task_completion(eid)
        else:
            self._edit_selected()

    def _on_tree_double_click(self) -> None:
        if not self.selected_entity:
            return
        etype, eid = self.selected_entity
        if etype == "task":
            self.controller.toggle_task_completion(eid)
        else:
            self._edit_selected()

    def _update_inspector_label(self, etype: str, eid: str) -> None:
        if etype == "goal":
            g = self.controller.goal_repo.get_by_id(eid)
            title = g.title if g else eid
        elif etype == "milestone":
            m = self.controller.milestone_repo.get_by_id(eid)
            title = m.title if m else eid
        elif etype == "project":
            pr = self.controller.project_repo.get_by_id(eid)
            title = pr.title if pr else eid
        else:
            t = self.controller.task_repo.get_by_id(eid)
            title = t.title if t else eid
        self.inspector_lbl.configure(
            text=f"Selected {etype.upper()}: {title[:32]}"
        )

    def _set_tree_expansion(self, expand: bool) -> None:
        def recurse(item: str) -> None:
            self.tree.item(item, open=expand)
            for child in self.tree.get_children(item):
                recurse(child)

        for root_item in self.tree.get_children(""):
            recurse(root_item)

    def _add_milestone(self) -> None:
        gid = self.controller.selected_goal_id
        if gid:
            MilestoneFormDialog(self, self.controller, goal_id=gid)

    def _add_project(self) -> None:
        gid = self.controller.selected_goal_id
        if not gid:
            return
        mid = None
        if self.selected_entity:
            etype, eid = self.selected_entity
            if etype == "milestone":
                mid = eid
            elif etype == "project":
                p = self.controller.project_repo.get_by_id(eid)
                mid = p.milestone_id if p else None
        if not mid:
            ms = self.controller.milestone_repo.list_by_goal(gid)
            if not ms:
                messagebox.showinfo(
                    "Create Milestone First",
                    "Please add a Milestone to this Goal before adding a Project.",
                )
                return
            mid = ms[0].id
        ProjectFormDialog(self, self.controller, milestone_id=mid, goal_id=gid)

    def _add_task(self) -> None:
        pid = None
        if self.selected_entity:
            etype, eid = self.selected_entity
            if etype == "project":
                pid = eid
            elif etype == "task":
                t = self.controller.task_repo.get_by_id(eid)
                pid = t.project_id if t else None
            elif etype == "milestone":
                projs = self.controller.project_repo.list_by_milestone(eid)
                if projs:
                    pid = projs[0].id
        TaskFormDialog(self, self.controller, project_id=pid)

    def _toggle_selected_task(self) -> None:
        if not self.selected_entity or self.selected_entity[0] != "task":
            messagebox.showinfo(
                "Select a Task",
                "Select a Task node in the tree or canvas to toggle its completion status.",
            )
            return
        self.controller.toggle_task_completion(self.selected_entity[1])

    def _edit_selected(self) -> None:
        if not self.selected_entity:
            return
        etype, eid = self.selected_entity
        if etype == "goal":
            g = self.controller.goal_repo.get_by_id(eid)
            if g:
                GoalFormDialog(self, self.controller, goal=g)
        elif etype == "milestone":
            m = self.controller.milestone_repo.get_by_id(eid)
            if m:
                MilestoneFormDialog(
                    self, self.controller, goal_id=m.goal_id, milestone=m
                )
        elif etype == "project":
            pr = self.controller.project_repo.get_by_id(eid)
            if pr:
                ProjectFormDialog(
                    self,
                    self.controller,
                    milestone_id=pr.milestone_id,
                    goal_id=self.controller.selected_goal_id,
                    project=pr,
                )
        elif etype == "task":
            t = self.controller.task_repo.get_by_id(eid)
            if t:
                TaskFormDialog(self, self.controller, task=t)

    def _reorder_selected(self, direction: int) -> None:
        if not self.selected_entity:
            return
        etype, eid = self.selected_entity
        if etype == "milestone":
            self.controller.goal_service.reorder_milestone(eid, direction)
            self.controller.notify_data_changed("reordered")
        elif etype == "project":
            self.controller.goal_service.reorder_project(eid, direction)
            self.controller.notify_data_changed("reordered")
        elif etype == "task":
            self.controller.task_service.reorder_task(eid, direction)
            self.controller.notify_data_changed("reordered")

    def _delete_selected(self) -> None:
        if not self.selected_entity:
            return
        etype, eid = self.selected_entity
        if not messagebox.askyesno(
            f"Delete {etype.title()}",
            f"Are you sure you want to delete this {etype} and any child items under it?",
        ):
            return
        if etype == "goal":
            self.controller.goal_service.delete_goal(eid)
            self.controller.selected_goal_id = None
        elif etype == "milestone":
            self.controller.goal_service.delete_milestone(eid)
        elif etype == "project":
            self.controller.goal_service.delete_project(eid)
        elif etype == "task":
            self.controller.task_service.delete_task(eid)
        self.selected_entity = None
        self.controller.notify_data_changed("entity_deleted")
