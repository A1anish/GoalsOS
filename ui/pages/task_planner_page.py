"""Unified Task Planner page with filtering, sorting, and quick actions."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Tuple

from models.entities import Task
from ui.app_controller import AppController
from ui.components.dialogs import RescheduleDialog, TaskFormDialog
from ui.components.scrollable import ScrollableFrame
from utils.dates import format_duration, format_relative_deadline


class TaskPlannerPage(tk.Frame):
    """Unified task execution and scheduling view across all active goals."""

    def __init__(self, parent: tk.Widget, controller: AppController) -> None:
        self.controller = controller
        p = controller.colors
        super().__init__(parent, bg=p["bg"])

        default_sort = controller.settings_repo.get(
            "default_task_sort", "due_date"
        )
        self.status_var = tk.StringVar(value="active_only")
        self.priority_var = tk.StringVar(value="all")
        self.goal_var = tk.StringVar(value="All Goals")
        self.due_var = tk.StringVar(value="all")
        self.sort_var = tk.StringVar(value=default_sort)
        self.search_var = tk.StringVar(value="")

        self._goal_map: List[Tuple[str, str]] = [("all", "All Goals")]
        self.scroll = ScrollableFrame(self, bg=p["bg"])
        self.scroll.pack(fill="both", expand=True)
        self.render()

    def apply_initial_filters(self) -> None:
        init = self.controller.planner_initial_filter
        if init:
            if "due" in init:
                self.due_var.set(init["due"])
            if "status" in init:
                self.status_var.set(init["status"])
            self.controller.planner_initial_filter = {}

    def render(self) -> None:
        self.apply_initial_filters()
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
        left_h.pack(side="left")
        tk.Label(
            left_h,
            text="Task Planner & Execution Queue",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            left_h,
            text="Filter, prioritize, schedule, and execute actionable tasks across all active goals.",
            bg=p["bg"],
            fg=p["text_muted"],
            font=("Segoe UI", 10),
            anchor="w",
        ).pack(anchor="w")

        tk.Button(
            header,
            text="+ New Task",
            bg=p["accent"],
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
            command=lambda: TaskFormDialog(self, self.controller),
        ).pack(side="right")

        # Filter & Sort Toolbar
        f_panel = tk.Frame(
            container,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=16,
            pady=12,
        )
        f_panel.pack(fill="x", padx=26, pady=(0, 16))

        row1 = tk.Frame(f_panel, bg=p["surface"])
        row1.pack(fill="x")

        # Status filter
        self._add_dropdown(
            row1,
            "Status:",
            self.status_var,
            [
                "active_only",
                "all",
                "todo",
                "in_progress",
                "completed",
                "cancelled",
            ],
            width=13,
        )

        # Due window filter
        self._add_dropdown(
            row1,
            "Due Window:",
            self.due_var,
            ["all", "overdue", "today", "next_7_days", "unscheduled"],
            width=13,
        )

        # Priority filter
        self._add_dropdown(
            row1,
            "Priority:",
            self.priority_var,
            ["all", "high", "medium", "low"],
            width=10,
        )

        # Goal filter
        goals = [
            g
            for g in self.controller.goal_repo.list_all()
            if g.status != "archived"
        ]
        self._goal_map = [("all", "All Goals")] + [
            (g.id, g.title[:28]) for g in goals
        ]
        self._add_dropdown(
            row1,
            "Goal:",
            self.goal_var,
            [lbl for _, lbl in self._goal_map],
            width=22,
        )

        # Sort by
        self._add_dropdown(
            row1,
            "Sort By:",
            self.sort_var,
            [
                "due_date",
                "priority",
                "estimated_minutes",
                "status",
                "created_at",
            ],
            width=15,
        )

        # Search input + Reset button on row 2
        row2 = tk.Frame(f_panel, bg=p["surface"], pady=6)
        row2.pack(fill="x")

        tk.Label(
            row2,
            text="Search Tasks:",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(0, 8))

        s_ent = tk.Entry(
            row2,
            textvariable=self.search_var,
            bg=p["input_bg"],
            fg=p["text"],
            insertbackground=p["text"],
            highlightbackground=p["border"],
            highlightthickness=1,
            relief="flat",
            width=36,
            font=("Segoe UI", 9),
        )
        s_ent.pack(side="left", ipady=4, padx=(0, 8))
        s_ent.bind("<Return>", lambda _e: self.render())

        tk.Button(
            row2,
            text="Apply Search",
            bg=p["accent"],
            fg="#FFFFFF",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.render,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            row2,
            text="Reset Filters",
            bg=p["surface_alt"],
            fg=p["text_muted"],
            font=("Segoe UI", 8),
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._reset_filters,
        ).pack(side="left")

        # Determine selected goal ID
        sel_goal_label = self.goal_var.get()
        goal_id_filter = next(
            (gid for gid, lbl in self._goal_map if lbl == sel_goal_label),
            "all",
        )

        tasks = self.controller.task_service.filter_and_sort_tasks(
            status_filter=self.status_var.get(),
            priority_filter=self.priority_var.get(),
            goal_id_filter=goal_id_filter,
            due_filter=self.due_var.get(),
            search_query=self.search_var.get(),
            sort_by=self.sort_var.get(),
        )

        total_est = sum(
            (t.estimated_minutes or 30)
            for t in tasks
            if t.status not in ("completed", "cancelled")
        )
        tk.Label(
            row2,
            text=f"Showing {len(tasks)} task(s)   •   Active Est. Workload: {format_duration(total_est)}",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 9, "bold"),
        ).pack(side="right")

        # Task Table / List
        list_frame = tk.Frame(container, bg=p["bg"], padx=26)
        list_frame.pack(fill="both", expand=True, pady=(0, 26))

        if not tasks:
            empty = tk.Frame(
                list_frame,
                bg=p["surface"],
                highlightbackground=p["border"],
                highlightthickness=1,
                padx=24,
                pady=36,
            )
            empty.pack(fill="x")
            tk.Label(
                empty,
                text="No tasks match your current filters.",
                bg=p["surface"],
                fg=p["text"],
                font=("Segoe UI", 11, "bold"),
            ).pack()
            tk.Label(
                empty,
                text="Try resetting filters or click '+ New Task' to schedule actionable work.",
                bg=p["surface"],
                fg=p["text_muted"],
                font=("Segoe UI", 9),
                pady=6,
            ).pack()
            return

        for t in tasks:
            self._build_planner_task_row(list_frame, t)

    def _add_dropdown(
        self,
        parent: tk.Widget,
        label: str,
        var: tk.StringVar,
        values: list,
        width: int = 12,
    ) -> None:
        p = self.controller.colors
        tk.Label(
            parent,
            text=label,
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left", padx=(0, 4))
        cb = ttk.Combobox(
            parent,
            textvariable=var,
            values=values,
            state="readonly",
            width=width,
            font=("Segoe UI", 9),
        )
        cb.pack(side="left", padx=(0, 12))
        cb.bind("<<ComboboxSelected>>", lambda _e: self.render())

    def _reset_filters(self) -> None:
        self.status_var.set("active_only")
        self.priority_var.set("all")
        self.goal_var.set("All Goals")
        self.due_var.set("all")
        self.search_var.set("")
        self.render()

    def _build_planner_task_row(self, parent: tk.Widget, t: Task) -> None:
        p = self.controller.colors
        is_comp = t.status == "completed"
        is_canc = t.status == "cancelled"

        card = tk.Frame(
            parent,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=14,
            pady=10,
        )
        card.pack(fill="x", pady=(0, 8))

        # Left color bar matching parent Goal
        bar = tk.Frame(card, bg=t.goal_color or p["accent"], width=4, height=38)
        bar.pack(side="left", fill="y", padx=(0, 10))

        # Checkbox
        chk = tk.Button(
            card,
            text="☑" if is_comp else ("☒" if is_canc else "☐"),
            bg=p["surface"],
            fg=p["positive"]
            if is_comp
            else (p["text_dim"] if is_canc else p["text_muted"]),
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            command=lambda tid=t.id: self.controller.toggle_task_completion(tid),
        )
        chk.pack(side="left", padx=(0, 10))

        # Main Text Column
        main_col = tk.Frame(card, bg=p["surface"])
        main_col.pack(side="left", fill="x", expand=True)

        title_row = tk.Frame(main_col, bg=p["surface"])
        title_row.pack(fill="x")

        tk.Label(
            title_row,
            text=t.title,
            bg=p["surface"],
            fg=p["text_muted"] if (is_comp or is_canc) else p["text"],
            font=(
                "Segoe UI",
                10,
                "overstrike" if (is_comp or is_canc) else "bold",
            ),
            anchor="w",
        ).pack(side="left")

        if t.status == "in_progress":
            tk.Label(
                title_row,
                text=" IN PROGRESS ",
                bg=p["info_bg"],
                fg=p["info"],
                font=("Segoe UI", 7, "bold"),
                padx=5,
                pady=1,
            ).pack(side="left", padx=8)

        sub_row = tk.Frame(main_col, bg=p["surface"])
        sub_row.pack(fill="x", pady=(2, 0))

        goal_link = tk.Label(
            sub_row,
            text=f"◎ {t.goal_title}  ›  ▣ {t.project_title}",
            bg=p["surface"],
            fg=t.goal_color or p["accent"],
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        )
        goal_link.pack(side="left")
        goal_link.bind(
            "<Button-1>",
            lambda _e, gid=t.goal_id: self.controller.open_goal_detail(gid),
        )

        if t.scheduled_date:
            tk.Label(
                sub_row,
                text=f"   •   Scheduled: {t.scheduled_date}",
                bg=p["surface"],
                fg=p["text_muted"],
                font=("Segoe UI", 8),
            ).pack(side="left")

        # Right side metadata & quick actions
        right_col = tk.Frame(card, bg=p["surface"])
        right_col.pack(side="right")

        dl_text, dl_state = format_relative_deadline(
            t.due_date, is_completed=is_comp
        )
        dl_col = p.get(dl_state, p["text_muted"])

        tk.Label(
            right_col,
            text=dl_text,
            bg=p["surface_alt"],
            fg=dl_col,
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=3,
        ).pack(side="left", padx=4)

        tk.Label(
            right_col,
            text=format_duration(t.estimated_minutes),
            bg=p["surface_alt"],
            fg=p["text_muted"],
            font=("Segoe UI", 8),
            padx=7,
            pady=3,
        ).pack(side="left", padx=4)

        prio_colors = {
            "high": p["danger"],
            "medium": p["warning"],
            "low": p["info"],
        }
        tk.Button(
            right_col,
            text=t.priority.upper(),
            bg=p["surface_alt"],
            fg=prio_colors.get(t.priority, p["text"]),
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=lambda tid=t.id: self._cycle_priority(tid),
        ).pack(side="left", padx=4)

        tk.Button(
            right_col,
            text="Reschedule",
            bg=p["surface_alt"],
            fg=p["text"],
            font=("Segoe UI", 8),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=lambda task_obj=t: RescheduleDialog(
                self, self.controller, task=task_obj
            ),
        ).pack(side="left", padx=3)

        tk.Button(
            right_col,
            text="Edit",
            bg=p["surface_alt"],
            fg=p["text"],
            font=("Segoe UI", 8),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=lambda task_obj=t: TaskFormDialog(
                self, self.controller, task=task_obj
            ),
        ).pack(side="left", padx=3)

        tk.Button(
            right_col,
            text="✕",
            bg=p["surface_alt"],
            fg=p["danger"],
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=lambda task_obj=t: self._delete_task(task_obj),
        ).pack(side="left", padx=(3, 0))

    def _cycle_priority(self, task_id: str) -> None:
        updated = self.controller.task_service.cycle_priority(task_id)
        self.controller.show_toast(
            f"Priority set to {updated.priority.upper()}", "info"
        )
        self.controller.notify_data_changed("priority_cycled")

    def _delete_task(self, t: Task) -> None:
        if messagebox.askyesno("Delete Task", f"Delete task '{t.title}'?"):
            self.controller.task_service.delete_task(t.id)
            self.controller.notify_data_changed("task_deleted")
