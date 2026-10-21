"""Rule-based Next Best Action recommendation engine for GoalOS."""

from datetime import date
from typing import Dict, List, Optional, Tuple

from models.entities import Recommendation, Task
from repositories.project_repository import ProjectRepository
from repositories.task_repository import TaskRepository
from utils.dates import days_until


class RecommendationService:
    """Computes transparent priority scores and explanations for eligible tasks."""

    WEIGHT_DEADLINE = 40.0
    WEIGHT_PRIORITY = 30.0
    WEIGHT_GOAL = 20.0
    WEIGHT_READINESS = 10.0

    PRIORITY_MAP: Dict[str, float] = {
        "high": 1.0,
        "medium": 0.6,
        "low": 0.3,
    }

    def __init__(
        self,
        task_repo: TaskRepository,
        project_repo: Optional[ProjectRepository] = None,
    ) -> None:
        self.task_repo = task_repo
        self.project_repo = project_repo

    @classmethod
    def score_deadline(
        cls, due_date: Optional[str], ref_date: Optional[date] = None
    ) -> Tuple[float, Optional[str]]:
        diff = days_until(due_date, reference_date=ref_date)
        if diff is None:
            return 0.2, None
        if diff < 0:
            days_late = abs(diff)
            label = (
                "overdue by 1 day"
                if days_late == 1
                else f"overdue by {days_late} days"
            )
            return 1.0, label
        if diff == 0:
            return 1.0, "due today"
        if diff == 1:
            return 0.85, "due tomorrow"
        if diff <= 3:
            return 0.8, f"due in {diff} days"
        if diff <= 7:
            return 0.6, f"due this week ({diff}d left)"
        return 0.3, None

    @classmethod
    def score_priority(cls, priority: str) -> Tuple[float, Optional[str]]:
        p = (priority or "medium").lower()
        score = cls.PRIORITY_MAP.get(p, 0.6)
        if p == "high":
            return score, "high priority"
        if p == "medium":
            return score, "medium priority"
        return score, "low priority"

    @classmethod
    def score_goal_importance(cls, goal_priority: str) -> Tuple[float, Optional[str]]:
        gp = (goal_priority or "medium").lower()
        score = cls.PRIORITY_MAP.get(gp, 0.6)
        if gp == "high":
            return score, "supports a high-priority goal"
        return score, None

    @classmethod
    def score_readiness(
        cls,
        task: Task,
        ref_date: Optional[date] = None,
    ) -> Tuple[float, Optional[str]]:
        sched_diff = days_until(task.scheduled_date, reference_date=ref_date)
        if sched_diff is not None and sched_diff <= 0:
            if task.status == "in_progress":
                return 1.0, "scheduled for today and already in progress"
            return 1.0, "scheduled for today"
        if task.status == "in_progress":
            return 0.9, "currently in progress"
        if (task.estimated_minutes or 30) <= 25:
            return 0.75, f"quick {task.estimated_minutes}m win"
        return 0.5, None

    def evaluate_task(
        self,
        task: Task,
        ref_date: Optional[date] = None,
    ) -> Recommendation:
        """Computes S = 40D + 30P + 20G + 10R and generates an explanation."""
        d_score, d_reason = self.score_deadline(task.due_date, ref_date=ref_date)
        p_score, p_reason = self.score_priority(task.priority)
        g_score, g_reason = self.score_goal_importance(task.goal_priority)
        r_score, r_reason = self.score_readiness(task, ref_date=ref_date)

        total = (
            self.WEIGHT_DEADLINE * d_score
            + self.WEIGHT_PRIORITY * p_score
            + self.WEIGHT_GOAL * g_score
            + self.WEIGHT_READINESS * r_score
        )

        factors: List[str] = []
        if d_reason:
            factors.append(d_reason)
        if p_reason and (p_score >= 0.6 or not factors):
            factors.append(p_reason)
        if r_reason:
            factors.append(r_reason)
        if g_reason and len(factors) < 3:
            factors.append(g_reason)

        if not factors:
            factors.append("ready to start")

        explanation = f"{task.title} — " + ", ".join(factors[:3]) + "."

        return Recommendation(
            task=task,
            total_score=round(total, 1),
            deadline_score=d_score,
            priority_score=p_score,
            goal_score=g_score,
            readiness_score=r_score,
            explanation=explanation,
            factors=factors,
        )

    def get_recommendations(
        self,
        limit: int = 3,
        include_future_scheduled: bool = False,
        ref_date: Optional[date] = None,
    ) -> List[Recommendation]:
        """Returns the top recommended tasks across all active goals and active projects."""
        all_tasks = self.task_repo.list_all(include_archived_goals=False)
        active_project_ids = None
        if self.project_repo is not None:
            active_project_ids = {
                p.id
                for p in self.project_repo.list_all()
                if p.status == "active"
            }

        eligible_recommendations: List[Recommendation] = []
        for t in all_tasks:
            # Exclude completed or cancelled tasks
            if t.status in ("completed", "cancelled"):
                continue
            # Exclude tasks under paused, completed, or archived goals
            if t.goal_status != "active":
                continue
            # Exclude tasks under completed/archived projects if project_repo available
            if active_project_ids is not None and t.project_id not in active_project_ids:
                continue
            # Exclude future-scheduled tasks unless work-ahead requested
            if not include_future_scheduled and t.scheduled_date:
                sched_diff = days_until(t.scheduled_date, reference_date=ref_date)
                if sched_diff is not None and sched_diff > 0:
                    continue

            rec = self.evaluate_task(t, ref_date=ref_date)
            eligible_recommendations.append(rec)

        eligible_recommendations.sort(
            key=lambda r: (
                -r.total_score,
                r.task.due_date or "9999-12-31",
                r.task.position,
            )
        )
        return eligible_recommendations[:limit]
