"""Main application window and navigation shell for GoalOS."""

import tkinter as tk
from typing import Dict, Optional, Type

from ui.app_controller import AppController
from ui.components.dialogs import GoalFormDialog, TaskFormDialog
from ui.components.sidebar import Sidebar
from ui.pages import (
    AnalyticsPage,
    DashboardPage,
    GoalDetailPage,
    GoalExplorerPage,
    GoalsPage,
    SettingsPage,
    TaskPlannerPage,
    TimelinePage,
    WeeklyReviewPage,
)


PAGE_CLASSES: Dict[str, Type[tk.Frame]] = {
    "dashboard": DashboardPage,
    "goals": GoalsPage,
    "goal_detail": GoalDetailPage,
    "goal_explorer": GoalExplorerPage,
    "task_planner": TaskPlannerPage,
    "timeline": TimelinePage,
    "analytics": AnalyticsPage,
    "weekly_review": WeeklyReviewPage,
    "settings": SettingsPage,
}

PAGE_TITLES: Dict[str, str] = {
    "dashboard": "Dashboard  ›  Overview & Next Best Actions",
    "goals": "My Goals  ›  Long-Term Outcomes",
    "goal_detail": "My Goals  ›  Goal Execution Workspace",
    "goal_explorer": "Goal Explorer  ›  Hierarchical Tree & Node Canvas",
    "task_planner": "Task Planner  ›  Unified Action Queue",
    "timeline": "Timeline  ›  Deadlines & Graphical Gantt",
    "analytics": "Analytics  ›  Completion History & Performance",
    "weekly_review": "Weekly Review  ›  Reflect & Plan",
    "settings": "Settings  ›  Appearance & Database Management",
}


