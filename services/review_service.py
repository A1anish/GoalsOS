"""Weekly Review aggregation and persistence service for GoalOS."""

from datetime import date, timedelta
from typing import Dict, List, Optional
import uuid

from models.entities import Goal, Milestone, Task, WeeklyReview
from repositories.activity_repository import ActivityRepository
from repositories.goal_repository import GoalRepository
from repositories.milestone_repository import MilestoneRepository
from repositories.review_repository import ReviewRepository
from repositories.task_repository import TaskRepository
from utils.dates import now_iso, parse_iso_date


class ReviewService:
    """Manages weekly review statistics and saves reflection records."""

    def __init__(
        self,
        review_repo: ReviewRepository,
        goal_repo: GoalRepository,
        milestone_repo: MilestoneRepository,
        task_repo: TaskRepository,
        activity_repo: ActivityRepository,
    ) -> None:
        self.review_repo = review_repo
        self.goal_repo = goal_repo
        self.milestone_repo = milestone_repo
        self.task_repo = task_repo
        self.activity_repo = activity_repo

    def get_past_week_summary(self, ref_date: Optional[date] = None) -> Dict:
        """Computes Step 1 review metrics over the last 7 days ending on ref_date."""
        ref = ref_date or date.today()
        start_d = ref - timedelta(days=6)

        all_tasks = self.task_repo.list_all(include_archived_goals=False)
        completed_tasks: List[Task] = []
        incomplete_tasks: List[Task] = []
        missed_deadlines: List[Task] = []
        active_goal_ids_with_progress = set()

        for t in all_tasks:
            if t.status == "completed" and t.completed_at:
                c_date = parse_iso_date(t.completed_at)
                if c_date and start_d <= c_date <= ref:
                    completed_tasks.append(t)
                    active_goal_ids_with_progress.add(t.goal_id)
            elif t.status in ("todo", "in_progress") and t.goal_status == "active":
                incomplete_tasks.append(t)
                due_d = parse_iso_date(t.due_date)
                if due_d and due_d < ref:
                    missed_deadlines.append(t)

        completed_milestones: List[Milestone] = []
        for m in self.milestone_repo.list_all():
            if m.status == "completed" and m.completed_at:
                mc_date = parse_iso_date(m.completed_at)
                if mc_date and start_d <= mc_date <= ref:
                    completed_milestones.append(m)
                    active_goal_ids_with_progress.add(m.goal_id)

        active_goals = self.goal_repo.list_all(status="active")
        stagnant_goals: List[Goal] = [
            g for g in active_goals if g.id not in active_goal_ids_with_progress
        ]

        return {
            "period_start": start_d.isoformat(),
            "period_end": ref.isoformat(),
            "completed_tasks": completed_tasks,
            "incomplete_tasks": incomplete_tasks,
            "completed_milestones": completed_milestones,
            "missed_deadlines": missed_deadlines,
            "stagnant_goals": stagnant_goals,
        }

    def save_weekly_review(
        self,
        period_start: str,
        period_end: str,
        went_well: str,
        challenges: str,
        lessons_learned: str,
        next_week_changes: str,
        planned_priorities: str,
        selected_goal_ids: List[str],
    ) -> WeeklyReview:
        ts = now_iso()
        review = WeeklyReview(
            id=str(uuid.uuid4()),
            period_start=period_start,
            period_end=period_end,
            went_well=(went_well or "").strip(),
            challenges=(challenges or "").strip(),
            lessons_learned=(lessons_learned or "").strip(),
            next_week_changes=(next_week_changes or "").strip(),
            planned_priorities=(planned_priorities or "").strip(),
            selected_goal_ids=list(selected_goal_ids or []),
            created_at=ts,
            updated_at=ts,
        )
        self.review_repo.create(review)
        self.activity_repo.log(
            "review",
            review.id,
            "created",
            f"Saved weekly review ({review.period_start} to {review.period_end})",
        )
        return review

    def list_reviews(self) -> List[WeeklyReview]:
        return self.review_repo.list_all()
