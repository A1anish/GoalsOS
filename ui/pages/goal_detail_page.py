"""Detailed workspace page for a single Goal and its full hierarchy."""

import tkinter as tk
from tkinter import messagebox
from typing import Dict, Set

from models.entities import Goal, Milestone, ProgressStats, Project, Task
from ui.app_controller import AppController
from ui.components.canvas_widgets import (
    CircularProgressRing,
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
    """Deep workspace displaying a Goal's metadata, schedule feasibility,
    collapsible Milestones -> Projects -> Tasks hierarchy, and activity log.
    """

    def __init__(self, parent: tk.Widget, controller: AppController) -> None:
        self.controller = controller
        p = controller.colors
        super().__init__(parent, bg=p["bg"])

        self.collapsed_milestones: Set[str] = set()
        self.scroll = ScrollableFrame(self, bg=p["bg"])
        self.scroll.pack(fill="both", expand=True)
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
            empty = tk.Frame(container, bg=p["bg"], padx=30, pady=50)
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
        feasibility = self.controller.analytics_service.analyze_goal_feasibility(goal)

        # --- Top Navigation & Action Bar ---
        top_bar = tk.Frame(container, bg=p["bg"], padx=26, pady=14)
        top_bar.pack(fill="x")

        tk.Button(
            top_bar,
            text="← Back to Goals",
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
            text="❖ Open in Visual Explorer",
            bg=p["surface"],
            fg=p["accent"],
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda gid=goal.id: self.controller.open_goal_explorer(gid),
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            right_btns,
            text="✎ Edit Goal",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 9),
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda g=goal: GoalFormDialog(self, self.controller, goal=g),
        ).pack(side="left", padx=(0, 8))

        # Status transition buttons
        if goal.status == "active":
            tk.Button(
                right_btns,
                text="⏸ Pause",
                bg=p["surface"],
                fg=p["warning"],
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                padx=10,
                pady=5,
                cursor="hand2",
                command=lambda gid=goal.id: self._change_status(gid, "paused"),
            ).pack(side="left", padx=(0, 8))

            tk.Button(
                right_btns,
                text="✓ Mark Completed",
                bg=p["positive"],
                fg="#FFFFFF",
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                padx=12,
                pady=5,
                cursor="hand2",
                command=lambda g=goal, st=g_prog: self._complete_goal_action(g, st),
            ).pack(side="left", padx=(0, 8))
        else:
            tk.Button(
                right_btns,
                text="↻ Reopen to Active",
                bg=p["accent"],
                fg="#FFFFFF",
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                padx=12,
                pady=5,
                cursor="hand2",
                command=lambda gid=goal.id: self._change_status(gid, "active"),
            ).pack(side="left", padx=(0, 8))

        if goal.status != "archived":
            tk.Button(
                right_btns,
                text="Archive",
                bg=p["surface"],
                fg=p["text_muted"],
                font=("Segoe UI", 9),
                relief="flat",
                padx=10,
                pady=5,
                cursor="hand2",
                command=lambda g=goal: self._archive_goal_action(g),
            ).pack(side="left")

        # --- Hero Goal Banner ---
        hero = tk.Frame(
            container,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
        )
        hero.pack(fill="x", padx=26, pady=(0, 16))

        strip = tk.Frame(hero, bg=goal.color or p["accent"], width=6)
        strip.pack(side="left", fill="y")

        hero_inner = tk.Frame(hero, bg=p["surface"], padx=22, pady=18)
        hero_inner.pack(side="left", fill="both", expand=True)

        info_col = tk.Frame(hero_inner, bg=p["surface"])
        info_col.pack(side="left", fill="both", expand=True, padx=(0, 20))

        badge_row = tk.Frame(info_col, bg=p["surface"])
        badge_row.pack(fill="x")
        tk.Label(
            badge_row,
            text=f" {goal.category.upper()} ",
            bg=p["surface_alt"],
            fg=goal.color or p["accent"],
            font=("Segoe UI", 8, "bold"),
            padx=6,
            pady=2,
        ).pack(side="left")
        tk.Label(
            badge_row,
            text=f"  •  PRIORITY: {goal.priority.upper()}  •  STATUS: {goal.status.upper()}",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left")

        tk.Label(
            info_col,
            text=goal.title,
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(6, 4))

        tk.Label(
            info_col,
            text=goal.description or "No description specified.",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 10),
            anchor="w",
            justify="left",
            wraplength=760,
        ).pack(fill="x", pady=(0, 10))

        dl_text, dl_state = format_relative_deadline(
            goal.deadline, is_completed=(goal.status == "completed")
        )
        target_str = (
            f"  |  Target: {goal.target_value:g} {goal.target_unit}"
            if goal.target_value is not None
            else ""
        )
        meta_str = f"Start: {goal.start_date or '—'}   |   Deadline: {goal.deadline or 'None'} ({dl_text})   |   Progress: {g_prog.status_label}{target_str}"
        tk.Label(
            info_col,
            text=meta_str,
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x")

        # Feasibility Banner inside Hero
        f_colors = {
            "feasible": p["positive"],
            "completed": p["positive"],
            "tight": p["warning"],
            "at_risk": p["danger"],
            "overdue": p["danger"],
        }
        f_col = f_colors.get(feasibility["status"], p["info"])
        f_box = tk.Frame(info_col, bg=p["surface_alt"], padx=12, pady=6)
        f_box.pack(fill="x", pady=(10, 0))
        tk.Label(
            f_box,
            text=f"Schedule Analysis: {feasibility['label']} — {feasibility['detail']}",
            bg=p["surface_alt"],
            fg=f_col,
            font=("Segoe UI", 8, "bold"),
            anchor="w",
        ).pack(fill="x")

        # Right side of Hero: Circular Progress Ring
        ring = CircularProgressRing(
            hero_inner,
            size=96,
            thickness=9,
            percentage=g_prog.percentage,
            bg_color=p["surface"],
            track_color=p["track"],
            fill_color=p["positive"]
            if g_prog.percentage >= 100
            else (goal.color or p["accent"]),
            text_color=p["text"],
            sub_label=f"{g_prog.completed_tasks}/{g_prog.total_eligible_tasks}",
        )
        ring.pack(side="right", padx=8)

        # --- Milestones, Projects, and Tasks Section Header ---
        sec_head = tk.Frame(container, bg=p["bg"], padx=26, pady=6)
        sec_head.pack(fill="x")
        tk.Label(
            sec_head,
            text=f"Execution Plan ({len(milestones)} Milestone{'s' if len(milestones) != 1 else ''})",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 14, "bold"),
        ).pack(side="left")

        tk.Button(
            sec_head,
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

        # --- Milestones List ---
        m_list_frame = tk.Frame(container, bg=p["bg"], padx=26)
        m_list_frame.pack(fill="x", pady=(6, 20))

        if not milestones:
            empty_m = tk.Frame(
                m_list_frame,
                bg=p["surface"],
                highlightbackground=p["border"],
                highlightthickness=1,
                padx=24,
                pady=28,
            )
            empty_m.pack(fill="x")
            tk.Label(
                empty_m,
                text="No milestones created for this goal yet.",
                bg=p["surface"],
                fg=p["text"],
                font=("Segoe UI", 11, "bold"),
            ).pack()
            tk.Label(
                empty_m,
                text="Add your first milestone to break this goal into structured phases, projects, and actionable tasks.",
                bg=p["surface"],
                fg=p["text_muted"],
                font=("Segoe UI", 9),
                pady=4,
            ).pack()
        else:
            for idx, m_node in enumerate(milestones):
                self._build_milestone_section(
                    m_list_frame, goal, m_node, idx, len(milestones)
                )

        # --- Goal Activity History ---
        act_panel = tk.Frame(
            container,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=20,
            pady=14,
        )
        act_panel.pack(fill="x", padx=26, pady=(0, 28))
        tk.Label(
            act_panel,
            text="Goal Activity History",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        events = self.controller.activity_repo.list_recent(limit=12)
        for ev in events[:6]:
            erow = tk.Frame(act_panel, bg=p["surface"], pady=2)
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
        m_card.pack(fill="x", pady=(0, 14))

        # Milestone Header Bar
        m_head = tk.Frame(m_card, bg=p["surface_alt"], padx=16, pady=12)
        m_head.pack(fill="x")

        toggle_icon = "▶" if is_collapsed else "▼"
        tk.Button(
            m_head,
            text=f"{toggle_icon}  Milestone {idx + 1}: {m.title}",
            bg=p["surface_alt"],
            fg=p["text"],
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            command=lambda mid=m.id: self._toggle_milestone_collapse(mid),
        ).pack(side="left")

        dl_lbl, _ = format_relative_deadline(
            m.deadline, is_completed=(m.status == "completed")
        )
        tk.Label(
            m_head,
            text=f"   {m_prog.status_label}   •   {dl_lbl}",
            bg=p["surface_alt"],
            fg=p["accent"] if m_prog.percentage < 100 else p["positive"],
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=8)

        # Milestone Action Buttons
        m_actions = tk.Frame(m_head, bg=p["surface_alt"])
        m_actions.pack(side="right")

        tk.Button(
            m_actions,
            text="+ Add Project",
            bg=p["accent"],
            fg="#FFFFFF",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=lambda mid=m.id, gid=goal.id: ProjectFormDialog(
                self, self.controller, milestone_id=mid, goal_id=gid
            ),
        ).pack(side="left", padx=(0, 6))

        if idx > 0:
            tk.Button(
                m_actions,
                text="↑",
                bg=p["surface"],
                fg=p["text"],
                relief="flat",
                padx=6,
                command=lambda mid=m.id: self._reorder_m(mid, -1),
            ).pack(side="left", padx=2)
        if idx < total_m - 1:
            tk.Button(
                m_actions,
                text="↓",
                bg=p["surface"],
                fg=p["text"],
                relief="flat",
                padx=6,
                command=lambda mid=m.id: self._reorder_m(mid, 1),
            ).pack(side="left", padx=2)

        tk.Button(
            m_actions,
            text="Edit",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 8),
            relief="flat",
            padx=8,
            pady=3,
            command=lambda m_obj=m, gid=goal.id: MilestoneFormDialog(
                self, self.controller, goal_id=gid, milestone=m_obj
            ),
        ).pack(side="left", padx=4)

        tk.Button(
            m_actions,
            text="✕",
            bg=p["surface"],
            fg=p["danger"],
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=6,
            pady=3,
            command=lambda m_obj=m: self._delete_milestone(m_obj),
        ).pack(side="left")

        # Milestone Progress Bar
        SmoothProgressBar(
            m_card,
            percentage=m_prog.percentage,
            height=5,
            bg_color=p["surface"],
            track_color=p["track"],
            fill_color=p["positive"]
            if m_prog.percentage >= 100
            else (goal.color or p["accent"]),
        ).pack(fill="x")

        if is_collapsed:
            return

        m_body = tk.Frame(m_card, bg=p["surface"], padx=18, pady=12)
        m_body.pack(fill="x")

        if m.description:
            tk.Label(
                m_body,
                text=m.description,
                bg=p["surface"],
                fg=p["text_muted"],
                font=("Segoe UI", 9),
                anchor="w",
            ).pack(fill="x", pady=(0, 10))

        if not projects:
            tk.Label(
                m_body,
                text="No projects in this milestone yet. Click '+ Add Project' above to organize tasks.",
                bg=p["surface"],
                fg=p["text_muted"],
                font=("Segoe UI", 9),
                pady=6,
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
            padx=14,
            pady=10,
        )
        p_box.pack(fill="x", pady=(0, 10))

        p_head = tk.Frame(p_box, bg=p["surface_alt"])
        p_head.pack(fill="x", pady=(0, 6))

        tk.Label(
            p_head,
            text=f"▣  Project: {proj.title}",
            bg=p["surface_alt"],
            fg=p["text"],
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")

        tk.Label(
            p_head,
            text=f"  ({p_prog.status_label}  •  Priority: {proj.priority.upper()})",
            bg=p["surface_alt"],
            fg=p["text_muted"],
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left")

        p_acts = tk.Frame(p_head, bg=p["surface_alt"])
        p_acts.pack(side="right")

        tk.Button(
            p_acts,
            text="+ Add Task",
            bg=p["accent"],
            fg="#FFFFFF",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=lambda pid=proj.id: TaskFormDialog(
                self, self.controller, project_id=pid
            ),
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            p_acts,
            text="Edit",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 8),
            relief="flat",
            padx=6,
            pady=2,
            command=lambda pr=proj, mid=milestone.id, gid=goal.id: ProjectFormDialog(
                self,
                self.controller,
                milestone_id=mid,
                goal_id=gid,
                project=pr,
            ),
        ).pack(side="left", padx=(0, 4))

        tk.Button(
            p_acts,
            text="✕",
            bg=p["surface"],
            fg=p["danger"],
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=5,
            pady=2,
            command=lambda pr=proj: self._delete_project(pr),
        ).pack(side="left")

        if not tasks:
            tk.Label(
                p_box,
                text="No tasks in this project yet.",
                bg=p["surface_alt"],
                fg=p["text_muted"],
                font=("Segoe UI", 8),
                pady=4,
            ).pack(anchor="w")
            return

        for t in tasks:
            self._build_task_item(p_box, t)

    def _build_task_item(self, parent: tk.Widget, t: Task) -> None:
        p = self.controller.colors
        is_comp = t.status == "completed"
        is_canc = t.status == "cancelled"

        t_row = tk.Frame(parent, bg=p["surface"], padx=10, pady=6)
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
        chk.pack(side="left", padx=(0, 8))

        title_style = "overstrike" if (is_comp or is_canc) else "normal"
        tk.Label(
            t_row,
            text=t.title + (" (CANCELLED)" if is_canc else ""),
            bg=p["surface"],
            fg=p["text_muted"] if (is_comp or is_canc) else p["text"],
            font=("Segoe UI", 9, title_style),
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        dl_lbl, dl_state = format_relative_deadline(t.due_date, is_completed=is_comp)
        meta = f"{t.priority.upper()}  •  {format_duration(t.estimated_minutes)}  •  {dl_lbl}"
        tk.Label(
            t_row,
            text=meta,
            bg=p["surface"],
            fg=p.get(dl_state, p["text_muted"])
            if dl_state == "danger"
            else p["text_muted"],
            font=("Segoe UI", 8),
            padx=8,
        ).pack(side="left")

        tk.Button(
            t_row,
            text="Edit",
            bg=p["surface_alt"],
            fg=p["text_muted"],
            font=("Segoe UI", 8),
            relief="flat",
            padx=6,
            pady=1,
            command=lambda task_obj=t: TaskFormDialog(
                self, self.controller, task=task_obj
            ),
        ).pack(side="left", padx=2)

        tk.Button(
            t_row,
            text="✕",
            bg=p["surface_alt"],
            fg=p["danger"],
            font=("Segoe UI", 8),
            relief="flat",
            padx=5,
            pady=1,
            command=lambda task_obj=t: self._delete_task(task_obj),
        ).pack(side="left")

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
            f"Archive '{goal.title}'? Historical data will be preserved and you can restore it anytime from the Archived tab.",
        ):
            self._change_status(goal.id, "archived")

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
