"""Progress calculation service for GoalOS."""

from typing import Dict, Iterable, List

from models.entities import ProgressStats, Task
from repositories.activity_repository import SettingsRepository
from repositories.goal_repository import GoalRepository
from repositories.task_repository import TaskRepository


class ProgressService:
    """Calculates bottom-up progress across Tasks, Projects, Milestones, and Goals."""

    def __init__(
        self,
        task_repo: TaskRepository,
        goal_repo: GoalRepository,
        settings_repo: SettingsRepository,
    ) -> None:
        self.task_repo = task_repo
        self.goal_repo = goal_repo
        self.settings_repo = settings_repo

    def is_effort_weighted(self) -> bool:
        return (
            self.settings_repo.get("effort_weighted_progress", "false").lower()
            == "true"
        )

    def compute_from_tasks(
        self,
        entity_id: str,
        entity_type: str,
        tasks: Iterable[Task],
        effort_weighted: bool = False,
    ) -> ProgressStats:
        """Computes ProgressStats directly from an iterable of Task entities.
        Cancelled tasks are excluded from the eligible denominator.
        """
        completed_count = 0
        eligible_count = 0
        cancelled_count = 0
        completed_mins = 0
        eligible_mins = 0

        for t in tasks:
            if t.status == "cancelled":
                cancelled_count += 1
                continue
            eligible_count += 1
            est = max(t.estimated_minutes or 30, 1)
            eligible_mins += est
            if t.status == "completed":
                completed_count += 1
                completed_mins += est

        return ProgressStats(
            entity_id=entity_id,
            entity_type=entity_type,
            completed_tasks=completed_count,
            total_eligible_tasks=eligible_count,
            cancelled_tasks=cancelled_count,
            completed_minutes=completed_mins,
            total_eligible_minutes=eligible_mins,
            effort_weighted=effort_weighted,
        )

    def get_project_progress(self, project_id: str) -> ProgressStats:
        tasks = self.task_repo.list_by_project(project_id)
        return self.compute_from_tasks(
            project_id,
            "project",
            tasks,
            effort_weighted=self.is_effort_weighted(),
        )

    def get_milestone_progress(self, milestone_id: str) -> ProgressStats:
        tasks = self.task_repo.list_by_milestone(milestone_id)
        return self.compute_from_tasks(
            milestone_id,
            "milestone",
            tasks,
            effort_weighted=self.is_effort_weighted(),
        )

    def get_goal_progress(self, goal_id: str) -> ProgressStats:
        tasks = self.task_repo.list_by_goal(goal_id)
        return self.compute_from_tasks(
            goal_id,
            "goal",
            tasks,
            effort_weighted=self.is_effort_weighted(),
        )

    def get_all_active_goals_progress(self) -> ProgressStats:
        """Calculates aggregate progress across all active goals."""
        active_goals = self.goal_repo.list_all(status="active")
        all_tasks: List[Task] = []
        for g in active_goals:
            all_tasks.extend(self.task_repo.list_by_goal(g.id))
        return self.compute_from_tasks(
            "all_active_goals",
            "overall",
            all_tasks,
            effort_weighted=self.is_effort_weighted(),
        )

    def get_goal_hierarchy_progress_map(self, goal_id: str) -> Dict[str, ProgressStats]:
        """Returns a dictionary mapping goal_id, every milestone_id, and every project_id
        under the goal to its ProgressStats in a single query pass.
        """
        tasks = self.task_repo.list_by_goal(goal_id)
        weighted = self.is_effort_weighted()
        by_milestone: Dict[str, List[Task]] = {}
        by_project: Dict[str, List[Task]] = {}

        for t in tasks:
            by_milestone.setdefault(t.milestone_id, []).append(t)
            by_project.setdefault(t.project_id, []).append(t)

        result: Dict[str, ProgressStats] = {
            goal_id: self.compute_from_tasks(goal_id, "goal", tasks, weighted)
        }
        for mid, m_tasks in by_milestone.items():
            result[mid] = self.compute_from_tasks(mid, "milestone", m_tasks, weighted)
        for pid, p_tasks in by_project.items():
            result[pid] = self.compute_from_tasks(pid, "project", p_tasks, weighted)
        return result
