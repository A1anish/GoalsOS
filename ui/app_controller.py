"""Central application controller and state coordinator for GoalOS."""

from tkinter import messagebox
from typing import Callable, Dict, List, Optional

from database.connection import DatabaseManager
from repositories import (
    ActivityRepository,
    GoalRepository,
    MilestoneRepository,
    ProjectRepository,
    ReviewRepository,
    SettingsRepository,
    TaskRepository,
)
from services import (
    AnalyticsService,
    BackupService,
    GoalService,
    ProgressService,
    RecommendationService,
    ReviewService,
    TaskService,
)
from ui.theme import ThemeManager


class AppController:
    """Coordinates services, navigation state, theme updates, and UI refresh events."""

    def __init__(self, db_path: Optional[str] = None, seed_if_empty: bool = True) -> None:
        self.db = DatabaseManager(db_path)

        # Repositories
        self.goal_repo = GoalRepository(self.db)
        self.milestone_repo = MilestoneRepository(self.db)
        self.project_repo = ProjectRepository(self.db)
        self.task_repo = TaskRepository(self.db)
        self.review_repo = ReviewRepository(self.db)
        self.activity_repo = ActivityRepository(self.db)
        self.settings_repo = SettingsRepository(self.db)

        # Services
        self.progress_service = ProgressService(
            self.task_repo, self.goal_repo, self.settings_repo
        )
        self.goal_service = GoalService(
            self.goal_repo,
            self.milestone_repo,
            self.project_repo,
            self.task_repo,
            self.activity_repo,
            self.progress_service,
        )
        self.task_service = TaskService(
            self.task_repo,
            self.project_repo,
            self.milestone_repo,
            self.goal_repo,
            self.activity_repo,
            self.progress_service,
        )
        self.recommendation_service = RecommendationService(
            self.task_repo, self.project_repo
        )
        self.analytics_service = AnalyticsService(
            self.goal_repo,
            self.milestone_repo,
            self.project_repo,
            self.task_repo,
            self.settings_repo,
            self.progress_service,
        )
        self.review_service = ReviewService(
            self.review_repo,
            self.goal_repo,
            self.milestone_repo,
            self.task_repo,
            self.activity_repo,
        )
        self.backup_service = BackupService(
            self.db,
            self.goal_repo,
            self.milestone_repo,
            self.project_repo,
            self.task_repo,
            self.review_repo,
            self.activity_repo,
            self.settings_repo,
            self.goal_service,
            self.task_service,
            self.review_service,
        )

        if seed_if_empty:
            self.backup_service.seed_sample_data_if_empty(force=False)

        # Theme & UI State
        saved_theme = self.settings_repo.get("theme", "dark")
        saved_accent = self.settings_repo.get("accent_color", "#6366F1")
        self.theme = ThemeManager(mode=saved_theme, accent=saved_accent)

        self.current_page: str = "dashboard"
        self.selected_goal_id: Optional[str] = None
        self.global_search_query: str = ""
        self.planner_initial_filter: Dict[str, str] = {}

        self._listeners: List[Callable[[str], None]] = []
        self._toast_callback: Optional[Callable[[str, str], None]] = None
        self._nav_callback: Optional[Callable[[str], None]] = None

    @property
    def colors(self) -> Dict[str, str]:
        return self.theme.palette

    @property
    def fonts(self) -> Dict[str, tuple]:
        return self.theme.FONTS

    def register_listener(self, callback: Callable[[str], None]) -> None:
        if callback not in self._listeners:
            self._listeners.append(callback)

    def set_toast_handler(self, callback: Callable[[str, str], None]) -> None:
        self._toast_callback = callback

    def set_navigation_handler(self, callback: Callable[[str], None]) -> None:
        self._nav_callback = callback

    def show_toast(self, message: str, kind: str = "info") -> None:
        if self._toast_callback:
            self._toast_callback(message, kind)

    def notify_data_changed(self, event_name: str = "data_updated") -> None:
        for listener in list(self._listeners):
            try:
                listener(event_name)
            except Exception:
                pass

    def navigate(
        self,
        page_key: str,
        goal_id: Optional[str] = None,
        planner_filter: Optional[Dict[str, str]] = None,
    ) -> None:
        if goal_id is not None:
            self.selected_goal_id = goal_id
        if planner_filter is not None:
            self.planner_initial_filter = dict(planner_filter)
        self.current_page = page_key
        if self._nav_callback:
            self._nav_callback(page_key)

    def open_goal_detail(self, goal_id: str) -> None:
        self.selected_goal_id = goal_id
        self.navigate("goal_detail", goal_id=goal_id)

    def open_goal_explorer(self, goal_id: Optional[str] = None) -> None:
        if goal_id:
            self.selected_goal_id = goal_id
        elif not self.selected_goal_id:
            goals = self.goal_repo.list_all()
            if goals:
                self.selected_goal_id = goals[0].id
        self.navigate("goal_explorer", goal_id=self.selected_goal_id)

    def toggle_task_completion(self, task_id: str) -> None:
        """Centralized handler for completing or reopening a task from any screen."""
        task = self.task_repo.get_by_id(task_id)
        if not task:
            return

        if task.status != "completed":
            res = self.task_service.complete_task(task_id)
            pct = res["goal_progress"].percentage
            self.show_toast(
                f"Completed '{task.title}' — Goal now at {pct:.0f}%", "positive"
            )
            if res["suggest_goal_completion"] and res["goal"]:
                goal = res["goal"]
                if messagebox.askyesno(
                    "All Tasks Completed!",
                    f"Every eligible task under '{goal.title}' is now 100% complete!\n\nWould you like to mark the goal '{goal.title}' as Completed?",
                ):
                    self.goal_service.change_goal_status(goal.id, "completed")
                    self.show_toast(
                        f"Goal '{goal.title}' marked as Completed!", "positive"
                    )
        else:
            res = self.task_service.reopen_task(task_id)
            self.show_toast(f"Reopened '{task.title}'", "info")
            if res["prompt_reopen_goal"] and res["goal"]:
                goal = res["goal"]
                if messagebox.askyesno(
                    "Reopen Completed Goal?",
                    f"You reopened a task under '{goal.title}', which is currently marked as Completed.\n\nWould you like to reopen the goal to Active status?",
                ):
                    self.goal_service.change_goal_status(goal.id, "active")
                    self.show_toast(
                        f"Goal '{goal.title}' reopened to Active.", "warning"
                    )

        self.notify_data_changed("task_toggled")

    def switch_theme(self, mode: str, accent: Optional[str] = None) -> None:
        new_accent = accent or self.theme.accent
        self.settings_repo.set("theme", mode)
        self.settings_repo.set("accent_color", new_accent)
        self.theme.set_theme(mode, new_accent)
        self.notify_data_changed("theme_changed")
