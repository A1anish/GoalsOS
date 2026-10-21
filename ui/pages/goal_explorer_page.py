"""Streamlined Hierarchical Goal Explorer with contextual bottom bar and view switcher."""

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
    """Spacious Hierarchical Goal Explorer with Canvas, Tree, or Split modes
    and a context-aware bottom inspector bar.
    """

    def __init__(self, parent: tk.Widget, controller: AppController) -> None:
        self.controller = controller
        p = controller.colors
        super().__init__(parent, bg=p["bg"])

        self.view_mode = tk.StringVar(value="canvas")  # 'canvas', 'tree', 'split'
        self.selected_entity: Optional[Tuple[str, str]] = None  # (type, id)
        self._goal_choices: list = []
        self._tree_item_map: Dict[str, Tuple[str, str]] = {}
        self.tree: Optional[ttk.Treeview] = None
        self.graph_canvas: Optional[InteractiveGoalTreeCanvas] = None
        self.render()

    def _set_view_mode(self, mode: str) -> None:
        self.view_mode.set(mode)
        self.render()

    def render(self) -> None:
        p = self.controller.colors
        self.configure(bg=p["bg"])
        for child in self.winfo_children():
            child.destroy()
        self._tree_item_map.clear()
        self.tree = None
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
        if not self.selected_entity and cur_goal_id:
            self.selected_entity = ("goal", cur_goal_id)

        hierarchy = (
            self.controller.goal_service.get_full_hierarchy(cur_goal_id)
            if cur_goal_id
            else None
        )

        # --- Clean Header with Goal Selector & View Mode Toggle ---
        header = tk.Frame(self, bg=p["bg"], padx=32, pady=18)
        header.pack(fill="x")

        left_h = tk.Frame(header, bg=p["bg"])
        left_h.pack(side="left")

        tk.Label(
            left_h,
            text="Goal Explorer",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).pack(side="left", padx=(0, 16))

        self.goal_combo = ttk.Combobox(
            left_h,
            values=[lbl for _, lbl in self._goal_choices],
            state="readonly",
            width=34,
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

        # Segmented View Switcher on Right
        mode_bar = tk.Frame(header, bg=p["surface"], padx=4, pady=4)
        mode_bar.pack(side="right")

        cur_mode = self.view_mode.get()
        for key, lbl in [
            ("canvas", "❖ Visual Canvas"),
            ("tree", "☰ Outline Tree"),
            ("split", "◫ Split View"),
        ]:
            is_sel = cur_mode == key
            tk.Button(
                mode_bar,
                text=lbl,
                bg=p["accent"] if is_sel else p["surface_alt"],
                fg="#FFFFFF" if is_sel else p["text_muted"],
                font=("Segoe UI", 9, "bold" if is_sel else "normal"),
                relief="flat",
                padx=12,
                pady=4,
                cursor="hand2",
                command=lambda k=key: self._set_view_mode(k),
            ).pack(side="left", padx=2)

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

        # --- Contextual Inspector Bar at Bottom ---
        self.inspector_bar = tk.Frame(
            self,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=20,
            pady=12,
        )
        self.inspector_bar.pack(
            fill="x", side="bottom", padx=32, pady=(12, 20)
        )

        # --- Main Workspace Area ---
        workspace = tk.Frame(self, bg=p["bg"], padx=32)
        workspace.pack(fill="both", expand=True)

        if cur_mode == "canvas":
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
                on_select_node=self._on_select_node,
                on_double_click_node=self._on_double_click_node,
            )
            self.graph_canvas.pack(fill="both", expand=True)
            self.graph_canvas.set_hierarchy(hierarchy, self.selected_entity)

        elif cur_mode == "tree":
            tree_panel = self._create_tree_panel(workspace, hierarchy)
            tree_panel.pack(fill="both", expand=True)

        else:  # 'split'
            workspace.columnconfigure(0, weight=4)
            workspace.columnconfigure(1, weight=6)
            workspace.rowconfigure(0, weight=1)

            tree_panel = self._create_tree_panel(workspace, hierarchy)
            tree_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

            canvas_panel = tk.Frame(
                workspace,
                bg=p["canvas_bg"],
                highlightbackground=p["border"],
                highlightthickness=1,
            )
            canvas_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
            self.graph_canvas = InteractiveGoalTreeCanvas(
                canvas_panel,
                colors=p,
                on_select_node=self._on_select_node,
                on_double_click_node=self._on_double_click_node,
            )
            self.graph_canvas.pack(fill="both", expand=True)
            self.graph_canvas.set_hierarchy(hierarchy, self.selected_entity)

        self._rebuild_inspector_bar()

    def _create_tree_panel(
        self, parent: tk.Widget, hierarchy: Dict
    ) -> tk.Frame:
        p = self.controller.colors
        tree_panel = tk.Frame(
            parent,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
        )

        self.tree = ttk.Treeview(
            tree_panel,
            columns=("type", "progress", "due"),
            show="tree headings",
            selectmode="browse",
        )
        self.tree.heading("#0", text="Hierarchy Outline", anchor="w")
        self.tree.heading("type", text="Level", anchor="w")
        self.tree.heading("progress", text="Progress / Status", anchor="w")
        self.tree.heading("due", text="Deadline", anchor="w")

        self.tree.column("#0", width=320, minwidth=180)
        self.tree.column("type", width=90, stretch=False)
        self.tree.column("progress", width=130, stretch=False)
        self.tree.column("due", width=100, stretch=False)

        vsb = ttk.Scrollbar(
            tree_panel, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._populate_tree(hierarchy)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", lambda _e: self._on_tree_double_click())
        return tree_panel

    def _populate_tree(self, hierarchy: Dict) -> None:
        if not self.tree:
            return
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

    def _rebuild_inspector_bar(self) -> None:
        """Dynamically renders only the actions relevant to the currently selected node."""
        for child in self.inspector_bar.winfo_children():
            child.destroy()

        p = self.controller.colors
        if not self.selected_entity:
            tk.Label(
                self.inspector_bar,
                text="Click any node in the graph or tree to inspect or add child items.",
                bg=p["surface"],
                fg=p["text_muted"],
                font=("Segoe UI", 9),
            ).pack(side="left")
            return

        etype, eid = self.selected_entity
        title = ""
        if etype == "goal":
            g = self.controller.goal_repo.get_by_id(eid)
            title = g.title if g else ""
        elif etype == "milestone":
            m = self.controller.milestone_repo.get_by_id(eid)
            title = m.title if m else ""
        elif etype == "project":
            pr = self.controller.project_repo.get_by_id(eid)
            title = pr.title if pr else ""
        elif etype == "task":
            t = self.controller.task_repo.get_by_id(eid)
            title = t.title if t else ""

        tk.Label(
            self.inspector_bar,
            text=f" {etype.upper()} ",
            bg=p["surface_alt"],
            fg=p["accent"],
            font=("Segoe UI", 8, "bold"),
            padx=6,
            pady=2,
        ).pack(side="left", padx=(0, 8))

        tk.Label(
            self.inspector_bar,
            text=title[:48],
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")

        acts = tk.Frame(self.inspector_bar, bg=p["surface"])
        acts.pack(side="right")

        # Contextual primary child creation button
        if etype == "goal":
            tk.Button(
                acts,
                text="+ Add Milestone",
                bg=p["accent"],
                fg="#FFFFFF",
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                padx=12,
                pady=4,
                cursor="hand2",
                command=self._add_milestone,
            ).pack(side="left", padx=4)
        elif etype == "milestone":
            tk.Button(
                acts,
                text="+ Add Project",
                bg=p["accent"],
                fg="#FFFFFF",
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                padx=12,
                pady=4,
                cursor="hand2",
                command=self._add_project,
            ).pack(side="left", padx=4)
        elif etype == "project":
            tk.Button(
                acts,
                text="+ Add Task",
                bg=p["accent"],
                fg="#FFFFFF",
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                padx=12,
                pady=4,
                cursor="hand2",
                command=self._add_task,
            ).pack(side="left", padx=4)
        elif etype == "task":
            tk.Button(
                acts,
                text="✓ Complete / Reopen",
                bg=p["positive"],
                fg="#FFFFFF",
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                padx=12,
                pady=4,
                cursor="hand2",
                command=lambda: self.controller.toggle_task_completion(eid),
            ).pack(side="left", padx=4)

        if etype in ("milestone", "project", "task"):
            tk.Button(
                acts,
                text="↑",
                bg=p["surface_alt"],
                fg=p["text"],
                relief="flat",
                padx=8,
                pady=4,
                cursor="hand2",
                command=lambda: self._reorder_selected(-1),
            ).pack(side="left", padx=2)
            tk.Button(
                acts,
                text="↓",
                bg=p["surface_alt"],
                fg=p["text"],
                relief="flat",
                padx=8,
                pady=4,
                cursor="hand2",
                command=lambda: self._reorder_selected(1),
            ).pack(side="left", padx=2)

        tk.Button(
            acts,
            text="Edit",
            bg=p["surface_alt"],
            fg=p["text"],
            font=("Segoe UI", 9),
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._edit_selected,
        ).pack(side="left", padx=4)

        tk.Button(
            acts,
            text="Delete",
            bg=p["surface_alt"],
            fg=p["danger"],
            font=("Segoe UI", 9),
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._delete_selected,
        ).pack(side="left", padx=(4, 0))

    def _on_goal_selected(self, _event: tk.Event) -> None:
        idx = self.goal_combo.current()
        if 0 <= idx < len(self._goal_choices):
            self.controller.selected_goal_id = self._goal_choices[idx][0]
            self.selected_entity = ("goal", self.controller.selected_goal_id)
            self.render()

    def _on_tree_select(self, _event: tk.Event) -> None:
        if not self.tree:
            return
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        if iid in self._tree_item_map:
            etype, eid = self._tree_item_map[iid]
            self._on_select_node(etype, eid)

    def _on_select_node(self, etype: str, eid: str) -> None:
        self.selected_entity = (etype, eid)
        self._rebuild_inspector_bar()
        if self.graph_canvas:
            self.graph_canvas.selected_key = (etype, eid)
            self.graph_canvas.render()
        if self.tree:
            iid = f"{etype}:{eid}"
            if self.tree.exists(iid):
                self.tree.selection_set(iid)
                self.tree.see(iid)

    def _on_double_click_node(self, etype: str, eid: str) -> None:
        self.selected_entity = (etype, eid)
        if etype == "task":
            self.controller.toggle_task_completion(eid)
        else:
            self._edit_selected()

    def _on_tree_double_click(self) -> None:
        if not self.selected_entity:
            return
        self._on_double_click_node(*self.selected_entity)

    def _add_milestone(self) -> None:
        gid = self.controller.selected_goal_id
        if gid:
            MilestoneFormDialog(self, self.controller, goal_id=gid)

    def _add_project(self) -> None:
        gid = self.controller.selected_goal_id
        if not gid:
            return
        mid = (
            self.selected_entity[1]
            if self.selected_entity and self.selected_entity[0] == "milestone"
            else None
        )
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
        pid = (
            self.selected_entity[1]
            if self.selected_entity and self.selected_entity[0] == "project"
            else None
        )
        TaskFormDialog(self, self.controller, project_id=pid)

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
