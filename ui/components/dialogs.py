"""Modal dialogs for creating and editing Goals, Milestones, Projects, and Tasks."""

from datetime import date, timedelta
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, List, Optional, Tuple

from models.entities import (
    GOAL_ACCENT_COLORS,
    GOAL_CATEGORIES,
    GOAL_STATUSES,
    PRIORITIES,
    TASK_STATUSES,
    Goal,
    Milestone,
    Project,
    Task,
)
from ui.app_controller import AppController
from utils.dates import today_iso
from utils.validators import ValidationError


class BaseModalDialog(tk.Toplevel):
    """Base styled modal dialog window with inline validation error banner."""

    def __init__(
        self,
        parent: tk.Widget,
        controller: AppController,
        title: str,
        width: int = 520,
        height: int = 560,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.colors = controller.colors
        self.title(title)
        self.configure(bg=self.colors["surface"])
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        # Center over parent window
        root = parent.winfo_toplevel()
        root.update_idletasks()
        rx, ry = root.winfo_rootx(), root.winfo_rooty()
        rw, rh = root.winfo_width(), root.winfo_height()
        x = max(40, rx + (rw - width) // 2)
        y = max(40, ry + (rh - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

        # Header
        header = tk.Frame(self, bg=self.colors["surface_alt"], padx=20, pady=14)
        header.pack(fill="x")
        tk.Label(
            header,
            text=title,
            bg=self.colors["surface_alt"],
            fg=self.colors["text"],
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left")

        # Error banner (hidden by default)
        self.error_var = tk.StringVar(value="")
        self.error_lbl = tk.Label(
            self,
            textvariable=self.error_var,
            bg=self.colors["danger_bg"],
            fg=self.colors["danger"],
            font=("Segoe UI", 9, "bold"),
            padx=16,
            pady=8,
            anchor="w",
            justify="left",
            wraplength=width - 40,
        )

        # Body container
        self.body = tk.Frame(self, bg=self.colors["surface"], padx=22, pady=14)
        self.body.pack(fill="both", expand=True)

        # Footer container
        self.footer = tk.Frame(
            self, bg=self.colors["surface_alt"], padx=20, pady=12
        )
        self.footer.pack(fill="x", side="bottom")

        self.bind("<Escape>", lambda _e: self.destroy())

    def show_error(self, message: str) -> None:
        self.error_var.set(f"⚠  {message}")
        self.error_lbl.pack(fill="x", before=self.body)

    def add_field_label(self, parent: tk.Widget, text: str) -> None:
        tk.Label(
            parent,
            text=text,
            bg=self.colors["surface"],
            fg=self.colors["text_muted"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(8, 3))

    def make_entry(self, parent: tk.Widget, initial: str = "") -> tk.Entry:
        ent = tk.Entry(
            parent,
            bg=self.colors["input_bg"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["accent"],
            highlightthickness=1,
            relief="flat",
            font=("Segoe UI", 10),
        )
        if initial:
            ent.insert(0, str(initial))
        return ent


class GoalFormDialog(BaseModalDialog):
    """Modal dialog for creating or editing a Goal."""

    def __init__(
        self,
        parent: tk.Widget,
        controller: AppController,
        goal: Optional[Goal] = None,
        on_saved: Optional[Callable[[Goal], None]] = None,
    ) -> None:
        is_edit = goal is not None
        super().__init__(
            parent,
            controller,
            title="Edit Goal" if is_edit else "Create New Goal",
            width=540,
            height=640,
        )
        self.goal = goal
        self.on_saved = on_saved
        p = self.colors

        # Title
        self.add_field_label(self.body, "GOAL TITLE *")
        self.title_ent = self.make_entry(
            self.body, goal.title if goal else ""
        )
        self.title_ent.pack(fill="x", ipady=5)
        self.title_ent.focus_set()

        # Description
        self.add_field_label(self.body, "DESCRIPTION & OUTCOME VISION")
        self.desc_txt = tk.Text(
            self.body,
            height=3,
            bg=p["input_bg"],
            fg=p["text"],
            insertbackground=p["text"],
            highlightbackground=p["border"],
            highlightcolor=p["accent"],
            highlightthickness=1,
            relief="flat",
            font=("Segoe UI", 10),
            padx=6,
            pady=6,
        )
        self.desc_txt.pack(fill="x")
        if goal and goal.description:
            self.desc_txt.insert("1.0", goal.description)

        # Row: Category & Priority
        row1 = tk.Frame(self.body, bg=p["surface"])
        row1.pack(fill="x", pady=(6, 0))
        col_cat = tk.Frame(row1, bg=p["surface"])
        col_cat.pack(side="left", fill="x", expand=True, padx=(0, 8))
        col_prio = tk.Frame(row1, bg=p["surface"])
        col_prio.pack(side="left", fill="x", expand=True, padx=(8, 0))

        self.add_field_label(col_cat, "CATEGORY (SELECT OR TYPE CUSTOM)")
        existing_cats = sorted(
            set(GOAL_CATEGORIES + controller.goal_repo.get_distinct_categories())
        )
        self.cat_combo = ttk.Combobox(
            col_cat, values=existing_cats, font=("Segoe UI", 10)
        )
        self.cat_combo.set(goal.category if goal else "Personal Development")
        self.cat_combo.pack(fill="x")

        self.add_field_label(col_prio, "PRIORITY")
        self.prio_combo = ttk.Combobox(
            col_prio, values=PRIORITIES, state="readonly", font=("Segoe UI", 10)
        )
        self.prio_combo.set(goal.priority if goal else "high")
        self.prio_combo.pack(fill="x")

        # Row: Start Date & Target Deadline
        row2 = tk.Frame(self.body, bg=p["surface"])
        row2.pack(fill="x", pady=(6, 0))
        col_start = tk.Frame(row2, bg=p["surface"])
        col_start.pack(side="left", fill="x", expand=True, padx=(0, 8))
        col_end = tk.Frame(row2, bg=p["surface"])
        col_end.pack(side="left", fill="x", expand=True, padx=(8, 0))

        self.add_field_label(col_start, "START DATE (YYYY-MM-DD)")
        self.start_ent = self.make_entry(
            col_start,
            goal.start_date if goal and goal.start_date else today_iso(),
        )
        self.start_ent.pack(fill="x", ipady=4)

        self.add_field_label(col_end, "TARGET DEADLINE (YYYY-MM-DD)")
        default_dl = (
            goal.deadline
            if goal and goal.deadline
            else (date.today() + timedelta(days=30)).isoformat()
        )
        self.deadline_ent = self.make_entry(
            col_end, default_dl if not goal or goal.deadline else ""
        )
        self.deadline_ent.pack(fill="x", ipady=4)

        # Row: Measurable Target (Optional) & Unit
        row3 = tk.Frame(self.body, bg=p["surface"])
        row3.pack(fill="x", pady=(6, 0))
        col_tval = tk.Frame(row3, bg=p["surface"])
        col_tval.pack(side="left", fill="x", expand=True, padx=(0, 8))
        col_tunit = tk.Frame(row3, bg=p["surface"])
        col_tunit.pack(side="left", fill="x", expand=True, padx=(8, 0))

        self.add_field_label(col_tval, "MEASURABLE TARGET (OPTIONAL)")
        tval_str = (
            str(goal.target_value)
            if goal and goal.target_value is not None
            else ""
        )
        self.tval_ent = self.make_entry(col_tval, tval_str)
        self.tval_ent.pack(fill="x", ipady=4)

        self.add_field_label(col_tunit, "TARGET UNIT (E.G. MODULES, BOOKS)")
        self.tunit_ent = self.make_entry(
            col_tunit, goal.target_unit if goal else ""
        )
        self.tunit_ent.pack(fill="x", ipady=4)

        # Status (if editing) & Color Picker
        row4 = tk.Frame(self.body, bg=p["surface"])
        row4.pack(fill="x", pady=(8, 0))

        self.selected_color = tk.StringVar(
            value=goal.color if goal and goal.color else GOAL_ACCENT_COLORS[0]
        )
        self.add_field_label(row4, "GOAL ACCENT COLOR")
        swatch_row = tk.Frame(row4, bg=p["surface"])
        swatch_row.pack(fill="x", pady=4)

        self._swatch_btns = []
        for col_hex in GOAL_ACCENT_COLORS:
            btn = tk.Button(
                swatch_row,
                bg=col_hex,
                activebackground=col_hex,
                width=3,
                height=1,
                relief="flat",
                bd=0,
                cursor="hand2",
                command=lambda c=col_hex: self._select_color(c),
            )
            btn.pack(side="left", padx=(0, 8))
            self._swatch_btns.append((col_hex, btn))
        self._select_color(self.selected_color.get())

        if is_edit:
            self.add_field_label(self.body, "GOAL STATUS")
            self.status_combo = ttk.Combobox(
                self.body,
                values=GOAL_STATUSES,
                state="readonly",
                font=("Segoe UI", 10),
            )
            self.status_combo.set(goal.status)
            self.status_combo.pack(fill="x")

        # Footer buttons
        tk.Button(
            self.footer,
            text="Cancel",
            bg=p["surface"],
            fg=p["text"],
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.destroy,
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            self.footer,
            text="Save Goal" if is_edit else "Create Goal",
            bg=p["accent"],
            fg="#FFFFFF",
            activebackground=p["accent_hover"],
            activeforeground="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=18,
            pady=6,
            cursor="hand2",
            command=self._on_submit,
        ).pack(side="right")

    def _select_color(self, c: str) -> None:
        self.selected_color.set(c)
        for col_hex, btn in self._swatch_btns:
            if col_hex == c:
                btn.configure(text="✓", fg="#FFFFFF", font=("Segoe UI", 9, "bold"))
            else:
                btn.configure(text="")

    def _on_submit(self) -> None:
        title = self.title_ent.get()
        desc = self.desc_txt.get("1.0", "end").strip()
        cat = self.cat_combo.get()
        prio = self.prio_combo.get()
        start_d = self.start_ent.get()
        deadline_d = self.deadline_ent.get()
        tval = self.tval_ent.get()
        tunit = self.tunit_ent.get()
        col = self.selected_color.get()

        try:
            if self.goal is None:
                saved = self.controller.goal_service.create_goal(
                    title=title,
                    description=desc,
                    category=cat,
                    start_date=start_d,
                    deadline=deadline_d,
                    priority=prio,
                    target_value=tval,
                    target_unit=tunit,
                    color=col,
                )
                self.controller.show_toast(
                    f"Created goal '{saved.title}'", "positive"
                )
            else:
                new_status = self.status_combo.get()
                override = False
                if new_status == "completed" and self.goal.status != "completed":
                    stats = self.controller.progress_service.get_goal_progress(
                        self.goal.id
                    )
                    if (
                        stats.has_eligible_tasks
                        and stats.completed_tasks < stats.total_eligible_tasks
                    ):
                        rem = stats.total_eligible_tasks - stats.completed_tasks
                        override = messagebox.askyesno(
                            "Unfinished Tasks Remaining",
                            f"This goal still has {rem} unfinished eligible task(s).\n\nDo you want to override and mark the goal Completed anyway?",
                            parent=self,
                        )
                        if not override:
                            return

                saved = self.controller.goal_service.update_goal(
                    goal_id=self.goal.id,
                    title=title,
                    description=desc,
                    category=cat,
                    start_date=start_d,
                    deadline=deadline_d,
                    priority=prio,
                    status=new_status,
                    target_value=tval,
                    target_unit=tunit,
                    color=col,
                    allow_incomplete_override=override,
                )
                self.controller.show_toast(
                    f"Updated goal '{saved.title}'", "info"
                )

            self.controller.notify_data_changed("goal_saved")
            if self.on_saved:
                self.on_saved(saved)
            self.destroy()
        except ValidationError as exc:
            self.show_error(str(exc))


class MilestoneFormDialog(BaseModalDialog):
    """Modal dialog for creating or editing a Milestone."""

    def __init__(
        self,
        parent: tk.Widget,
        controller: AppController,
        goal_id: str,
        milestone: Optional[Milestone] = None,
    ) -> None:
        is_edit = milestone is not None
        super().__init__(
            parent,
            controller,
            title="Edit Milestone" if is_edit else "Add Milestone",
            width=480,
            height=450,
        )
        self.goal_id = goal_id
        self.milestone = milestone
        p = self.colors

        self.add_field_label(self.body, "MILESTONE TITLE *")
        self.title_ent = self.make_entry(
            self.body, milestone.title if milestone else ""
        )
        self.title_ent.pack(fill="x", ipady=5)
        self.title_ent.focus_set()

        self.add_field_label(self.body, "DESCRIPTION")
        self.desc_ent = self.make_entry(
            self.body, milestone.description if milestone else ""
        )
        self.desc_ent.pack(fill="x", ipady=5)

        row_dates = tk.Frame(self.body, bg=p["surface"])
        row_dates.pack(fill="x", pady=(6, 0))
        c1 = tk.Frame(row_dates, bg=p["surface"])
        c1.pack(side="left", fill="x", expand=True, padx=(0, 8))
        c2 = tk.Frame(row_dates, bg=p["surface"])
        c2.pack(side="left", fill="x", expand=True, padx=(8, 0))

        self.add_field_label(c1, "START DATE (YYYY-MM-DD)")
        self.start_ent = self.make_entry(
            c1,
            milestone.start_date
            if milestone and milestone.start_date
            else today_iso(),
        )
        self.start_ent.pack(fill="x", ipady=4)

        self.add_field_label(c2, "DEADLINE (YYYY-MM-DD)")
        self.deadline_ent = self.make_entry(
            c2,
            milestone.deadline
            if milestone and milestone.deadline
            else (date.today() + timedelta(days=14)).isoformat(),
        )
        self.deadline_ent.pack(fill="x", ipady=4)

        if is_edit:
            self.add_field_label(self.body, "STATUS")
            self.status_combo = ttk.Combobox(
                self.body,
                values=["active", "completed", "archived"],
                state="readonly",
            )
            self.status_combo.set(milestone.status)
            self.status_combo.pack(fill="x")

        tk.Button(
            self.footer,
            text="Cancel",
            bg=p["surface"],
            fg=p["text"],
            relief="flat",
            padx=14,
            pady=6,
            command=self.destroy,
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            self.footer,
            text="Save Milestone",
            bg=p["accent"],
            fg="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=16,
            pady=6,
            cursor="hand2",
            command=self._on_submit,
        ).pack(side="right")

    def _on_submit(self) -> None:
        try:
            if self.milestone is None:
                m = self.controller.goal_service.create_milestone(
                    goal_id=self.goal_id,
                    title=self.title_ent.get(),
                    description=self.desc_ent.get(),
                    start_date=self.start_ent.get(),
                    deadline=self.deadline_ent.get(),
                )
                self.controller.show_toast(
                    f"Added milestone '{m.title}'", "positive"
                )
            else:
                m = self.controller.goal_service.update_milestone(
                    milestone_id=self.milestone.id,
                    title=self.title_ent.get(),
                    description=self.desc_ent.get(),
                    start_date=self.start_ent.get(),
                    deadline=self.deadline_ent.get(),
                    status=self.status_combo.get(),
                )
                self.controller.show_toast(
                    f"Updated milestone '{m.title}'", "info"
                )
            self.controller.notify_data_changed("milestone_saved")
            self.destroy()
        except ValidationError as exc:
            self.show_error(str(exc))


class ProjectFormDialog(BaseModalDialog):
    """Modal dialog for creating or editing a Project under a Milestone."""

    def __init__(
        self,
        parent: tk.Widget,
        controller: AppController,
        milestone_id: str,
        goal_id: Optional[str] = None,
        project: Optional[Project] = None,
    ) -> None:
        is_edit = project is not None
        super().__init__(
            parent,
            controller,
            title="Edit Project" if is_edit else "Add Project",
            width=500,
            height=500,
        )
        self.milestone_id = milestone_id
        self.project = project
        p = self.colors

        # Allow moving project to a different milestone within the same goal
        self._milestone_options: List[Tuple[str, str]] = []
        if goal_id:
            for m in controller.milestone_repo.list_by_goal(goal_id):
                self._milestone_options.append((m.id, m.title))

        if self._milestone_options:
            self.add_field_label(self.body, "PARENT MILESTONE")
            self.m_combo = ttk.Combobox(
                self.body,
                values=[lbl for _, lbl in self._milestone_options],
                state="readonly",
            )
            cur_idx = next(
                (
                    i
                    for i, (mid, _) in enumerate(self._milestone_options)
                    if mid == milestone_id
                ),
                0,
            )
            self.m_combo.current(cur_idx)
            self.m_combo.pack(fill="x")

        self.add_field_label(self.body, "PROJECT TITLE *")
        self.title_ent = self.make_entry(
            self.body, project.title if project else ""
        )
        self.title_ent.pack(fill="x", ipady=5)
        self.title_ent.focus_set()

        self.add_field_label(self.body, "DESCRIPTION")
        self.desc_ent = self.make_entry(
            self.body, project.description if project else ""
        )
        self.desc_ent.pack(fill="x", ipady=5)

        row_dates = tk.Frame(self.body, bg=p["surface"])
        row_dates.pack(fill="x", pady=(6, 0))
        c1 = tk.Frame(row_dates, bg=p["surface"])
        c1.pack(side="left", fill="x", expand=True, padx=(0, 8))
        c2 = tk.Frame(row_dates, bg=p["surface"])
        c2.pack(side="left", fill="x", expand=True, padx=(8, 0))

        self.add_field_label(c1, "START DATE")
        self.start_ent = self.make_entry(
            c1,
            project.start_date
            if project and project.start_date
            else today_iso(),
        )
        self.start_ent.pack(fill="x", ipady=4)

        self.add_field_label(c2, "DEADLINE")
        self.deadline_ent = self.make_entry(
            c2,
            project.deadline
            if project and project.deadline
            else (date.today() + timedelta(days=10)).isoformat(),
        )
        self.deadline_ent.pack(fill="x", ipady=4)

        row_meta = tk.Frame(self.body, bg=p["surface"])
        row_meta.pack(fill="x", pady=(6, 0))
        cp = tk.Frame(row_meta, bg=p["surface"])
        cp.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.add_field_label(cp, "PRIORITY")
        self.prio_combo = ttk.Combobox(
            cp, values=PRIORITIES, state="readonly"
        )
        self.prio_combo.set(project.priority if project else "medium")
        self.prio_combo.pack(fill="x")

        if is_edit:
            cs = tk.Frame(row_meta, bg=p["surface"])
            cs.pack(side="left", fill="x", expand=True, padx=(8, 0))
            self.add_field_label(cs, "STATUS")
            self.status_combo = ttk.Combobox(
                cs,
                values=["active", "completed", "archived"],
                state="readonly",
            )
            self.status_combo.set(project.status)
            self.status_combo.pack(fill="x")

        tk.Button(
            self.footer,
            text="Cancel",
            bg=p["surface"],
            fg=p["text"],
            relief="flat",
            padx=14,
            pady=6,
            command=self.destroy,
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            self.footer,
            text="Save Project",
            bg=p["accent"],
            fg="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=16,
            pady=6,
            cursor="hand2",
            command=self._on_submit,
        ).pack(side="right")

    def _on_submit(self) -> None:
        target_mid = self.milestone_id
        if self._milestone_options and hasattr(self, "m_combo"):
            sel_idx = self.m_combo.current()
            if 0 <= sel_idx < len(self._milestone_options):
                target_mid = self._milestone_options[sel_idx][0]

        try:
            if self.project is None:
                proj = self.controller.goal_service.create_project(
                    milestone_id=target_mid,
                    title=self.title_ent.get(),
                    description=self.desc_ent.get(),
                    start_date=self.start_ent.get(),
                    deadline=self.deadline_ent.get(),
                    priority=self.prio_combo.get(),
                )
                self.controller.show_toast(
                    f"Created project '{proj.title}'", "positive"
                )
            else:
                proj = self.controller.goal_service.update_project(
                    project_id=self.project.id,
                    milestone_id=target_mid,
                    title=self.title_ent.get(),
                    description=self.desc_ent.get(),
                    start_date=self.start_ent.get(),
                    deadline=self.deadline_ent.get(),
                    priority=self.prio_combo.get(),
                    status=self.status_combo.get(),
                )
                self.controller.show_toast(
                    f"Updated project '{proj.title}'", "info"
                )
            self.controller.notify_data_changed("project_saved")
            self.destroy()
        except ValidationError as exc:
            self.show_error(str(exc))


class TaskFormDialog(BaseModalDialog):
    """Modal dialog for creating or editing a Task."""

    def __init__(
        self,
        parent: tk.Widget,
        controller: AppController,
        project_id: Optional[str] = None,
        task: Optional[Task] = None,
    ) -> None:
        is_edit = task is not None
        super().__init__(
            parent,
            controller,
            title="Edit Task" if is_edit else "Create Actionable Task",
            width=540,
            height=580,
        )
        self.task = task
        p = self.colors

        # Load all available projects
        self.project_choices = (
            controller.goal_service.list_all_projects_with_context()
        )
        self.add_field_label(
            self.body, "PARENT PROJECT (GOAL › MILESTONE › PROJECT) *"
        )

        if not self.project_choices:
            tk.Label(
                self.body,
                text="No projects exist yet. Create a Goal, Milestone, and Project first!",
                bg=p["warning_bg"],
                fg=p["warning"],
                font=("Segoe UI", 9, "bold"),
                padx=10,
                pady=6,
            ).pack(fill="x")
            self.proj_combo = None
        else:
            self.proj_combo = ttk.Combobox(
                self.body,
                values=[lbl for _, lbl in self.project_choices],
                state="readonly",
                font=("Segoe UI", 9),
            )
            target_pid = task.project_id if task else project_id
            idx = next(
                (
                    i
                    for i, (pid, _) in enumerate(self.project_choices)
                    if pid == target_pid
                ),
                0,
            )
            self.proj_combo.current(idx)
            self.proj_combo.pack(fill="x")

        self.add_field_label(self.body, "TASK TITLE *")
        self.title_ent = self.make_entry(self.body, task.title if task else "")
        self.title_ent.pack(fill="x", ipady=5)
        self.title_ent.focus_set()

        self.add_field_label(self.body, "NOTES / ACTION DETAILS")
        self.desc_ent = self.make_entry(
            self.body, task.description if task else ""
        )
        self.desc_ent.pack(fill="x", ipady=5)

        # Dates row
        row_dates = tk.Frame(self.body, bg=p["surface"])
        row_dates.pack(fill="x", pady=(6, 0))
        c1 = tk.Frame(row_dates, bg=p["surface"])
        c1.pack(side="left", fill="x", expand=True, padx=(0, 8))
        c2 = tk.Frame(row_dates, bg=p["surface"])
        c2.pack(side="left", fill="x", expand=True, padx=(8, 0))

        self.add_field_label(c1, "DUE DATE (YYYY-MM-DD)")
        self.due_ent = self.make_entry(
            c1,
            task.due_date
            if task and task.due_date
            else (date.today() + timedelta(days=2)).isoformat(),
        )
        self.due_ent.pack(fill="x", ipady=4)

        self.add_field_label(c2, "SCHEDULED WORK DATE (YYYY-MM-DD)")
        self.sched_ent = self.make_entry(
            c2,
            task.scheduled_date
            if task and task.scheduled_date
            else today_iso(),
        )
        self.sched_ent.pack(fill="x", ipady=4)

        # Priority & Duration row
        row_meta = tk.Frame(self.body, bg=p["surface"])
        row_meta.pack(fill="x", pady=(6, 0))
        cp = tk.Frame(row_meta, bg=p["surface"])
        cp.pack(side="left", fill="x", expand=True, padx=(0, 8))
        cd = tk.Frame(row_meta, bg=p["surface"])
        cd.pack(side="left", fill="x", expand=True, padx=(8, 0))

        self.add_field_label(cp, "PRIORITY")
        self.prio_combo = ttk.Combobox(
            cp, values=PRIORITIES, state="readonly"
        )
        self.prio_combo.set(task.priority if task else "medium")
        self.prio_combo.pack(fill="x")

        self.add_field_label(cd, "ESTIMATED DURATION (MINUTES)")
        self.est_ent = self.make_entry(
            cd, str(task.estimated_minutes if task else 45)
        )
        self.est_ent.pack(fill="x", ipady=4)

        if is_edit:
            row_st = tk.Frame(self.body, bg=p["surface"])
            row_st.pack(fill="x", pady=(6, 0))
            cs = tk.Frame(row_st, bg=p["surface"])
            cs.pack(side="left", fill="x", expand=True, padx=(0, 8))
            ca = tk.Frame(row_st, bg=p["surface"])
            ca.pack(side="left", fill="x", expand=True, padx=(8, 0))

            self.add_field_label(cs, "STATUS")
            self.status_combo = ttk.Combobox(
                cs, values=TASK_STATUSES, state="readonly"
            )
            self.status_combo.set(task.status)
            self.status_combo.pack(fill="x")

            self.add_field_label(ca, "ACTUAL DURATION (MINUTES)")
            self.act_ent = self.make_entry(ca, str(task.actual_minutes or 0))
            self.act_ent.pack(fill="x", ipady=4)

        tk.Button(
            self.footer,
            text="Cancel",
            bg=p["surface"],
            fg=p["text"],
            relief="flat",
            padx=14,
            pady=6,
            command=self.destroy,
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            self.footer,
            text="Save Task" if is_edit else "Create Task",
            bg=p["accent"],
            fg="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=18,
            pady=6,
            cursor="hand2",
            command=self._on_submit,
        ).pack(side="right")

    def _on_submit(self) -> None:
        if not self.project_choices or self.proj_combo is None:
            self.show_error(
                "Please create a Goal, Milestone, and Project before adding tasks."
            )
            return
        sel_idx = self.proj_combo.current()
        pid = self.project_choices[sel_idx][0] if sel_idx >= 0 else ""

        try:
            if self.task is None:
                created = self.controller.task_service.create_task(
                    project_id=pid,
                    title=self.title_ent.get(),
                    description=self.desc_ent.get(),
                    due_date=self.due_ent.get(),
                    scheduled_date=self.sched_ent.get(),
                    estimated_minutes=self.est_ent.get(),
                    priority=self.prio_combo.get(),
                )
                self.controller.show_toast(
                    f"Added task '{created.title}'", "positive"
                )
            else:
                new_status = self.status_combo.get()
                if new_status == "completed" and self.task.status != "completed":
                    self.controller.task_service.update_task(
                        task_id=self.task.id,
                        project_id=pid,
                        title=self.title_ent.get(),
                        description=self.desc_ent.get(),
                        due_date=self.due_ent.get(),
                        scheduled_date=self.sched_ent.get(),
                        estimated_minutes=self.est_ent.get(),
                        actual_minutes=self.act_ent.get(),
                        priority=self.prio_combo.get(),
                        status=self.task.status,
                    )
                    self.controller.toggle_task_completion(self.task.id)
                    self.destroy()
                    return
                updated = self.controller.task_service.update_task(
                    task_id=self.task.id,
                    project_id=pid,
                    title=self.title_ent.get(),
                    description=self.desc_ent.get(),
                    due_date=self.due_ent.get(),
                    scheduled_date=self.sched_ent.get(),
                    estimated_minutes=self.est_ent.get(),
                    actual_minutes=self.act_ent.get(),
                    priority=self.prio_combo.get(),
                    status=new_status,
                )
                self.controller.show_toast(
                    f"Updated task '{updated.title}'", "info"
                )
            self.controller.notify_data_changed("task_saved")
            self.destroy()
        except ValidationError as exc:
            self.show_error(str(exc))


class RescheduleDialog(BaseModalDialog):
    """Quick dialog for rescheduling a task with preset date shortcuts."""

    def __init__(
        self,
        parent: tk.Widget,
        controller: AppController,
        task: Task,
    ) -> None:
        super().__init__(
            parent,
            controller,
            title=f"Reschedule Task",
            width=440,
            height=360,
        )
        self.task = task
        p = self.colors

        tk.Label(
            self.body,
            text=task.title,
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            wraplength=390,
        ).pack(fill="x", pady=(0, 8))

        # Quick preset buttons
        preset_row = tk.Frame(self.body, bg=p["surface"])
        preset_row.pack(fill="x", pady=(0, 10))
        for label, offset in [
            ("Today", 0),
            ("Tomorrow", 1),
            ("+3 Days", 3),
            ("Next Week", 7),
        ]:
            tk.Button(
                preset_row,
                text=label,
                bg=p["surface_alt"],
                fg=p["accent"],
                font=("Segoe UI", 8, "bold"),
                relief="flat",
                padx=10,
                pady=4,
                cursor="hand2",
                command=lambda off=offset: self._apply_preset(off),
            ).pack(side="left", padx=(0, 6))

        self.add_field_label(self.body, "SCHEDULED WORK DATE (YYYY-MM-DD)")
        self.sched_ent = self.make_entry(
            self.body, task.scheduled_date or today_iso()
        )
        self.sched_ent.pack(fill="x", ipady=4)

        self.add_field_label(self.body, "DUE DATE (YYYY-MM-DD)")
        self.due_ent = self.make_entry(self.body, task.due_date or today_iso())
        self.due_ent.pack(fill="x", ipady=4)

        tk.Button(
            self.footer,
            text="Cancel",
            bg=p["surface"],
            fg=p["text"],
            relief="flat",
            padx=14,
            pady=6,
            command=self.destroy,
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            self.footer,
            text="Save Schedule",
            bg=p["accent"],
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._on_submit,
        ).pack(side="right")

    def _apply_preset(self, offset_days: int) -> None:
        target = (date.today() + timedelta(days=offset_days)).isoformat()
        self.sched_ent.delete(0, "end")
        self.sched_ent.insert(0, target)
        self.due_ent.delete(0, "end")
        self.due_ent.insert(0, target)

    def _on_submit(self) -> None:
        try:
            self.controller.task_service.reschedule_task(
                task_id=self.task.id,
                due_date=self.due_ent.get(),
                scheduled_date=self.sched_ent.get(),
            )
            self.controller.show_toast(
                f"Rescheduled '{self.task.title}'", "info"
            )
            self.controller.notify_data_changed("task_rescheduled")
            self.destroy()
        except ValidationError as exc:
            self.show_error(str(exc))
