"""Clean, streamlined Goal Workspace page with inline task creation and sub-tabs."""

import tkinter as tk
from tkinter import messagebox
from typing import Dict, Set

from models.entities import Goal, Milestone, ProgressStats, Project, Task
from ui.app_controller import AppController
from ui.components.canvas_widgets import (
    CircularProgressRing,
    InteractiveGoalTreeCanvas,
    SmoothProgressBar,
)
from ui.components.dialogs import (
    GoalFormDialog,
    MilestoneFormDialog,
    ProjectFormDialog,
    TaskFormDialog,
)
from ui.components.scrollable import ScrollableFrame
from utils.dates import format_duration, format_relative_deadline
from utils.validators import ValidationError


class GoalDetailPage(tk.Frame):
    """Streamlined workspace for a single Goal featuring sub-tabs:
    1. Execution Plan (with inline quick-add task bars and clean context menus)
    2. Visual Node Map (full-width interactive Canvas)
    3. Schedule & History (feasibility analysis & activity log)
    """

    def __init__(self, parent: tk.Widget, controller: AppController) -> None:
        self.controller = controller
        p = controller.colors
        super().__init__(parent, bg=p["bg"])

        self.active_tab = tk.StringVar(value="plan")  # 'plan', 'visual', 'schedule'
        self.collapsed_milestones: Set[str] = set()
        self.scroll = ScrollableFrame(self, bg=p["bg"])
        self.scroll.pack(fill="both", expand=True)
        self.render()

    def _set_tab(self, tab_key: str) -> None:
        self.active_tab.set(tab_key)
        self.render()

    def _toggle_milestone_collapse(self, milestone_id: str) -> None:
        if milestone_id in self.collapsed_milestones:
            self.collapsed_milestones.remove(milestone_id)
        else:
            self.collapsed_milestones.add(milestone_id)
        self.render()

    def render(self) -> None:
        p = self.controller.colors
        self.configure(bg=p["bg"])
        self.scroll.set_bg(p["bg"])
        container = self.scroll.inner

        for child in container.winfo_children():
            child.destroy()

        goal_id = self.controller.selected_goal_id
        if not goal_id:
            goals = self.controller.goal_repo.list_all()
            if goals:
                goal_id = goals[0].id
                self.controller.selected_goal_id = goal_id

        hierarchy = (
            self.controller.goal_service.get_full_hierarchy(goal_id)
            if goal_id
            else None
        )
        if not hierarchy:
            empty = tk.Frame(container, bg=p["bg"], padx=32, pady=50)
            empty.pack(fill="x")
            tk.Label(
                empty,
                text="No Goal Selected",
                bg=p["bg"],
                fg=p["text"],
                font=("Segoe UI", 16, "bold"),
            ).pack()
            tk.Button(
                empty,
                text="← Back to My Goals",
                bg=p["accent"],
                fg="#FFFFFF",
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                padx=14,
                pady=6,
                command=lambda: self.controller.navigate("goals"),
            ).pack(pady=12)
            return

        goal: Goal = hierarchy["goal"]
        g_prog: ProgressStats = hierarchy["progress"]
        milestones = hierarchy["milestones"]

        # --- Top Navigation & Clean Actions ---
        top_bar = tk.Frame(container, bg=p["bg"], padx=32, pady=16)
        top_bar.pack(fill="x")

        tk.Button(
            top_bar,
            text="← All Goals",
            bg=p["surface"],
            fg=p["text"],
            relief="flat",
            padx=12,
            pady=5,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            command=lambda: self.controller.navigate("goals"),
        ).pack(side="left")

        right_btns = tk.Frame(top_bar, bg=p["bg"])
        right_btns.pack(side="right")

        tk.Button(
            right_btns,
            text="Edit Goal",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 9),
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda g=goal: GoalFormDialog(self, self.controller, goal=g),
        ).pack(side="left", padx=(0, 8))

        if goal.status == "active":
            tk.Button(
                right_btns,
                text="✓ Complete Goal",
                bg=p["positive"],
                fg="#FFFFFF",
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                padx=14,
                pady=5,
                cursor="hand2",
                command=lambda g=goal, st=g_prog: self._complete_goal_action(g, st),
            ).pack(side="left", padx=(0, 8))
        else:
            tk.Button(
                right_btns,
                text="↻ Reopen Goal",
                bg=p["accent"],
                fg="#FFFFFF",
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                padx=14,
                pady=5,
                cursor="hand2",
                command=lambda gid=goal.id: self._change_status(gid, "active"),
            ).pack(side="left", padx=(0, 8))

        # More menu button (Pause / Archive)
        more_btn = tk.Button(
            right_btns,
            text="•••",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=5,
            cursor="hand2",
        )
        more_btn.pack(side="left")
        more_btn.bind(
            "<Button-1>",
            lambda e, g=goal: self._show_goal_menu(e, g),
        )

        # --- Clean Hero Card ---
        hero = tk.Frame(
            container,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
        )
        hero.pack(fill="x", padx=32, pady=(0, 18))

        strip = tk.Frame(hero, bg=goal.color or p["accent"], width=5)
        strip.pack(side="left", fill="y")

        hero_inner = tk.Frame(hero, bg=p["surface"], padx=24, pady=18)
        hero_inner.pack(side="left", fill="both", expand=True)

        info_col = tk.Frame(hero_inner, bg=p["surface"])
        info_col.pack(side="left", fill="both", expand=True, padx=(0, 20))

        dl_text, _ = format_relative_deadline(
            goal.deadline, is_completed=(goal.status == "completed")
        )
        tk.Label(
            info_col,
            text=f"{goal.category.upper()}   •   {goal.priority.upper()} PRIORITY   •   {dl_text.upper()}",
            bg=p["surface"],
            fg=goal.color or p["accent"],
            font=("Segoe UI", 8, "bold"),
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            info_col,
            text=goal.title,
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(4, 4))

        if goal.description:
            tk.Label(
                info_col,
                text=goal.description,
                bg=p["surface"],
                fg=p["text_muted"],
                font=("Segoe UI", 10),
                anchor="w",
                justify="left",
                wraplength=780,
            ).pack(fill="x")

        ring = CircularProgressRing(
            hero_inner,
            size=82,
            thickness=8,
            percentage=g_prog.percentage,
            bg_color=p["surface"],
            track_color=p["track"],
            fill_color=p["positive"]
            if g_prog.percentage >= 100
            else (goal.color or p["accent"]),
            text_color=p["text"],
            sub_label=f"{g_prog.completed_tasks}/{g_prog.total_eligible_tasks}",
        )
        ring.pack(side="right")

        # --- Sub-Tabs Bar + "+ Add Milestone" ---
        sub_bar = tk.Frame(container, bg=p["bg"], padx=32)
        sub_bar.pack(fill="x", pady=(0, 14))

        cur_tab = self.active_tab.get()
        for t_key, t_lbl in [
            ("plan", f"☰ Execution Plan ({len(milestones)} Phases)"),
            ("visual", "❖ Visual Node Map"),
            ("schedule", "◷ Feasibility & History"),
        ]:
            is_sel = cur_tab == t_key
            tk.Button(
                sub_bar,
                text=t_lbl,
                bg=p["accent"] if is_sel else p["surface"],
                fg="#FFFFFF" if is_sel else p["text_muted"],
                font=("Segoe UI", 9, "bold" if is_sel else "normal"),
                relief="flat",
                padx=14,
                pady=6,
                cursor="hand2",
                command=lambda k=t_key: self._set_tab(k),
            ).pack(side="left", padx=(0, 8))

        if cur_tab == "plan":
            tk.Button(
                sub_bar,
                text="+ Add Milestone",
                bg=p["accent"],
                fg="#FFFFFF",
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                padx=14,
                pady=6,
                cursor="hand2",
                command=lambda gid=goal.id: MilestoneFormDialog(
                    self, self.controller, goal_id=gid
                ),
            ).pack(side="right")

        # --- Tab Content ---
        content_wrap = tk.Frame(container, bg=p["bg"], padx=32)
        content_wrap.pack(fill="both", expand=True, pady=(0, 32))

        if cur_tab == "plan":
            if not milestones:
                empty_m = tk.Frame(
                    content_wrap,
                    bg=p["surface"],
                    highlightbackground=p["border"],
                    highlightthickness=1,
                    padx=24,
                    pady=36,
                )
                empty_m.pack(fill="x")
                tk.Label(
                    empty_m,
                    text="Break this goal into Milestones, Projects, and Tasks",
                    bg=p["surface"],
                    fg=p["text"],
                    font=("Segoe UI", 12, "bold"),
                ).pack()
                tk.Button(
                    empty_m,
                    text="+ Create First Milestone",
                    bg=p["accent"],
                    fg="#FFFFFF",
                    font=("Segoe UI", 9, "bold"),
                    relief="flat",
                    padx=16,
                    pady=7,
                    cursor="hand2",
                    command=lambda gid=goal.id: MilestoneFormDialog(
                        self, self.controller, goal_id=gid
                    ),
                ).pack(pady=(12, 0))
            else:
                for idx, m_node in enumerate(milestones):
                    self._build_milestone_section(
                        content_wrap, goal, m_node, idx, len(milestones)
                    )

        elif cur_tab == "visual":
            canvas_box = tk.Frame(
                content_wrap,
                bg=p["canvas_bg"],
                highlightbackground=p["border"],
                highlightthickness=1,
                height=520,
            )
            canvas_box.pack(fill="both", expand=True)
            canvas_box.pack_propagate(False)

            tree_canvas = InteractiveGoalTreeCanvas(
                canvas_box,
                colors=p,
                on_double_click_node=self._on_canvas_double_click,
            )
            tree_canvas.pack(fill="both", expand=True)
            tree_canvas.set_hierarchy(hierarchy)

        else:  # 'schedule'
            feasibility = self.controller.analytics_service.analyze_goal_feasibility(
                goal
            )
            f_card = tk.Frame(
                content_wrap,
                bg=p["surface"],
                highlightbackground=p["border"],
                highlightthickness=1,
                padx=22,
                pady=18,
            )
            f_card.pack(fill="x", pady=(0, 16))
            tk.Label(
                f_card,
                text="SCHEDULE FEASIBILITY ANALYSIS",
                bg=p["surface"],
                fg=p["accent"],
                font=("Segoe UI", 9, "bold"),
                anchor="w",
            ).pack(fill="x")
            tk.Label(
                f_card,
                text=feasibility["label"],
                bg=p["surface"],
                fg=p["text"],
                font=("Segoe UI", 14, "bold"),
                anchor="w",
            ).pack(fill="x", pady=(6, 2))
            tk.Label(
                f_card,
                text=feasibility["detail"],
                bg=p["surface"],
                fg=p["text_muted"],
                font=("Segoe UI", 10),
                anchor="w",
            ).pack(fill="x")

            act_card = tk.Frame(
                content_wrap,
                bg=p["surface"],
                highlightbackground=p["border"],
                highlightthickness=1,
                padx=22,
                pady=18,
            )
            act_card.pack(fill="x")
            tk.Label(
                act_card,
                text="RECENT ACTIVITY LOG",
                bg=p["surface"],
                fg=p["accent"],
                font=("Segoe UI", 9, "bold"),
                anchor="w",
            ).pack(fill="x", pady=(0, 10))
            for ev in self.controller.activity_repo.list_recent(limit=10):
                r = tk.Frame(act_card, bg=p["surface"], pady=3)
                r.pack(fill="x")
                tk.Label(
                    r,
                    text=f"•  {ev.description}",
                    bg=p["surface"],
                    fg=p["text"],
                    font=("Segoe UI", 9),
                ).pack(side="left")
                tk.Label(
                    r,
                    text=ev.created_at.replace("T", " "),
                    bg=p["surface"],
                    fg=p["text_dim"],
                    font=("Segoe UI", 8),
                ).pack(side="right")

    def _build_milestone_section(
        self,
        parent: tk.Widget,
        goal: Goal,
        m_node: Dict,
        idx: int,
        total_m: int,
    ) -> None:
        p = self.controller.colors
        m: Milestone = m_node["milestone"]
        m_prog: ProgressStats = m_node["progress"]
        projects = m_node["projects"]
        is_collapsed = m.id in self.collapsed_milestones

        m_card = tk.Frame(
            parent,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
        )
        m_card.pack(fill="x", pady=(0, 16))

        m_head = tk.Frame(m_card, bg=p["surface_alt"], padx=18, pady=12)
        m_head.pack(fill="x")

        toggle_icon = "▶" if is_collapsed else "▼"
        tk.Button(
            m_head,
            text=f"{toggle_icon}  {m.title}",
            bg=p["surface_alt"],
            fg=p["text"],
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            command=lambda mid=m.id: self._toggle_milestone_collapse(mid),
        ).pack(side="left")

        tk.Label(
            m_head,
            text=f"   {m_prog.status_label}",
            bg=p["surface_alt"],
            fg=p["text_muted"],
            font=("Segoe UI", 9),
        ).pack(side="left")

        m_actions = tk.Frame(m_head, bg=p["surface_alt"])
        m_actions.pack(side="right")

        tk.Button(
            m_actions,
            text="+ Project",
            bg=p["surface"],
            fg=p["accent"],
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=lambda mid=m.id, gid=goal.id: ProjectFormDialog(
                self, self.controller, milestone_id=mid, goal_id=gid
            ),
        ).pack(side="left", padx=(0, 6))

        menu_btn = tk.Button(
            m_actions,
            text="•••",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
        )
        menu_btn.pack(side="left")
        menu_btn.bind(
            "<Button-1>",
            lambda e, m_obj=m, g_id=goal.id, i=idx, tot=total_m: self._show_milestone_menu(
                e, m_obj, g_id, i, tot
            ),
        )

        SmoothProgressBar(
            m_card,
            percentage=m_prog.percentage,
            height=4,
            bg_color=p["surface"],
            track_color=p["track"],
            fill_color=p["positive"]
            if m_prog.percentage >= 100
            else (goal.color or p["accent"]),
        ).pack(fill="x")

        if is_collapsed:
            return

        m_body = tk.Frame(m_card, bg=p["surface"], padx=20, pady=14)
        m_body.pack(fill="x")

        if not projects:
            tk.Label(
                m_body,
                text="No projects yet — click '+ Project' above to add one.",
                bg=p["surface"],
                fg=p["text_muted"],
                font=("Segoe UI", 9),
            ).pack(anchor="w")
            return

        for p_entry in projects:
            self._build_project_block(m_body, goal, m, p_entry)

    def _build_project_block(
        self,
        parent: tk.Widget,
        goal: Goal,
        milestone: Milestone,
        p_entry: Dict,
    ) -> None:
        p = self.controller.colors
        proj: Project = p_entry["project"]
        p_prog: ProgressStats = p_entry["progress"]
        tasks = p_entry["tasks"]

        p_box = tk.Frame(
            parent,
            bg=p["surface_alt"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=16,
            pady=12,
        )
        p_box.pack(fill="x", pady=(0, 12))

        p_head = tk.Frame(p_box, bg=p["surface_alt"])
        p_head.pack(fill="x", pady=(0, 8))

        tk.Label(
            p_head,
            text=proj.title,
            bg=p["surface_alt"],
            fg=p["text"],
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")

        tk.Label(
            p_head,
            text=f"   {p_prog.status_label}",
            bg=p["surface_alt"],
            fg=p["text_muted"],
            font=("Segoe UI", 8),
        ).pack(side="left")

        p_menu_btn = tk.Button(
            p_head,
            text="•••",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
        )
        p_menu_btn.pack(side="right")
        p_menu_btn.bind(
            "<Button-1>",
            lambda e, pr=proj, mid=milestone.id, gid=goal.id: self._show_project_menu(
                e, pr, mid, gid
            ),
        )

        for t in tasks:
            self._build_task_item(p_box, t)

        # Inline Quick-Add Task Bar inside every Project!
        quick_row = tk.Frame(p_box, bg=p["surface_alt"], pady=4)
        quick_row.pack(fill="x")

        q_ent = tk.Entry(
            quick_row,
            bg=p["input_bg"],
            fg=p["text"],
            insertbackground=p["text"],
            highlightbackground=p["border"],
            highlightthickness=1,
            relief="flat",
            font=("Segoe UI", 9),
        )
        q_ent.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 8))

        def _quick_add(_e=None, pid=proj.id, entry=q_ent) -> None:
            t_title = entry.get().strip()
            if not t_title:
                TaskFormDialog(self, self.controller, project_id=pid)
                return
            self.controller.task_service.create_task(
                project_id=pid, title=t_title
            )
            self.controller.show_toast(f"Added task '{t_title}'", "positive")
            self.controller.notify_data_changed("task_created_inline")

        q_ent.bind("<Return>", _quick_add)

        tk.Button(
            quick_row,
            text="+ Add Task",
            bg=p["surface"],
            fg=p["accent"],
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=_quick_add,
        ).pack(side="right")

    def _build_task_item(self, parent: tk.Widget, t: Task) -> None:
        p = self.controller.colors
        is_comp = t.status == "completed"
        is_canc = t.status == "cancelled"

        t_row = tk.Frame(parent, bg=p["surface"], padx=12, pady=7)
        t_row.pack(fill="x", pady=2)

        chk = tk.Button(
            t_row,
            text="☑" if is_comp else ("☒" if is_canc else "☐"),
            bg=p["surface"],
            fg=p["positive"]
            if is_comp
            else (p["text_dim"] if is_canc else p["text_muted"]),
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            command=lambda tid=t.id: self.controller.toggle_task_completion(tid),
        )
        chk.pack(side="left", padx=(0, 10))

        title_style = "overstrike" if (is_comp or is_canc) else "normal"
        lbl = tk.Label(
            t_row,
            text=t.title + (" (Cancelled)" if is_canc else ""),
            bg=p["surface"],
            fg=p["text_muted"] if (is_comp or is_canc) else p["text"],
            font=("Segoe UI", 9, title_style),
            anchor="w",
            cursor="hand2",
        )
        lbl.pack(side="left", fill="x", expand=True)
        lbl.bind(
            "<Button-1>",
            lambda _e, tid=t.id: self.controller.toggle_task_completion(tid),
        )

        dl_lbl, dl_state = format_relative_deadline(t.due_date, is_completed=is_comp)
        tk.Label(
            t_row,
            text=f"{format_duration(t.estimated_minutes)}  •  {dl_lbl}",
            bg=p["surface"],
            fg=p.get(dl_state, p["text_muted"])
            if dl_state == "danger"
            else p["text_muted"],
            font=("Segoe UI", 8),
            padx=8,
        ).pack(side="left")

        t_menu_btn = tk.Button(
            t_row,
            text="•••",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=6,
            pady=1,
            cursor="hand2",
        )
        t_menu_btn.pack(side="right")
        t_menu_btn.bind(
            "<Button-1>", lambda e, task_o=t: self._show_task_menu(e, task_o)
        )

    # --- Clean Context Menus (Replaces Button Clutter) ---

    def _show_goal_menu(self, event: tk.Event, goal: Goal) -> None:
        p = self.controller.colors
        menu = tk.Menu(self, tearoff=0, bg=p["surface"], fg=p["text"])
        menu.add_command(
            label="Open in Full Explorer",
            command=lambda: self.controller.open_goal_explorer(goal.id),
        )
        if goal.status == "active":
            menu.add_command(
                label="Pause Goal",
                command=lambda: self._change_status(goal.id, "paused"),
            )
        if goal.status != "archived":
            menu.add_command(
                label="Archive Goal",
                command=lambda: self._archive_goal_action(goal),
            )
        menu.add_separator()
        menu.add_command(
            label="Delete Goal Permanently",
            foreground=p["danger"],
            command=lambda: self._delete_goal_action(goal),
        )
        menu.tk_popup(event.x_root, event.y_root)

    def _show_milestone_menu(
        self,
        event: tk.Event,
        m: Milestone,
        goal_id: str,
        idx: int,
        total_m: int,
    ) -> None:
        p = self.controller.colors
        menu = tk.Menu(self, tearoff=0, bg=p["surface"], fg=p["text"])
        menu.add_command(
            label="Edit Milestone",
            command=lambda: MilestoneFormDialog(
                self, self.controller, goal_id=goal_id, milestone=m
            ),
        )
        if idx > 0:
            menu.add_command(
                label="Move Up ↑",
                command=lambda: self._reorder_m(m.id, -1),
            )
        if idx < total_m - 1:
            menu.add_command(
                label="Move Down ↓",
                command=lambda: self._reorder_m(m.id, 1),
            )
        menu.add_separator()
        menu.add_command(
            label="Delete Milestone",
            foreground=p["danger"],
            command=lambda: self._delete_milestone(m),
        )
        menu.tk_popup(event.x_root, event.y_root)

    def _show_project_menu(
        self, event: tk.Event, proj: Project, milestone_id: str, goal_id: str
    ) -> None:
        p = self.controller.colors
        menu = tk.Menu(self, tearoff=0, bg=p["surface"], fg=p["text"])
        menu.add_command(
            label="Edit Project",
            command=lambda: ProjectFormDialog(
                self,
                self.controller,
                milestone_id=milestone_id,
                goal_id=goal_id,
                project=proj,
            ),
        )
        menu.add_command(
            label="Add Task (Detailed Form)",
            command=lambda: TaskFormDialog(
                self, self.controller, project_id=proj.id
            ),
        )
        menu.add_separator()
        menu.add_command(
            label="Delete Project",
            foreground=p["danger"],
            command=lambda: self._delete_project(proj),
        )
        menu.tk_popup(event.x_root, event.y_root)

    def _show_task_menu(self, event: tk.Event, t: Task) -> None:
        p = self.controller.colors
        menu = tk.Menu(self, tearoff=0, bg=p["surface"], fg=p["text"])
        menu.add_command(
            label="Edit Task",
            command=lambda: TaskFormDialog(self, self.controller, task=t),
        )
        menu.add_command(
            label="Complete / Reopen",
            command=lambda: self.controller.toggle_task_completion(t.id),
        )
        menu.add_separator()
        menu.add_command(
            label="Delete Task",
            foreground=p["danger"],
            command=lambda: self._delete_task(t),
        )
        menu.tk_popup(event.x_root, event.y_root)

    def _on_canvas_double_click(self, etype: str, eid: str) -> None:
        if etype == "task":
            self.controller.toggle_task_completion(eid)

    def _reorder_m(self, milestone_id: str, direction: int) -> None:
        self.controller.goal_service.reorder_milestone(milestone_id, direction)
        self.controller.notify_data_changed("milestone_reordered")

    def _change_status(self, goal_id: str, new_status: str) -> None:
        self.controller.goal_service.change_goal_status(goal_id, new_status)
        self.controller.show_toast(
            f"Goal status updated to {new_status.upper()}", "info"
        )
        self.controller.notify_data_changed("goal_status_changed")

    def _complete_goal_action(self, goal: Goal, stats: ProgressStats) -> None:
        override = False
        if (
            stats.has_eligible_tasks
            and stats.completed_tasks < stats.total_eligible_tasks
        ):
            rem = stats.total_eligible_tasks - stats.completed_tasks
            if not messagebox.askyesno(
                "Unfinished Tasks",
                f"There are still {rem} unfinished eligible task(s) under '{goal.title}'.\n\nOverride and mark this goal Completed anyway?",
            ):
                return
            override = True

        try:
            self.controller.goal_service.change_goal_status(
                goal.id, "completed", allow_incomplete_override=override
            )
            self.controller.show_toast(
                f"Goal '{goal.title}' marked as Completed!", "positive"
            )
            self.controller.notify_data_changed("goal_completed")
        except ValidationError as exc:
            messagebox.showerror("Cannot Complete Goal", str(exc))

    def _archive_goal_action(self, goal: Goal) -> None:
        if messagebox.askyesno(
            "Archive Goal",
            f"Archive '{goal.title}'? Historical data will be preserved.",
        ):
            self._change_status(goal.id, "archived")

    def _delete_goal_action(self, goal: Goal) -> None:
        if messagebox.askyesno(
            "Delete Goal",
            f"Permanently delete '{goal.title}' and all its milestones, projects, and tasks?",
        ):
            self.controller.goal_service.delete_goal(goal.id)
            self.controller.selected_goal_id = None
            self.controller.navigate("goals")
            self.controller.notify_data_changed("goal_deleted")

    def _delete_milestone(self, m: Milestone) -> None:
        if messagebox.askyesno(
            "Delete Milestone",
            f"Delete milestone '{m.title}' and all projects/tasks inside it?",
        ):
            self.controller.goal_service.delete_milestone(m.id)
            self.controller.notify_data_changed("milestone_deleted")

    def _delete_project(self, proj: Project) -> None:
        if messagebox.askyesno(
            "Delete Project",
            f"Delete project '{proj.title}' and all tasks inside it?",
        ):
            self.controller.goal_service.delete_project(proj.id)
            self.controller.notify_data_changed("project_deleted")

    def _delete_task(self, t: Task) -> None:
        if messagebox.askyesno("Delete Task", f"Delete task '{t.title}'?"):
            self.controller.task_service.delete_task(t.id)
            self.controller.notify_data_changed("task_deleted")
