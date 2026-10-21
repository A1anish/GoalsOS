"""Streamlined Task Planner page with 1-click filter pills, inline quick-add, and clean rows."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Tuple

from models.entities import Task
from ui.app_controller import AppController
from ui.components.dialogs import RescheduleDialog, TaskFormDialog
from ui.components.scrollable import ScrollableFrame
from utils.dates import format_duration, format_relative_deadline, today_iso


class TaskPlannerPage(tk.Frame):
    """Unified task execution and scheduling view with fast 1-click filter pills
    and an inline quick-add task bar.
    """

    def __init__(self, parent: tk.Widget, controller: AppController) -> None:
        self.controller = controller
        p = controller.colors
        super().__init__(parent, bg=p["bg"])

        default_sort = controller.settings_repo.get(
            "default_task_sort", "due_date"
        )
        self.quick_tab = tk.StringVar(value="active")  # 'active', 'today', 'overdue', 'upcoming', 'completed'
        self.goal_var = tk.StringVar(value="All Goals")
        self.sort_var = tk.StringVar(value=default_sort)
        self.search_var = tk.StringVar(value="")

        self._goal_map: List[Tuple[str, str]] = [("all", "All Goals")]
        self.scroll = ScrollableFrame(self, bg=p["bg"])
        self.scroll.pack(fill="both", expand=True)
        self.render()

    def apply_initial_filters(self) -> None:
        init = self.controller.planner_initial_filter
        if init:
            due = init.get("due")
            if due in ("today", "overdue"):
                self.quick_tab.set(due)
            elif init.get("status") == "all":
                self.quick_tab.set("active")
            self.controller.planner_initial_filter = {}

    def _set_quick_tab(self, tab_key: str) -> None:
        self.quick_tab.set(tab_key)
        self.render()

    def render(self) -> None:
        self.apply_initial_filters()
        p = self.controller.colors
        self.configure(bg=p["bg"])
        self.scroll.set_bg(p["bg"])
        container = self.scroll.inner

        for child in container.winfo_children():
            child.destroy()

        # --- Clean Header ---
        header = tk.Frame(container, bg=p["bg"], padx=32, pady=20)
        header.pack(fill="x")

        tk.Label(
            header,
            text="Task Planner",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).pack(side="left")

        # --- Inline Quick-Add Bar ---
        projects = self.controller.goal_service.list_all_projects_with_context()
        if projects:
            quick_card = tk.Frame(
                container,
                bg=p["surface"],
                highlightbackground=p["border"],
                highlightthickness=1,
                padx=16,
                pady=12,
            )
            quick_card.pack(fill="x", padx=32, pady=(0, 16))

            q_ent = tk.Entry(
                quick_card,
                bg=p["input_bg"],
                fg=p["text"],
                insertbackground=p["text"],
                highlightbackground=p["border"],
                highlightthickness=1,
                relief="flat",
                font=("Segoe UI", 10),
            )
            q_ent.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 10))

            proj_cb = ttk.Combobox(
                quick_card,
                values=[lbl for _, lbl in projects],
                state="readonly",
                width=32,
                font=("Segoe UI", 9),
            )
            proj_cb.current(0)
            proj_cb.pack(side="left", padx=(0, 10))

            def _inline_add(_e=None) -> None:
                title = q_ent.get().strip()
                if not title:
                    TaskFormDialog(self, self.controller)
                    return
                idx = proj_cb.current()
                pid = projects[idx][0] if idx >= 0 else projects[0][0]
                self.controller.task_service.create_task(
                    project_id=pid,
                    title=title,
                    due_date=today_iso(),
                    scheduled_date=today_iso(),
                )
                self.controller.show_toast(f"Added task '{title}'", "positive")
                self.controller.notify_data_changed("inline_task_added")

            q_ent.bind("<Return>", _inline_add)

            tk.Button(
                quick_card,
                text="+ Quick Add",
                bg=p["accent"],
                fg="#FFFFFF",
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                padx=14,
                pady=5,
                cursor="hand2",
                command=_inline_add,
            ).pack(side="right")

        # --- Streamlined 1-Row Filter Bar (Pills on Left, Goal & Sort on Right) ---
        filter_bar = tk.Frame(container, bg=p["bg"], padx=32)
        filter_bar.pack(fill="x", pady=(0, 14))

        cur_tab = self.quick_tab.get()
        for key, lbl in [
            ("active", "All Active"),
            ("today", "Due Today"),
            ("overdue", "Overdue"),
            ("upcoming", "Next 7 Days"),
            ("completed", "Completed"),
        ]:
            is_sel = cur_tab == key
            tk.Button(
                filter_bar,
                text=lbl,
                bg=p["accent"] if is_sel else p["surface"],
                fg="#FFFFFF" if is_sel else p["text_muted"],
                font=("Segoe UI", 9, "bold" if is_sel else "normal"),
                relief="flat",
                padx=12,
                pady=5,
                cursor="hand2",
                command=lambda k=key: self._set_quick_tab(k),
            ).pack(side="left", padx=(0, 6))

        right_f = tk.Frame(filter_bar, bg=p["bg"])
        right_f.pack(side="right")

        goals = [
            g
            for g in self.controller.goal_repo.list_all()
            if g.status != "archived"
        ]
        self._goal_map = [("all", "All Goals")] + [
            (g.id, g.title[:26]) for g in goals
        ]

        goal_cb = ttk.Combobox(
            right_f,
            textvariable=self.goal_var,
            values=[lbl for _, lbl in self._goal_map],
            state="readonly",
            width=20,
            font=("Segoe UI", 9),
        )
        goal_cb.pack(side="left", padx=(0, 8))
        goal_cb.bind("<<ComboboxSelected>>", lambda _e: self.render())

        sort_cb = ttk.Combobox(
            right_f,
            textvariable=self.sort_var,
            values=["due_date", "priority", "estimated_minutes", "created_at"],
            state="readonly",
            width=14,
            font=("Segoe UI", 9),
        )
        sort_cb.pack(side="left")
        sort_cb.bind("<<ComboboxSelected>>", lambda _e: self.render())

        # Map quick_tab to TaskService filter parameters
        status_filter = "completed" if cur_tab == "completed" else "active_only"
        due_filter = "all"
        if cur_tab == "today":
            due_filter = "today"
        elif cur_tab == "overdue":
            due_filter = "overdue"
        elif cur_tab == "upcoming":
            due_filter = "next_7_days"

        sel_goal_label = self.goal_var.get()
        goal_id_filter = next(
            (gid for gid, lbl in self._goal_map if lbl == sel_goal_label),
            "all",
        )

        tasks = self.controller.task_service.filter_and_sort_tasks(
            status_filter=status_filter,
            priority_filter="all",
            goal_id_filter=goal_id_filter,
            due_filter=due_filter,
            search_query=self.search_var.get(),
            sort_by=self.sort_var.get(),
        )

        # --- Task List ---
        list_frame = tk.Frame(container, bg=p["bg"], padx=32)
        list_frame.pack(fill="both", expand=True, pady=(0, 28))

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
                text="No tasks in this view.",
                bg=p["surface"],
                fg=p["text"],
                font=("Segoe UI", 11, "bold"),
            ).pack()
            return

        for t in tasks:
            self._build_planner_task_row(list_frame, t)

    def _build_planner_task_row(self, parent: tk.Widget, t: Task) -> None:
        p = self.controller.colors
        is_comp = t.status == "completed"
        is_canc = t.status == "cancelled"

        card = tk.Frame(
            parent,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=16,
            pady=11,
        )
        card.pack(fill="x", pady=(0, 8))

        bar = tk.Frame(card, bg=t.goal_color or p["accent"], width=4, height=34)
        bar.pack(side="left", fill="y", padx=(0, 12))

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

        main_col = tk.Frame(card, bg=p["surface"])
        main_col.pack(side="left", fill="x", expand=True)

        title_lbl = tk.Label(
            main_col,
            text=t.title,
            bg=p["surface"],
            fg=p["text_muted"] if (is_comp or is_canc) else p["text"],
            font=(
                "Segoe UI",
                10,
                "overstrike" if (is_comp or is_canc) else "bold",
            ),
            anchor="w",
            cursor="hand2",
        )
        title_lbl.pack(fill="x")
        title_lbl.bind(
            "<Button-1>",
            lambda _e, tid=t.id: self.controller.toggle_task_completion(tid),
        )

        goal_link = tk.Label(
            main_col,
            text=f"{t.goal_title}  ›  {t.project_title}   •   {format_duration(t.estimated_minutes)}",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 8),
            anchor="w",
            cursor="hand2",
        )
        goal_link.pack(fill="x", pady=(2, 0))
        goal_link.bind(
            "<Button-1>",
            lambda _e, gid=t.goal_id: self.controller.open_goal_detail(gid),
        )

        # Clean Right Metadata: Due Badge + Priority Badge + Context Menu
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
            padx=10,
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

        menu_btn = tk.Button(
            right_col,
            text="•••",
            bg=p["surface_alt"],
            fg=p["text_muted"],
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
        )
        menu_btn.pack(side="left", padx=(4, 0))
        menu_btn.bind(
            "<Button-1>", lambda e, task_o=t: self._show_task_menu(e, task_o)
        )

    def _show_task_menu(self, event: tk.Event, t: Task) -> None:
        p = self.controller.colors
        menu = tk.Menu(self, tearoff=0, bg=p["surface"], fg=p["text"])
        menu.add_command(
            label="Reschedule Dates…",
            command=lambda: RescheduleDialog(self, self.controller, task=t),
        )
        menu.add_command(
            label="Edit Task Details…",
            command=lambda: TaskFormDialog(self, self.controller, task=t),
        )
        menu.add_command(
            label="Open Parent Goal",
            command=lambda: self.controller.open_goal_detail(t.goal_id),
        )
        menu.add_separator()
        menu.add_command(
            label="Delete Task",
            foreground=p["danger"],
            command=lambda: self._delete_task(t),
        )
        menu.tk_popup(event.x_root, event.y_root)

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
