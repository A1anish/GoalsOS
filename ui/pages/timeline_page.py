"""Clean Chronological Agenda and Graphical Gantt view page for GoalOS."""

import tkinter as tk
from typing import Dict, List

from ui.app_controller import AppController
from ui.components.canvas_widgets import GanttTimelineCanvas
from ui.components.dialogs import RescheduleDialog
from ui.components.scrollable import ScrollableFrame
from utils.dates import format_relative_deadline


class TimelinePage(tk.Frame):
    """Displays either a clean Chronological Agenda or a full-width Graphical Gantt Chart."""

    def __init__(self, parent: tk.Widget, controller: AppController) -> None:
        self.controller = controller
        p = controller.colors
        super().__init__(parent, bg=p["bg"])

        self.view_mode = tk.StringVar(value="list")  # 'list' or 'gantt'
        self.scroll = ScrollableFrame(self, bg=p["bg"])
        self.scroll.pack(fill="both", expand=True)
        self.render()

    def _set_mode(self, mode: str) -> None:
        self.view_mode.set(mode)
        self.render()

    def render(self) -> None:
        p = self.controller.colors
        self.configure(bg=p["bg"])
        self.scroll.set_bg(p["bg"])
        container = self.scroll.inner

        for child in container.winfo_children():
            child.destroy()

        # Header
        header = tk.Frame(container, bg=p["bg"], padx=32, pady=20)
        header.pack(fill="x")

        tk.Label(
            header,
            text="Timeline & Deadlines",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).pack(side="left")

        mode_bar = tk.Frame(header, bg=p["surface"], padx=4, pady=4)
        mode_bar.pack(side="right")

        cur_mode = self.view_mode.get()
        for key, lbl in [
            ("list", "☰ Chronological Agenda"),
            ("gantt", "◷ Graphical Gantt Chart"),
        ]:
            is_sel = cur_mode == key
            tk.Button(
                mode_bar,
                text=lbl,
                bg=p["accent"] if is_sel else p["surface_alt"],
                fg="#FFFFFF" if is_sel else p["text_muted"],
                font=("Segoe UI", 9, "bold" if is_sel else "normal"),
                relief="flat",
                padx=14,
                pady=5,
                cursor="hand2",
                command=lambda k=key: self._set_mode(k),
            ).pack(side="left", padx=2)

        if cur_mode == "gantt":
            gantt_card = tk.Frame(
                container,
                bg=p["surface"],
                highlightbackground=p["border"],
                highlightthickness=1,
                padx=20,
                pady=18,
            )
            gantt_card.pack(fill="both", expand=True, padx=32, pady=(0, 28))

            tk.Label(
                gantt_card,
                text="35-DAY SCHEDULE HORIZON (MILESTONES & TASKS)",
                bg=p["surface"],
                fg=p["accent"],
                font=("Segoe UI", 9, "bold"),
                anchor="w",
            ).pack(fill="x", pady=(0, 12))

            gantt_rows = self._collect_gantt_rows()
            gantt_h = max(360, min(600, 70 + len(gantt_rows) * 36))
            gantt = GanttTimelineCanvas(
                gantt_card, colors=p, height=gantt_h
            )
            gantt.pack(fill="both", expand=True)
            gantt.set_items(gantt_rows)
            return

        # Chronological Agenda View
        buckets = self.controller.analytics_service.get_timeline_buckets()
        bucket_defs = [
            ("overdue", "Overdue", p["danger"]),
            ("today", "Due Today", p["warning"]),
            ("next_7_days", "Next 7 Days", p["info"]),
            ("later", "Later", p["accent"]),
            ("unscheduled", "Unscheduled", p["text_muted"]),
        ]

        any_rendered = False
        for b_key, b_title, b_color in bucket_defs:
            items = buckets.get(b_key, [])
            if items:
                any_rendered = True
                self._build_bucket_section(
                    container, b_title, items, b_color
                )

        if not any_rendered:
            empty = tk.Frame(
                container,
                bg=p["surface"],
                highlightbackground=p["border"],
                highlightthickness=1,
                padx=24,
                pady=36,
            )
            empty.pack(fill="x", padx=32)
            tk.Label(
                empty,
                text="No upcoming milestones or tasks on your timeline.",
                bg=p["surface"],
                fg=p["text"],
                font=("Segoe UI", 11, "bold"),
            ).pack()

    def _collect_gantt_rows(self) -> List[Dict]:
        rows: List[Dict] = []
        active_goals = {
            g.id: g
            for g in self.controller.goal_repo.list_all(status="active")
        }
        for m in self.controller.milestone_repo.list_all():
            g = active_goals.get(m.goal_id)
            if not g or m.status == "archived":
                continue
            if m.start_date or m.deadline:
                rows.append(
                    {
                        "type": "Milestone",
                        "title": f"{m.title} ({g.title[:16]})",
                        "start_date": m.start_date,
                        "end_date": m.deadline,
                        "color": g.color or self.controller.colors["accent"],
                    }
                )
        for t in self.controller.task_repo.list_all(include_archived_goals=False):
            if t.goal_status != "active" or t.status in ("completed", "cancelled"):
                continue
            if t.scheduled_date or t.due_date:
                rows.append(
                    {
                        "type": "Task",
                        "title": t.title,
                        "start_date": t.scheduled_date or t.due_date,
                        "end_date": t.due_date or t.scheduled_date,
                        "color": t.goal_color or self.controller.colors["info"],
                    }
                )
        return rows[:18]

    def _build_bucket_section(
        self,
        parent: tk.Widget,
        title: str,
        items: List[Dict],
        accent_color: str,
    ) -> None:
        p = self.controller.colors
        sec = tk.Frame(
            parent,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=20,
            pady=14,
        )
        sec.pack(fill="x", padx=32, pady=(0, 14))

        head = tk.Frame(sec, bg=p["surface"])
        head.pack(fill="x", pady=(0, 8))
        tk.Label(
            head,
            text=f"{title} ({len(items)})",
            bg=p["surface"],
            fg=accent_color,
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left")

        for item in items:
            row = tk.Frame(sec, bg=p["surface_alt"], padx=14, pady=8)
            row.pack(fill="x", pady=3)

            etype = item["entity_type"]
            badge_col = (
                p["info"]
                if etype == "Milestone"
                else (item["goal_color"] or p["accent"])
            )

            tk.Label(
                row,
                text=etype.upper(),
                bg=p["surface"],
                fg=badge_col,
                font=("Segoe UI", 7, "bold"),
                padx=6,
                pady=1,
            ).pack(side="left", padx=(0, 10))

            tk.Label(
                row,
                text=item["title"],
                bg=p["surface_alt"],
                fg=p["text"],
                font=("Segoe UI", 10, "bold"),
                anchor="w",
            ).pack(side="left")

            tk.Label(
                row,
                text=f"   •   {item['goal_title']}",
                bg=p["surface_alt"],
                fg=p["text_muted"],
                font=("Segoe UI", 8),
            ).pack(side="left")

            right = tk.Frame(row, bg=p["surface_alt"])
            right.pack(side="right")

            dl_lbl, dl_state = format_relative_deadline(item["due_date"])
            tk.Label(
                right,
                text=dl_lbl,
                bg=p["surface_alt"],
                fg=p.get(dl_state, p["text_muted"]),
                font=("Segoe UI", 8, "bold"),
                padx=8,
            ).pack(side="left")

            if etype == "Task":
                t_obj = item["raw"]
                tk.Button(
                    right,
                    text="✓ Done",
                    bg=p["positive"],
                    fg="#FFFFFF",
                    font=("Segoe UI", 8, "bold"),
                    relief="flat",
                    padx=10,
                    pady=2,
                    cursor="hand2",
                    command=lambda tid=t_obj.id: self.controller.toggle_task_completion(
                        tid
                    ),
                ).pack(side="left", padx=3)

                tk.Button(
                    right,
                    text="Reschedule",
                    bg=p["surface"],
                    fg=p["text_muted"],
                    font=("Segoe UI", 8),
                    relief="flat",
                    padx=8,
                    pady=2,
                    cursor="hand2",
                    command=lambda task_o=t_obj: RescheduleDialog(
                        self, self.controller, task=task_o
                    ),
                ).pack(side="left", padx=3)
            else:
                tk.Button(
                    right,
                    text="Open Goal →",
                    bg=p["surface"],
                    fg=p["text"],
                    font=("Segoe UI", 8),
                    relief="flat",
                    padx=8,
                    pady=2,
                    cursor="hand2",
                    command=lambda gid=item["goal_id"]: self.controller.open_goal_detail(
                        gid
                    ),
                ).pack(side="left", padx=3)
