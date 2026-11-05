"""Clean 7-Day Timeline list page for GoalOS."""

import tkinter as tk
from typing import Dict, List

from ui.app_controller import AppController
from ui.components.dialogs import RescheduleDialog
from ui.components.scrollable import ScrollableFrame
from utils.dates import format_relative_deadline


class TimelinePage(tk.Frame):
    """Displays the chronological 7-Day Schedule list."""

    def __init__(self, parent: tk.Widget, controller: AppController) -> None:
        self.controller = controller
        p = controller.colors
        super().__init__(parent, bg=p["bg"])

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

        # Header
        header = tk.Frame(container, bg=p["bg"], padx=32, pady=20)
        header.pack(fill="x")

        tk.Label(
            header,
            text="Timeline (Next 7 Days)",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).pack(side="left")

        # 7-Day Chronological List View (Today & Next 7 Days)
        buckets = self.controller.analytics_service.get_timeline_buckets()
        seven_day_items = buckets.get("today", []) + buckets.get("next_7_days", [])

        if seven_day_items:
            self._build_bucket_section(
                container, "Next 7 Days", seven_day_items, p["accent"]
            )
        else:
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
                text="No tasks or milestones scheduled in the next 7 days.",
                bg=p["surface"],
                fg=p["text"],
                font=("Segoe UI", 11, "bold"),
            ).pack()

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
