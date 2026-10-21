"""Analytics, dashboard aggregation, timeline, and feasibility service for GoalOS."""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from models.entities import Goal, Milestone, Task
from repositories.activity_repository import SettingsRepository
from repositories.goal_repository import GoalRepository
from repositories.milestone_repository import MilestoneRepository
from repositories.project_repository import ProjectRepository
from repositories.task_repository import TaskRepository
from services.progress_service import ProgressService
from utils.dates import classify_deadline, days_until, parse_iso_date


class AnalyticsService:
    """Computes real-time dashboard metrics, timelines, charts, and schedule feasibility."""

    def __init__(
        self,
        goal_repo: GoalRepository,
        milestone_repo: MilestoneRepository,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        settings_repo: SettingsRepository,
        progress_service: ProgressService,
    ) -> None:
        self.goal_repo = goal_repo
        self.milestone_repo = milestone_repo
        self.project_repo = project_repo
        self.task_repo = task_repo
        self.settings_repo = settings_repo
        self.progress_service = progress_service

    def get_dashboard_summary(self, ref_date: Optional[date] = None) -> Dict:
        """Calculates the 5 primary dashboard summary metrics and week-over-week comparisons."""
        ref = ref_date or date.today()
        all_goals = self.goal_repo.list_all()
        active_goals = [g for g in all_goals if g.status == "active"]
        completed_goals = [g for g in all_goals if g.status == "completed"]

        all_tasks = self.task_repo.list_all(include_archived_goals=False)

        this_week_start = ref - timedelta(days=ref.weekday())
        last_week_start = this_week_start - timedelta(days=7)
        last_week_end = this_week_start - timedelta(days=1)

        completed_this_week = 0
        completed_last_week = 0
        due_today_count = 0
        overdue_count = 0
        due_today_minutes = 0

        for t in all_tasks:
            if t.status == "completed" and t.completed_at:
                c_date = parse_iso_date(t.completed_at)
                if c_date:
                    if this_week_start <= c_date <= ref + timedelta(days=6):
                        completed_this_week += 1
                    elif last_week_start <= c_date <= last_week_end:
                        completed_last_week += 1

            # Exclude paused goals from active workload warnings by default
            if t.goal_status != "active":
                continue
            if t.status in ("completed", "cancelled"):
                continue

            due_diff = days_until(t.due_date, reference_date=ref)
            sched_diff = days_until(t.scheduled_date, reference_date=ref)

            if due_diff is not None and due_diff < 0:
                overdue_count += 1
            if due_diff == 0 or sched_diff == 0:
                due_today_count += 1
                due_today_minutes += t.estimated_minutes or 30

        overall_progress = self.progress_service.get_all_active_goals_progress()
        week_delta = completed_this_week - completed_last_week

        return {
            "active_goals_count": len(active_goals),
            "completed_goals_count": len(completed_goals),
            "completed_this_week": completed_this_week,
            "completed_last_week": completed_last_week,
            "week_delta": week_delta,
            "due_today_count": due_today_count,
            "due_today_minutes": due_today_minutes,
            "overdue_count": overdue_count,
            "overall_progress": overall_progress,
        }

    def get_todays_priorities(self, ref_date: Optional[date] = None) -> List[Task]:
        """Returns tasks scheduled for today, due today, or overdue under active goals."""
        ref = ref_date or date.today()
        all_tasks = self.task_repo.list_all(include_archived_goals=False)
        priorities: List[Task] = []

        for t in all_tasks:
            if t.goal_status != "active" or t.status == "cancelled":
                continue
            due_diff = days_until(t.due_date, reference_date=ref)
            sched_diff = days_until(t.scheduled_date, reference_date=ref)
            comp_date = parse_iso_date(t.completed_at) if t.completed_at else None

            is_due_or_overdue = (
                t.status != "completed"
                and due_diff is not None
                and due_diff <= 0
            )
            is_scheduled_today = (
                t.status != "completed"
                and sched_diff is not None
                and sched_diff <= 0
            )
            is_completed_today = t.status == "completed" and comp_date == ref

            if is_due_or_overdue or is_scheduled_today or is_completed_today:
                priorities.append(t)

        prio_map = {"high": 1, "medium": 2, "low": 3}
        priorities.sort(
            key=lambda x: (
                1 if x.status == "completed" else 0,
                days_until(x.due_date, reference_date=ref)
                if x.due_date
                else 999,
                prio_map.get(x.priority, 2),
            )
        )
        return priorities

    def get_upcoming_milestones(
        self, limit: int = 8, ref_date: Optional[date] = None
    ) -> List[Dict]:
        """Returns active milestones ordered by deadline with their goal and progress stats."""
        goals = {g.id: g for g in self.goal_repo.list_all() if g.status == "active"}
        milestones = self.milestone_repo.list_all()
        result: List[Dict] = []

        for m in milestones:
            goal = goals.get(m.goal_id)
            if not goal or m.status == "archived":
                continue
            stats = self.progress_service.get_milestone_progress(m.id)
            is_comp = m.status == "completed" or (
                stats.has_eligible_tasks
                and stats.completed_tasks == stats.total_eligible_tasks
            )
            if is_comp:
                continue
            result.append(
                {
                    "milestone": m,
                    "goal": goal,
                    "progress": stats,
                    "days_left": days_until(m.deadline, reference_date=ref_date),
                }
            )

        result.sort(
            key=lambda item: (
                item["milestone"].deadline or "9999-12-31",
                item["milestone"].position,
            )
        )
        return result[:limit]

    def get_timeline_buckets(self, ref_date: Optional[date] = None) -> Dict[str, List[Dict]]:
        """Groups active tasks and milestones into chronological buckets:
        'overdue', 'today', 'next_7_days', 'later', 'unscheduled'.
        """
        ref = ref_date or date.today()
        buckets: Dict[str, List[Dict]] = {
            "overdue": [],
            "today": [],
            "next_7_days": [],
            "later": [],
            "unscheduled": [],
        }

        goals = {g.id: g for g in self.goal_repo.list_all() if g.status == "active"}
        for m in self.milestone_repo.list_all():
            g = goals.get(m.goal_id)
            if not g or m.status in ("completed", "archived"):
                continue
            stats = self.progress_service.get_milestone_progress(m.id)
            is_comp = m.status == "completed"
            bucket = classify_deadline(m.deadline, is_completed=is_comp, reference_date=ref)
            if bucket in buckets:
                buckets[bucket].append(
                    {
                        "entity_type": "Milestone",
                        "id": m.id,
                        "title": m.title,
                        "goal_id": g.id,
                        "goal_title": g.title,
                        "goal_color": g.color,
                        "due_date": m.deadline,
                        "priority": g.priority,
                        "status": m.status,
                        "progress_pct": stats.percentage,
                        "raw": m,
                    }
                )

        for t in self.task_repo.list_all(include_archived_goals=False):
            if t.goal_status != "active" or t.status in ("completed", "cancelled"):
                continue
            effective_date = t.due_date or t.scheduled_date
            bucket = classify_deadline(effective_date, is_completed=False, reference_date=ref)
            if bucket in buckets:
                buckets[bucket].append(
                    {
                        "entity_type": "Task",
                        "id": t.id,
                        "title": t.title,
                        "goal_id": t.goal_id,
                        "goal_title": t.goal_title,
                        "goal_color": t.goal_color,
                        "due_date": effective_date,
                        "priority": t.priority,
                        "status": t.status,
                        "estimated_minutes": t.estimated_minutes,
                        "raw": t,
                    }
                )

        for key in buckets:
            buckets[key].sort(key=lambda x: x["due_date"] or "9999-12-31")

        return buckets

    def get_completion_history(
        self, days: int = 14, ref_date: Optional[date] = None
    ) -> List[Tuple[str, int, int]]:
        """Returns list of (YYYY-MM-DD, completed_task_count, completed_minutes)
        for each of the past `days` days ending on ref_date.
        """
        ref = ref_date or date.today()
        start_d = ref - timedelta(days=days - 1)
        counts: Dict[str, int] = {}
        minutes_map: Dict[str, int] = {}

        for i in range(days):
            d_iso = (start_d + timedelta(days=i)).isoformat()
            counts[d_iso] = 0
            minutes_map[d_iso] = 0

        for t in self.task_repo.list_all(include_archived_goals=True):
            if t.status == "completed" and t.completed_at:
                c_date = parse_iso_date(t.completed_at)
                if c_date:
                    c_iso = c_date.isoformat()
                    if c_iso in counts:
                        counts[c_iso] += 1
                        minutes_map[c_iso] += t.actual_minutes or t.estimated_minutes or 30

        return [(d_iso, counts[d_iso], minutes_map[d_iso]) for d_iso in sorted(counts.keys())]

    def get_category_distribution(self) -> List[Tuple[str, int]]:
        """Returns list of (category, count) for active and completed goals."""
        goals = [
            g for g in self.goal_repo.list_all() if g.status in ("active", "completed", "paused")
        ]
        dist: Dict[str, int] = {}
        for g in goals:
            cat = g.category or "Other"
            dist[cat] = dist.get(cat, 0) + 1
        return sorted(dist.items(), key=lambda x: (-x[1], x[0]))

    def get_deadline_performance(self, ref_date: Optional[date] = None) -> Dict[str, int]:
        """Calculates task deadline compliance across all non-cancelled tasks:
        - completed_on_time: completed on or before due_date (or completed without due_date)
        - completed_late: completed after due_date
        - currently_overdue: incomplete and past due_date (under active goals)
        - on_track: incomplete and due today or in the future
        """
        ref = ref_date or date.today()
        on_time = 0
        completed_late = 0
        currently_overdue = 0
        on_track = 0

        for t in self.task_repo.list_all(include_archived_goals=False):
            if t.status == "cancelled":
                continue
            due_d = parse_iso_date(t.due_date)
            if t.status == "completed":
                comp_d = parse_iso_date(t.completed_at)
                if due_d and comp_d and comp_d > due_d:
                    completed_late += 1
                else:
                    on_time += 1
            else:
                if t.goal_status != "active":
                    continue
                if due_d and due_d < ref:
                    currently_overdue += 1
                else:
                    on_track += 1

        return {
            "completed_on_time": on_time,
            "completed_late": completed_late,
            "currently_overdue": currently_overdue,
            "on_track": on_track,
        }

    def get_workload_distribution(
        self, days: int = 7, ref_date: Optional[date] = None
    ) -> Dict:
        """Calculates estimated workload in minutes for each of the next `days` days,
        plus overdue workload and unscheduled workload.
        """
        ref = ref_date or date.today()
        daily_mins: Dict[str, int] = {}
        for i in range(days):
            d_iso = (ref + timedelta(days=i)).isoformat()
            daily_mins[d_iso] = 0

        unscheduled_mins = 0
        overdue_mins = 0
        later_mins = 0

        for t in self.task_repo.list_all(include_archived_goals=False):
            if t.goal_status != "active" or t.status in ("completed", "cancelled"):
                continue
            est = t.estimated_minutes or 30
            target_iso = t.scheduled_date or t.due_date
            target_d = parse_iso_date(target_iso)
            if target_d is None:
                unscheduled_mins += est
            elif target_d < ref:
                overdue_mins += est
            elif target_d.isoformat() in daily_mins:
                daily_mins[target_d.isoformat()] += est
            else:
                later_mins += est

        return {
            "daily": [(k, daily_mins[k]) for k in sorted(daily_mins.keys())],
            "unscheduled_minutes": unscheduled_mins,
            "overdue_minutes": overdue_mins,
            "later_minutes": later_mins,
        }

    def analyze_goal_feasibility(
        self, goal: Goal, ref_date: Optional[date] = None
    ) -> Dict:
        """Evaluates whether remaining estimated task minutes for a goal can fit
        before its deadline based on daily capacity.
        """
        ref = ref_date or date.today()
        tasks = self.task_repo.list_by_goal(goal.id)
        remaining_mins = sum(
            (t.estimated_minutes or 30)
            for t in tasks
            if t.status not in ("completed", "cancelled")
        )
        remaining_tasks = sum(
            1 for t in tasks if t.status not in ("completed", "cancelled")
        )

        try:
            daily_cap = int(
                self.settings_repo.get("daily_capacity_minutes", "180")
            )
        except ValueError:
            daily_cap = 180
        daily_cap = max(daily_cap, 30)

        if remaining_tasks == 0:
            if not tasks:
                return {
                    "status": "unplanned",
                    "label": "No tasks planned yet",
                    "detail": "Break this goal into milestones, projects, and tasks to estimate schedule feasibility.",
                }
            return {
                "status": "completed",
                "label": "All planned tasks completed",
                "detail": "0m of remaining work.",
            }

        if not goal.deadline:
            days_needed = round(remaining_mins / daily_cap, 1)
            return {
                "status": "no_deadline",
                "label": f"~{days_needed} work days needed",
                "detail": f"{remaining_mins}m remaining across {remaining_tasks} task(s) at {daily_cap}m/day capacity.",
            }

        d_left = days_until(goal.deadline, reference_date=ref)
        if d_left is None or d_left < 0:
            return {
                "status": "overdue",
                "label": "Goal deadline passed",
                "detail": f"{remaining_mins}m ({remaining_tasks} tasks) still remaining past deadline ({goal.deadline}).",
            }

        available_days = max(d_left, 1)
        required_mins_per_day = round(remaining_mins / available_days)

        if required_mins_per_day <= daily_cap * 0.8:
            return {
                "status": "feasible",
                "label": "On Track & Feasible",
                "detail": f"Requires ~{required_mins_per_day}m/day over {available_days} day(s) (well within {daily_cap}m/day capacity).",
            }
        if required_mins_per_day <= daily_cap:
            return {
                "status": "tight",
                "label": "Tight Schedule",
                "detail": f"Requires ~{required_mins_per_day}m/day over {available_days} day(s) (near {daily_cap}m/day capacity).",
            }
        return {
            "status": "at_risk",
            "label": "At Risk — Overload",
            "detail": f"Requires ~{required_mins_per_day}m/day over {available_days} day(s), exceeding {daily_cap}m/day capacity.",
        }
