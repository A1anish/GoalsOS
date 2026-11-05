"""Persistent left navigation sidebar component for GoalOS."""

import tkinter as tk
from typing import Dict, List, Tuple

from ui.app_controller import AppController


NAV_ITEMS: List[Tuple[str, str, str]] = [
    ("dashboard", "◈", "Dashboard"),
    ("goals", "◎", "My Goals"),
    ("goal_explorer", "❖", "Goal Explorer"),
    ("task_planner", "☑", "Task Planner"),
    ("timeline", "◷", "Timeline"),
    ("analytics", "▤", "Analytics"),
    ("weekly_review", "✦", "Weekly Review"),
]


class Sidebar(tk.Frame):
    """Persistent left sidebar with navigation links."""

    def __init__(self, parent: tk.Widget, controller: AppController) -> None:
        self.controller = controller
        p = controller.colors
        super().__init__(parent, bg=p["sidebar_bg"], width=235)
        self.pack_propagate(False)

        self._nav_buttons: Dict[str, Tuple[tk.Frame, tk.Frame, tk.Label]] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        for child in self.winfo_children():
            child.destroy()
        self._nav_buttons.clear()
        p = self.controller.colors
        self.configure(bg=p["sidebar_bg"])

        # Brand Logo Area
        brand = tk.Frame(self, bg=p["sidebar_bg"], padx=20, pady=20)
        brand.pack(fill="x")

        logo_badge = tk.Label(
            brand,
            text="G",
            bg=p["accent"],
            fg="#FFFFFF",
            font=("Segoe UI", 14, "bold"),
            width=2,
            pady=2,
        )
        logo_badge.pack(side="left", padx=(0, 10))

        title_col = tk.Frame(brand, bg=p["sidebar_bg"])
        title_col.pack(side="left", fill="x")
        tk.Label(
            title_col,
            text="GoalOS",
            bg=p["sidebar_bg"],
            fg="#F8FAFB",
            font=("Segoe UI", 14, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            title_col,
            text="Execution & Planning OS",
            bg=p["sidebar_bg"],
            fg="#94A3B8",
            font=("Segoe UI", 8),
            anchor="w",
        ).pack(fill="x")

        tk.Frame(self, bg="#1E293B", height=1).pack(
            fill="x", padx=16, pady=(0, 12)
        )

        # Navigation Section Label
        tk.Label(
            self,
            text="WORKSPACE",
            bg=p["sidebar_bg"],
            fg="#64748B",
            font=("Segoe UI", 8, "bold"),
            anchor="w",
            padx=22,
        ).pack(fill="x", pady=(0, 6))

        # Main Navigation Items
        nav_container = tk.Frame(self, bg=p["sidebar_bg"])
        nav_container.pack(fill="x")

        for key, icon, label in NAV_ITEMS:
            self._create_nav_item(nav_container, key, icon, label)

        self.set_active(self.controller.current_page)

    def _create_nav_item(
        self, parent: tk.Widget, key: str, icon: str, label: str
    ) -> None:
        p = self.controller.colors
        row = tk.Frame(parent, bg=p["sidebar_bg"], cursor="hand2")
        row.pack(fill="x", padx=10, pady=2)

        indicator = tk.Frame(row, bg=p["sidebar_bg"], width=4, height=34)
        indicator.pack(side="left", fill="y")

        lbl = tk.Label(
            row,
            text=f"  {icon}   {label}",
            bg=p["sidebar_bg"],
            fg="#94A3B8",
            font=("Segoe UI", 10),
            anchor="w",
            padx=8,
            pady=7,
        )
        lbl.pack(side="left", fill="x", expand=True)

        def on_click(_e=None, k=key) -> None:
            self.controller.navigate(k)

        row.bind("<Button-1>", on_click)
        lbl.bind("<Button-1>", on_click)
        self._nav_buttons[key] = (row, indicator, lbl)

    def set_active(self, active_key: str) -> None:
        p = self.controller.colors
        effective_key = (
            "goals" if active_key == "goal_detail" else active_key
        )
        for key, (row, indicator, lbl) in self._nav_buttons.items():
            if key == effective_key:
                row.configure(bg="#1E293B")
                indicator.configure(bg=p["accent"])
                lbl.configure(
                    bg="#1E293B",
                    fg="#FFFFFF",
                    font=("Segoe UI", 10, "bold"),
                )
            else:
                row.configure(bg=p["sidebar_bg"])
                indicator.configure(bg=p["sidebar_bg"])
                lbl.configure(
                    bg=p["sidebar_bg"],
                    fg="#94A3B8",
                    font=("Segoe UI", 10),
                )

    def refresh(self) -> None:
        self._build_ui()
