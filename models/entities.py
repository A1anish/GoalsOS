"""Core domain models for GoalOS."""

from dataclasses import dataclass, field
from typing import List, Optional


GOAL_CATEGORIES = [
    "Education",
    "Career",
    "Personal Development",
    "Health and Wellness",
    "Projects",
    "Finance",
    "Other",
]

GOAL_STATUSES = ["active", "paused", "completed", "archived"]
MILESTONE_STATUSES = ["active", "completed", "archived"]
PROJECT_STATUSES = ["active", "completed", "archived"]
TASK_STATUSES = ["todo", "in_progress", "completed", "cancelled"]
PRIORITIES = ["low", "medium", "high"]

GOAL_ACCENT_COLORS = [
    "#6366F1",  # Indigo
    "#8B5CF6",  # Violet
    "#EC4899",  # Pink
    "#10B981",  # Emerald
    "#3B82F6",  # Blue
    "#F59E0B",  # Amber
    "#14B8A6",  # Teal
    "#EF4444",  # Rose/Red
]


@dataclass
class ProgressStats:
    """Represents calculated progress for a Goal, Milestone, or Project."""

    entity_id: str
    entity_type: str
    completed_tasks: int = 0
    total_eligible_tasks: int = 0
    cancelled_tasks: int = 0
    completed_minutes: int = 0
    total_eligible_minutes: int = 0
    effort_weighted: bool = False

    @property
    def has_eligible_tasks(self) -> bool:
        return self.total_eligible_tasks > 0

    @property
    def percentage(self) -> float:
        if not self.has_eligible_tasks:
            return 0.0
        if self.effort_weighted and self.total_eligible_minutes > 0:
            return round(
                (self.completed_minutes / self.total_eligible_minutes) * 100.0, 1
            )
        return round(
            (self.completed_tasks / self.total_eligible_tasks) * 100.0, 1
        )

    @property
    def status_label(self) -> str:
        if self.total_eligible_tasks == 0:
            if self.cancelled_tasks > 0:
                return f"All {self.cancelled_tasks} task(s) cancelled"
            return "No tasks yet"
        return f"{self.completed_tasks}/{self.total_eligible_tasks} tasks ({self.percentage:.0f}%)"


@dataclass
class Goal:
    """Represents a high-level long-term outcome."""

    id: str
    title: str
    description: str = ""
    category: str = "Other"
    start_date: Optional[str] = None
    deadline: Optional[str] = None
    priority: str = "medium"
    status: str = "active"
    target_value: Optional[float] = None
    target_unit: str = ""
    color: str = "#6366F1"
    completion_notes: str = ""
    created_at: str = ""
    updated_at: str = ""
    completed_at: Optional[str] = None


@dataclass
class Milestone:
    """Represents a significant intermediate outcome under a Goal."""

    id: str
    goal_id: str
    title: str
    description: str = ""
    start_date: Optional[str] = None
    deadline: Optional[str] = None
    status: str = "active"
    position: int = 0
    completion_notes: str = ""
    created_at: str = ""
    updated_at: str = ""
    completed_at: Optional[str] = None


@dataclass
class Project:
    """Represents a cohesive body of work under a Milestone."""

    id: str
    milestone_id: str
    title: str
    description: str = ""
    start_date: Optional[str] = None
    deadline: Optional[str] = None
    priority: str = "medium"
    status: str = "active"
    position: int = 0
    created_at: str = ""
    updated_at: str = ""
    completed_at: Optional[str] = None


@dataclass
class Task:
    """Represents an actionable unit of work under a Project."""

    id: str
    project_id: str
    title: str
    description: str = ""
    due_date: Optional[str] = None
    scheduled_date: Optional[str] = None
    estimated_minutes: int = 30
    actual_minutes: int = 0
    priority: str = "medium"
    status: str = "todo"
    position: int = 0
    created_at: str = ""
    updated_at: str = ""
    completed_at: Optional[str] = None

    # Enriched hierarchy fields for UI convenience (populated by joins/services)
    project_title: str = ""
    milestone_id: str = ""
    milestone_title: str = ""
    goal_id: str = ""
    goal_title: str = ""
    goal_color: str = "#6366F1"
    goal_status: str = "active"
    goal_priority: str = "medium"


@dataclass
class WeeklyReview:
    """Represents a structured weekly review and planning session."""

    id: str
    period_start: str
    period_end: str
    went_well: str = ""
    challenges: str = ""
    lessons_learned: str = ""
    next_week_changes: str = ""
    planned_priorities: str = ""
    selected_goal_ids: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


@dataclass
class ActivityEvent:
    """Represents a user action recorded in the activity log."""

    id: str
    entity_type: str
    entity_id: str
    action: str
    description: str
    created_at: str


@dataclass
class Recommendation:
    """Represents a Next Best Action task suggestion with scoring breakdown."""

    task: Task
    total_score: float
    deadline_score: float
    priority_score: float
    goal_score: float
    readiness_score: float
    explanation: str
    factors: List[str] = field(default_factory=list)
