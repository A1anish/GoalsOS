"""Task management, filtering, sorting, and completion workflow service."""

from datetime import date
from typing import Dict, List, Optional
import uuid

from models.entities import Task
from repositories.activity_repository import ActivityRepository
from repositories.goal_repository import GoalRepository
from repositories.milestone_repository import MilestoneRepository
from repositories.project_repository import ProjectRepository
from repositories.task_repository import TaskRepository
from services.progress_service import ProgressService
from utils.dates import classify_deadline, days_until, now_iso, today_iso
from utils.validators import (
    ValidationError,
    validate_duration,
    validate_non_empty,
    validate_optional_date,
    validate_priority,
    validate_task_status,
)


class TaskService:
    """Manages Tasks, completion/reopen rules, filtering, and sorting."""

    def __init__(
        self,
        task_repo: TaskRepository,
        project_repo: ProjectRepository,
        milestone_repo: MilestoneRepository,
        goal_repo: GoalRepository,
        activity_repo: ActivityRepository,
        progress_service: ProgressService,
    ) -> None:
        self.task_repo = task_repo
        self.project_repo = project_repo
        self.milestone_repo = milestone_repo
        self.goal_repo = goal_repo
        self.activity_repo = activity_repo
        self.progress_service = progress_service

    def create_task(
        self,
        project_id: str,
        title: str,
        description: str = "",
        due_date: Optional[str] = None,
        scheduled_date: Optional[str] = None,
        estimated_minutes: object = 30,
        priority: str = "medium",
    ) -> Task:
        if not project_id or not self.project_repo.get_by_id(project_id):
            raise ValidationError(
                "A task must belong to a valid project. Please select or create a project first."
            )
        clean_title = validate_non_empty(title, "Task title")
        clean_due = validate_optional_date(due_date, "Due date")
        clean_sched = validate_optional_date(scheduled_date, "Scheduled date")
        clean_est = validate_duration(estimated_minutes, "Estimated duration")
        clean_prio = validate_priority(priority)
        pos = self.task_repo.get_next_position(project_id)
        ts = now_iso()

        task = Task(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title=clean_title,
            description=(description or "").strip(),
            due_date=clean_due,
            scheduled_date=clean_sched,
            estimated_minutes=clean_est,
            actual_minutes=0,
            priority=clean_prio,
            status="todo",
            position=pos,
            created_at=ts,
            updated_at=ts,
        )
        created = self.task_repo.create(task)
        self.activity_repo.log(
            "task",
            created.id,
            "created",
            f"Added task '{created.title}' ({created.project_title})",
        )
        return created

    def update_task(
        self,
        task_id: str,
        title: str,
        description: str = "",
        project_id: Optional[str] = None,
        due_date: Optional[str] = None,
        scheduled_date: Optional[str] = None,
        estimated_minutes: object = 30,
        actual_minutes: object = 0,
        priority: str = "medium",
        status: Optional[str] = None,
    ) -> Task:
        existing = self.task_repo.get_by_id(task_id)
        if not existing:
            raise ValidationError("Task not found.")

        target_pid = project_id or existing.project_id
        if not self.project_repo.get_by_id(target_pid):
            raise ValidationError("Selected parent project does not exist.")

        clean_title = validate_non_empty(title, "Task title")
        clean_due = validate_optional_date(due_date, "Due date")
        clean_sched = validate_optional_date(scheduled_date, "Scheduled date")
        clean_est = validate_duration(estimated_minutes, "Estimated duration")
        clean_act = validate_duration(actual_minutes, "Actual duration")
        clean_prio = validate_priority(priority)
        new_status = (
            validate_task_status(status) if status else existing.status
        )
        ts = now_iso()

        old_status = existing.status
        existing.project_id = target_pid
        existing.title = clean_title
        existing.description = (description or "").strip()
        existing.due_date = clean_due
        existing.scheduled_date = clean_sched
        existing.estimated_minutes = clean_est
        existing.actual_minutes = clean_act
        existing.priority = clean_prio
        existing.status = new_status
        existing.updated_at = ts

        if new_status == "completed" and old_status != "completed":
            existing.completed_at = ts
        elif new_status != "completed":
            existing.completed_at = None

        updated = self.task_repo.update(existing)
        if old_status != new_status:
            self.activity_repo.log(
                "task",
                updated.id,
                f"status_{new_status}",
                f"Task '{updated.title}' marked {new_status.replace('_', ' ')}",
            )
        else:
            self.activity_repo.log(
                "task", updated.id, "updated", f"Updated task '{updated.title}'"
            )
        return updated

    def complete_task(self, task_id: str, completed_at: Optional[str] = None) -> Dict:
        """Marks a task completed, recalculates ancestor progress, and checks if
        the parent goal is now 100% complete so the UI can suggest goal completion.
        """
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise ValidationError("Task not found.")

        ts = completed_at or now_iso()
        task.status = "completed"
        task.completed_at = ts
        task.updated_at = ts
        if task.actual_minutes == 0:
            task.actual_minutes = task.estimated_minutes

        updated = self.task_repo.update(task)
        self.activity_repo.log(
            "task",
            updated.id,
            "completed",
            f"Completed task '{updated.title}' ({updated.goal_title})",
            created_at=ts,
        )

        # Auto-sync milestone status if all tasks in milestone are completed
        m_stats = self.progress_service.get_milestone_progress(updated.milestone_id)
        milestone = self.milestone_repo.get_by_id(updated.milestone_id)
        if (
            milestone
            and m_stats.has_eligible_tasks
            and m_stats.completed_tasks == m_stats.total_eligible_tasks
            and milestone.status != "completed"
        ):
            milestone.status = "completed"
            milestone.completed_at = ts
            milestone.updated_at = ts
            self.milestone_repo.update(milestone)
            self.activity_repo.log(
                "milestone",
                milestone.id,
                "completed",
                f"All tasks finished — milestone '{milestone.title}' completed!",
                created_at=ts,
            )

        goal_stats = self.progress_service.get_goal_progress(updated.goal_id)
        goal = self.goal_repo.get_by_id(updated.goal_id)
        suggest_goal_completion = bool(
            goal
            and goal.status == "active"
            and goal_stats.has_eligible_tasks
            and goal_stats.completed_tasks == goal_stats.total_eligible_tasks
        )

        return {
            "task": updated,
            "goal_progress": goal_stats,
            "suggest_goal_completion": suggest_goal_completion,
            "goal": goal,
        }

    def reopen_task(self, task_id: str) -> Dict:
        """Reopens a completed or cancelled task to 'todo', recalculates ancestor progress,
        and signals if the parent goal is currently marked 'completed'.
        """
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise ValidationError("Task not found.")

        ts = now_iso()
        task.status = "todo"
        task.completed_at = None
        task.updated_at = ts
        updated = self.task_repo.update(task)

        self.activity_repo.log(
            "task",
            updated.id,
            "reopened",
            f"Reopened task '{updated.title}'",
        )

        # If parent milestone was completed, set it back to active
        milestone = self.milestone_repo.get_by_id(updated.milestone_id)
        if milestone and milestone.status == "completed":
            milestone.status = "active"
            milestone.completed_at = None
            milestone.updated_at = ts
            self.milestone_repo.update(milestone)

        goal = self.goal_repo.get_by_id(updated.goal_id)
        goal_was_completed = bool(goal and goal.status == "completed")
        goal_stats = self.progress_service.get_goal_progress(updated.goal_id)

        return {
            "task": updated,
            "goal_progress": goal_stats,
            "prompt_reopen_goal": goal_was_completed,
            "goal": goal,
        }

    def reschedule_task(
        self,
        task_id: str,
        due_date: Optional[str] = None,
        scheduled_date: Optional[str] = None,
    ) -> Task:
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise ValidationError("Task not found.")
        if due_date is not None:
            task.due_date = validate_optional_date(due_date, "Due date")
        if scheduled_date is not None:
            task.scheduled_date = validate_optional_date(
                scheduled_date, "Scheduled date"
            )
        task.updated_at = now_iso()
        updated = self.task_repo.update(task)
        self.activity_repo.log(
            "task",
            updated.id,
            "rescheduled",
            f"Rescheduled '{updated.title}' (due: {updated.due_date or 'none'}, scheduled: {updated.scheduled_date or 'none'})",
        )
        return updated

    def cycle_priority(self, task_id: str) -> Task:
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise ValidationError("Task not found.")
        order = ["low", "medium", "high"]
        next_idx = (order.index(task.priority) + 1) % len(order) if task.priority in order else 1
        task.priority = order[next_idx]
        task.updated_at = now_iso()
        return self.task_repo.update(task)

    def reorder_task(self, task_id: str, direction: int) -> None:
        t = self.task_repo.get_by_id(task_id)
        if not t:
            return
        siblings = self.task_repo.list_by_project(t.project_id)
        idx = next((i for i, s in enumerate(siblings) if s.id == t.id), -1)
        target_idx = idx + direction
        if idx < 0 or target_idx < 0 or target_idx >= len(siblings):
            return
        siblings[idx], siblings[target_idx] = siblings[target_idx], siblings[idx]
        for pos, item in enumerate(siblings):
            item.position = pos
            self.task_repo.update(item)

    def delete_task(self, task_id: str) -> None:
        task = self.task_repo.get_by_id(task_id)
        if not task:
            return
        self.task_repo.delete(task_id)
        self.activity_repo.log(
            "task", task_id, "deleted", f"Deleted task '{task.title}'"
        )

    def filter_and_sort_tasks(
        self,
        status_filter: str = "all",
        priority_filter: str = "all",
        goal_id_filter: str = "all",
        due_filter: str = "all",
        search_query: str = "",
        sort_by: str = "due_date",
        include_paused_goals: bool = False,
        ref_date: Optional[date] = None,
    ) -> List[Task]:
        """Filters and sorts tasks across all goals according to planner criteria."""
        tasks = self.task_repo.list_all(include_archived_goals=False)
        filtered: List[Task] = []
        q = (search_query or "").strip().lower()

        for t in tasks:
            if not include_paused_goals and t.goal_status == "paused" and goal_id_filter == "all":
                continue
            if status_filter != "all":
                if status_filter == "active_only" and t.status in ("completed", "cancelled"):
                    continue
                elif status_filter != "active_only" and t.status != status_filter:
                    continue
            if priority_filter != "all" and t.priority != priority_filter:
                continue
            if goal_id_filter != "all" and t.goal_id != goal_id_filter:
                continue

            if due_filter != "all":
                is_comp = t.status == "completed"
                bucket = classify_deadline(t.due_date, is_completed=is_comp, reference_date=ref_date)
                sched_diff = days_until(t.scheduled_date, reference_date=ref_date)
                if due_filter == "overdue" and bucket != "overdue":
                    continue
                if due_filter == "today" and not (bucket == "today" or (sched_diff == 0 and not is_comp)):
                    continue
                if due_filter == "next_7_days" and bucket not in ("today", "next_7_days"):
                    continue
                if due_filter == "unscheduled" and (t.due_date or t.scheduled_date):
                    continue

            if q:
                haystack = f"{t.title} {t.description} {t.project_title} {t.goal_title}".lower()
                if q not in haystack:
                    continue

            filtered.append(t)

        prio_rank = {"high": 1, "medium": 2, "low": 3}
        status_rank = {"in_progress": 1, "todo": 2, "completed": 3, "cancelled": 4}

        if sort_by == "priority":
            filtered.sort(
                key=lambda x: (
                    prio_rank.get(x.priority, 2),
                    x.due_date or "9999-12-31",
                    x.title.lower(),
                )
            )
        elif sort_by == "estimated_minutes":
            filtered.sort(
                key=lambda x: (
                    -(x.estimated_minutes or 0),
                    prio_rank.get(x.priority, 2),
                )
            )
        elif sort_by == "status":
            filtered.sort(
                key=lambda x: (
                    status_rank.get(x.status, 2),
                    x.due_date or "9999-12-31",
                )
            )
        elif sort_by == "created_at":
            filtered.sort(key=lambda x: x.created_at or "", reverse=True)
        else:  # due_date default
            filtered.sort(
                key=lambda x: (
                    1 if x.status in ("completed", "cancelled") else 0,
                    x.due_date or "9999-12-31",
                    prio_rank.get(x.priority, 2),
                )
            )

        return filtered
