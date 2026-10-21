"""Goal, Milestone, and Project business logic service for GoalOS."""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
import uuid

from models.entities import Goal, Milestone, ProgressStats, Project
from repositories.activity_repository import ActivityRepository
from repositories.goal_repository import GoalRepository
from repositories.milestone_repository import MilestoneRepository
from repositories.project_repository import ProjectRepository
from repositories.task_repository import TaskRepository
from services.progress_service import ProgressService
from utils.dates import now_iso, today_iso
from utils.validators import (
    ValidationError,
    validate_date_range,
    validate_goal_status,
    validate_milestone_status,
    validate_non_empty,
    validate_optional_float,
    validate_priority,
    validate_project_status,
)


class GoalService:
    """Manages Goals, Milestones, and Projects with validation and progress rules."""

    def __init__(
        self,
        goal_repo: GoalRepository,
        milestone_repo: MilestoneRepository,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        activity_repo: ActivityRepository,
        progress_service: ProgressService,
    ) -> None:
        self.goal_repo = goal_repo
        self.milestone_repo = milestone_repo
        self.project_repo = project_repo
        self.task_repo = task_repo
        self.activity_repo = activity_repo
        self.progress_service = progress_service

    # --- Goal CRUD & Status ---

    def create_goal(
        self,
        title: str,
        description: str = "",
        category: str = "Other",
        start_date: Optional[str] = None,
        deadline: Optional[str] = None,
        priority: str = "medium",
        target_value: Optional[object] = None,
        target_unit: str = "",
        color: str = "#6366F1",
    ) -> Goal:
        clean_title = validate_non_empty(title, "Goal title")
        clean_cat = validate_non_empty(category or "Other", "Category")
        clean_prio = validate_priority(priority)
        start_iso, deadline_iso = validate_date_range(
            start_date or today_iso(), deadline, "Start date", "Deadline"
        )
        clean_target = validate_optional_float(target_value, "Target value")

        ts = now_iso()
        goal = Goal(
            id=str(uuid.uuid4()),
            title=clean_title,
            description=(description or "").strip(),
            category=clean_cat,
            start_date=start_iso,
            deadline=deadline_iso,
            priority=clean_prio,
            status="active",
            target_value=clean_target,
            target_unit=(target_unit or "").strip(),
            color=(color or "#6366F1").strip(),
            created_at=ts,
            updated_at=ts,
        )
        self.goal_repo.create(goal)
        self.activity_repo.log(
            "goal", goal.id, "created", f"Created goal '{goal.title}'"
        )
        return goal

    def update_goal(
        self,
        goal_id: str,
        title: str,
        description: str = "",
        category: str = "Other",
        start_date: Optional[str] = None,
        deadline: Optional[str] = None,
        priority: str = "medium",
        status: Optional[str] = None,
        target_value: Optional[object] = None,
        target_unit: str = "",
        color: Optional[str] = None,
        completion_notes: Optional[str] = None,
        allow_incomplete_override: bool = False,
    ) -> Goal:
        existing = self.goal_repo.get_by_id(goal_id)
        if not existing:
            raise ValidationError("Goal not found.")

        clean_title = validate_non_empty(title, "Goal title")
        clean_cat = validate_non_empty(category or "Other", "Category")
        clean_prio = validate_priority(priority)
        start_iso, deadline_iso = validate_date_range(
            start_date, deadline, "Start date", "Deadline"
        )
        clean_target = validate_optional_float(target_value, "Target value")
        new_status = (
            validate_goal_status(status) if status else existing.status
        )

        # Business rule: completing a goal with unfinished tasks requires explicit override
        if new_status == "completed" and existing.status != "completed":
            stats = self.progress_service.get_goal_progress(goal_id)
            if (
                stats.has_eligible_tasks
                and stats.completed_tasks < stats.total_eligible_tasks
                and not allow_incomplete_override
            ):
                remaining = stats.total_eligible_tasks - stats.completed_tasks
                raise ValidationError(
                    f"Cannot mark goal completed while {remaining} eligible task(s) remain unfinished without explicit confirmation."
                )

        ts = now_iso()
        old_deadline = existing.deadline
        old_status = existing.status

        existing.title = clean_title
        existing.description = (description or "").strip()
        existing.category = clean_cat
        existing.start_date = start_iso
        existing.deadline = deadline_iso
        existing.priority = clean_prio
        existing.status = new_status
        existing.target_value = clean_target
        existing.target_unit = (target_unit or "").strip()
        if color:
            existing.color = color.strip()
        if completion_notes is not None:
            existing.completion_notes = completion_notes.strip()
        existing.updated_at = ts

        if new_status == "completed" and old_status != "completed":
            existing.completed_at = ts
        elif new_status != "completed":
            existing.completed_at = None

        self.goal_repo.update(existing)

        if old_status != new_status:
            self.activity_repo.log(
                "goal",
                goal_id,
                f"status_{new_status}",
                f"Goal '{existing.title}' marked as {new_status}",
            )
        elif old_deadline != deadline_iso:
            self.activity_repo.log(
                "goal",
                goal_id,
                "deadline_changed",
                f"Updated deadline for '{existing.title}' to {deadline_iso or 'None'}",
            )
        else:
            self.activity_repo.log(
                "goal",
                goal_id,
                "updated",
                f"Updated goal '{existing.title}'",
            )
        return existing

    def change_goal_status(
        self,
        goal_id: str,
        new_status: str,
        allow_incomplete_override: bool = False,
    ) -> Goal:
        goal = self.goal_repo.get_by_id(goal_id)
        if not goal:
            raise ValidationError("Goal not found.")
        return self.update_goal(
            goal_id=goal.id,
            title=goal.title,
            description=goal.description,
            category=goal.category,
            start_date=goal.start_date,
            deadline=goal.deadline,
            priority=goal.priority,
            status=new_status,
            target_value=goal.target_value,
            target_unit=goal.target_unit,
            color=goal.color,
            completion_notes=goal.completion_notes,
            allow_incomplete_override=allow_incomplete_override,
        )

    def delete_goal(self, goal_id: str) -> None:
        goal = self.goal_repo.get_by_id(goal_id)
        if not goal:
            return
        self.goal_repo.delete(goal_id)
        self.activity_repo.log(
            "goal", goal_id, "deleted", f"Deleted goal '{goal.title}'"
        )

    # --- Milestone CRUD ---

    def create_milestone(
        self,
        goal_id: str,
        title: str,
        description: str = "",
        start_date: Optional[str] = None,
        deadline: Optional[str] = None,
    ) -> Milestone:
        parent_goal = self.goal_repo.get_by_id(goal_id)
        if not parent_goal:
            raise ValidationError("Parent goal does not exist.")
        clean_title = validate_non_empty(title, "Milestone title")
        start_iso, deadline_iso = validate_date_range(
            start_date, deadline, "Start date", "Deadline"
        )
        pos = self.milestone_repo.get_next_position(goal_id)
        ts = now_iso()

        milestone = Milestone(
            id=str(uuid.uuid4()),
            goal_id=goal_id,
            title=clean_title,
            description=(description or "").strip(),
            start_date=start_iso,
            deadline=deadline_iso,
            status="active",
            position=pos,
            created_at=ts,
            updated_at=ts,
        )
        self.milestone_repo.create(milestone)
        self.activity_repo.log(
            "milestone",
            milestone.id,
            "created",
            f"Added milestone '{milestone.title}' to '{parent_goal.title}'",
        )
        return milestone

    def update_milestone(
        self,
        milestone_id: str,
        title: str,
        description: str = "",
        start_date: Optional[str] = None,
        deadline: Optional[str] = None,
        status: Optional[str] = None,
        position: Optional[int] = None,
    ) -> Milestone:
        existing = self.milestone_repo.get_by_id(milestone_id)
        if not existing:
            raise ValidationError("Milestone not found.")
        clean_title = validate_non_empty(title, "Milestone title")
        start_iso, deadline_iso = validate_date_range(
            start_date, deadline, "Start date", "Deadline"
        )
        new_status = (
            validate_milestone_status(status) if status else existing.status
        )
        ts = now_iso()
        old_status = existing.status

        existing.title = clean_title
        existing.description = (description or "").strip()
        existing.start_date = start_iso
        existing.deadline = deadline_iso
        existing.status = new_status
        if position is not None:
            existing.position = int(position)
        existing.updated_at = ts
        if new_status == "completed" and old_status != "completed":
            existing.completed_at = ts
        elif new_status != "completed":
            existing.completed_at = None

        self.milestone_repo.update(existing)
        if old_status != new_status and new_status == "completed":
            self.activity_repo.log(
                "milestone",
                existing.id,
                "completed",
                f"Completed milestone '{existing.title}'",
            )
        return existing

    def reorder_milestone(self, milestone_id: str, direction: int) -> None:
        """Moves a milestone up (-1) or down (+1) among its siblings."""
        m = self.milestone_repo.get_by_id(milestone_id)
        if not m:
            return
        siblings = self.milestone_repo.list_by_goal(m.goal_id)
        idx = next((i for i, s in enumerate(siblings) if s.id == m.id), -1)
        target_idx = idx + direction
        if idx < 0 or target_idx < 0 or target_idx >= len(siblings):
            return
        siblings[idx], siblings[target_idx] = siblings[target_idx], siblings[idx]
        for pos, item in enumerate(siblings):
            item.position = pos
            self.milestone_repo.update(item)

    def delete_milestone(self, milestone_id: str) -> None:
        m = self.milestone_repo.get_by_id(milestone_id)
        if not m:
            return
        self.milestone_repo.delete(milestone_id)
        self.activity_repo.log(
            "milestone", milestone_id, "deleted", f"Deleted milestone '{m.title}'"
        )

    # --- Project CRUD ---

    def create_project(
        self,
        milestone_id: str,
        title: str,
        description: str = "",
        start_date: Optional[str] = None,
        deadline: Optional[str] = None,
        priority: str = "medium",
    ) -> Project:
        parent_m = self.milestone_repo.get_by_id(milestone_id)
        if not parent_m:
            raise ValidationError("Parent milestone does not exist.")
        clean_title = validate_non_empty(title, "Project title")
        clean_prio = validate_priority(priority)
        start_iso, deadline_iso = validate_date_range(
            start_date, deadline, "Start date", "Deadline"
        )
        pos = self.project_repo.get_next_position(milestone_id)
        ts = now_iso()

        project = Project(
            id=str(uuid.uuid4()),
            milestone_id=milestone_id,
            title=clean_title,
            description=(description or "").strip(),
            start_date=start_iso,
            deadline=deadline_iso,
            priority=clean_prio,
            status="active",
            position=pos,
            created_at=ts,
            updated_at=ts,
        )
        self.project_repo.create(project)
        self.activity_repo.log(
            "project",
            project.id,
            "created",
            f"Created project '{project.title}' under '{parent_m.title}'",
        )
        return project

    def update_project(
        self,
        project_id: str,
        title: str,
        description: str = "",
        start_date: Optional[str] = None,
        deadline: Optional[str] = None,
        priority: str = "medium",
        status: Optional[str] = None,
        milestone_id: Optional[str] = None,
        position: Optional[int] = None,
    ) -> Project:
        existing = self.project_repo.get_by_id(project_id)
        if not existing:
            raise ValidationError("Project not found.")
        if milestone_id and milestone_id != existing.milestone_id:
            if not self.milestone_repo.get_by_id(milestone_id):
                raise ValidationError("Target milestone does not exist.")
            existing.milestone_id = milestone_id

        clean_title = validate_non_empty(title, "Project title")
        clean_prio = validate_priority(priority)
        start_iso, deadline_iso = validate_date_range(
            start_date, deadline, "Start date", "Deadline"
        )
        new_status = (
            validate_project_status(status) if status else existing.status
        )
        ts = now_iso()

        existing.title = clean_title
        existing.description = (description or "").strip()
        existing.start_date = start_iso
        existing.deadline = deadline_iso
        existing.priority = clean_prio
        existing.status = new_status
        if position is not None:
            existing.position = int(position)
        existing.updated_at = ts
        if new_status == "completed" and not existing.completed_at:
            existing.completed_at = ts
        elif new_status != "completed":
            existing.completed_at = None

        self.project_repo.update(existing)
        return existing

    def reorder_project(self, project_id: str, direction: int) -> None:
        p = self.project_repo.get_by_id(project_id)
        if not p:
            return
        siblings = self.project_repo.list_by_milestone(p.milestone_id)
        idx = next((i for i, s in enumerate(siblings) if s.id == p.id), -1)
        target_idx = idx + direction
        if idx < 0 or target_idx < 0 or target_idx >= len(siblings):
            return
        siblings[idx], siblings[target_idx] = siblings[target_idx], siblings[idx]
        for pos, item in enumerate(siblings):
            item.position = pos
            self.project_repo.update(item)

    def delete_project(self, project_id: str) -> None:
        p = self.project_repo.get_by_id(project_id)
        if not p:
            return
        self.project_repo.delete(project_id)
        self.activity_repo.log(
            "project", project_id, "deleted", f"Deleted project '{p.title}'"
        )

    # --- Hierarchy Tree Snapshot ---

    def get_full_hierarchy(self, goal_id: str) -> Optional[Dict]:
        """Returns a complete nested tree structure for a goal with progress stats."""
        goal = self.goal_repo.get_by_id(goal_id)
        if not goal:
            return None
        milestones = self.milestone_repo.list_by_goal(goal_id)
        projects = self.project_repo.list_by_goal(goal_id)
        tasks = self.task_repo.list_by_goal(goal_id)
        prog_map = self.progress_service.get_goal_hierarchy_progress_map(goal_id)
        weighted = self.progress_service.is_effort_weighted()

        projects_by_milestone: Dict[str, List[Project]] = {}
        for p in projects:
            projects_by_milestone.setdefault(p.milestone_id, []).append(p)

        tasks_by_project: Dict[str, list] = {}
        for t in tasks:
            tasks_by_project.setdefault(t.project_id, []).append(t)

        milestone_nodes = []
        for m in milestones:
            m_stats = prog_map.get(
                m.id,
                ProgressStats(m.id, "milestone", effort_weighted=weighted),
            )
            project_nodes = []
            for p in projects_by_milestone.get(m.id, []):
                p_stats = prog_map.get(
                    p.id,
                    ProgressStats(p.id, "project", effort_weighted=weighted),
                )
                project_nodes.append(
                    {
                        "project": p,
                        "progress": p_stats,
                        "tasks": tasks_by_project.get(p.id, []),
                    }
                )
            milestone_nodes.append(
                {
                    "milestone": m,
                    "progress": m_stats,
                    "projects": project_nodes,
                }
            )

        return {
            "goal": goal,
            "progress": prog_map.get(
                goal.id,
                ProgressStats(goal.id, "goal", effort_weighted=weighted),
            ),
            "milestones": milestone_nodes,
        }

    def list_all_projects_with_context(self) -> List[Tuple[str, str]]:
        """Returns list of (project_id, 'Goal -> Milestone -> Project') for dropdowns."""
        goals = {g.id: g for g in self.goal_repo.list_all()}
        milestones = {m.id: m for m in self.milestone_repo.list_all()}
        projects = self.project_repo.list_all()
        result: List[Tuple[str, str]] = []
        for p in projects:
            m = milestones.get(p.milestone_id)
            if not m:
                continue
            g = goals.get(m.goal_id)
            if not g or g.status == "archived":
                continue
            label = f"{g.title}  ›  {m.title}  ›  {p.title}"
            result.append((p.id, label))
        return result