class MainWindow(tk.Tk):
    """Root Tkinter desktop window for GoalOS."""

    def __init__(self, controller: AppController) -> None:
        super().__init__()
        self.controller = controller
        self.title("GoalOS — Personal Goal Planning & Execution System")
        self.geometry("1440x900")
        self.minsize(1100, 700)

        self.controller.theme.apply_to_root(self)
        self.configure(bg=self.controller.colors["bg"])

        self._active_page_widget: Optional[tk.Frame] = None
        self._toast_frame: Optional[tk.Frame] = None
        self._toast_after_id: Optional[str] = None
        self.global_search_var = tk.StringVar(value="")

        # Wire controller callbacks
        self.controller.set_navigation_handler(self._on_navigate)
        self.controller.set_toast_handler(self._show_toast)
        self.controller.register_listener(self._on_data_or_theme_changed)

        # Keyboard shortcuts
        self.bind("<Control-n>", lambda _e: GoalFormDialog(self, self.controller))
        self.bind("<Control-t>", lambda _e: TaskFormDialog(self, self.controller))

        self._build_shell()
        self._on_navigate(self.controller.current_page)

    def _build_shell(self) -> None:
        p = self.controller.colors
        self.configure(bg=p["bg"])

        # 1. Persistent Left Sidebar
        self.sidebar = Sidebar(self, self.controller)
        self.sidebar.pack(side="left", fill="y")

        # Right side container (Top Header + Main Content Area)
        self.right_shell = tk.Frame(self, bg=p["bg"])
        self.right_shell.pack(side="left", fill="both", expand=True)

        # 2. Top Global Header Bar
        self.top_bar = tk.Frame(
            self.right_shell,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=32,
            pady=10,
        )
        self.top_bar.pack(fill="x", side="top")

        self.breadcrumb_lbl = tk.Label(
            self.top_bar,
            text="Dashboard",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 10, "bold"),
        )
        self.breadcrumb_lbl.pack(side="left")

        # Global actions on right of top bar
        top_actions = tk.Frame(self.top_bar, bg=p["surface"])
        top_actions.pack(side="right")

        # Quick Global Task Search (press Enter)
        tk.Label(
            top_actions,
            text="⌕",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 10),
        ).pack(side="left", padx=(0, 4))

        self.search_entry = tk.Entry(
            top_actions,
            textvariable=self.global_search_var,
            bg=p["input_bg"],
            fg=p["text"],
            insertbackground=p["text"],
            highlightbackground=p["border"],
            highlightcolor=p["accent"],
            highlightthickness=1,
            relief="flat",
            width=22,
            font=("Segoe UI", 9),
        )
        self.search_entry.pack(side="left", ipady=4, padx=(0, 14))
        self.search_entry.bind("<Return>", self._on_global_search)

        # Quick Theme Switcher button
        theme_icon = "☀" if self.controller.theme.mode == "dark" else "🌙"
        self.theme_btn = tk.Button(
            top_actions,
            text=theme_icon,
            bg=p["surface_alt"],
            fg=p["text"],
            font=("Segoe UI", 10),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._toggle_theme_quick,
        )
        self.theme_btn.pack(side="left", padx=(0, 8))

        tk.Button(
            top_actions,
            text="+ Task",
            bg=p["surface_alt"],
            fg=p["text"],
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=lambda: TaskFormDialog(self, self.controller),
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            top_actions,
            text="+ New Goal",
            bg=p["accent"],
            fg="#FFFFFF",
            activebackground=p["accent_hover"],
            activeforeground="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=4,
            cursor="hand2",
            command=lambda: GoalFormDialog(self, self.controller),
        ).pack(side="left")

        # 3. Main Content Host
        self.content_host = tk.Frame(self.right_shell, bg=p["bg"])
        self.content_host.pack(fill="both", expand=True)

    def _on_global_search(self, _event: Optional[tk.Event] = None) -> None:
        q = self.global_search_var.get().strip()
        self.controller.navigate("task_planner", planner_filter={"status": "all"})
        if isinstance(self._active_page_widget, TaskPlannerPage):
            self._active_page_widget.search_var.set(q)
            self._active_page_widget.render()

    def _toggle_theme_quick(self) -> None:
        next_mode = (
            "light" if self.controller.theme.mode == "dark" else "dark"
        )
        self.controller.switch_theme(next_mode)

    def _on_navigate(self, page_key: str) -> None:
        p = self.controller.colors
        self.sidebar.set_active(page_key)
        self.breadcrumb_lbl.configure(
            text=PAGE_TITLES.get(page_key, "GoalOS")
        )

        if self._active_page_widget is not None:
            self._active_page_widget.destroy()
            self._active_page_widget = None

        page_cls = PAGE_CLASSES.get(page_key, DashboardPage)
        self._active_page_widget = page_cls(self.content_host, self.controller)
        self._active_page_widget.pack(fill="both", expand=True)

    def _on_data_or_theme_changed(self, event_name: str) -> None:
        if event_name == "theme_changed":
            self.controller.theme.apply_to_root(self)
            for child in self.winfo_children():
                child.destroy()
            self._active_page_widget = None
            self._build_shell()
            self._on_navigate(self.controller.current_page)
            return

        self.sidebar.refresh()
        if self._active_page_widget is not None and hasattr(
            self._active_page_widget, "render"
        ):
            self._active_page_widget.render()

    def _show_toast(self, message: str, kind: str = "info") -> None:
        if self._toast_frame is not None and self._toast_frame.winfo_exists():
            self._toast_frame.destroy()
        if self._toast_after_id is not None:
            try:
                self.after_cancel(self._toast_after_id)
            except Exception:
                pass

        p = self.controller.colors
        bg_map = {
            "positive": p["positive"],
            "warning": p["warning"],
            "danger": p["danger"],
            "info": p["accent"],
        }
        badge_bg = bg_map.get(kind, p["accent"])

        self._toast_frame = tk.Frame(
            self,
            bg=badge_bg,
            padx=16,
            pady=10,
            highlightbackground="#FFFFFF",
            highlightthickness=1,
        )
        tk.Label(
            self._toast_frame,
            text=f"✦  {message}",
            bg=badge_bg,
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
        ).pack()

        self._toast_frame.place(relx=0.98, rely=0.96, anchor="se")
        self._toast_after_id = self.after(3200, self._dismiss_toast)

    def _dismiss_toast(self) -> None:
        if self._toast_frame is not None and self._toast_frame.winfo_exists():
            self._toast_frame.destroy()
        self._toast_frame = None
        self._toast_after_id = None
