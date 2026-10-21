"""Backup, restore, JSON export, and sample seed data service for GoalOS."""

from dataclasses import asdict
from datetime import date, timedelta
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Dict

from database.connection import DatabaseManager
from repositories.activity_repository import ActivityRepository, SettingsRepository
from repositories.goal_repository import GoalRepository
from repositories.milestone_repository import MilestoneRepository
from repositories.project_repository import ProjectRepository
from repositories.review_repository import ReviewRepository
from repositories.task_repository import TaskRepository
from services.goal_service import GoalService
from services.review_service import ReviewService
from services.task_service import TaskService
from utils.validators import ValidationError


class BackupService:
    """Handles database backup, validated restore, JSON export, and sample data seeding."""

    def __init__(
        self,
        db: DatabaseManager,
        goal_repo: GoalRepository,
        milestone_repo: MilestoneRepository,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        review_repo: ReviewRepository,
        activity_repo: ActivityRepository,
        settings_repo: SettingsRepository,
        goal_service: GoalService,
        task_service: TaskService,
        review_service: ReviewService,
    ) -> None:
        self.db = db
        self.goal_repo = goal_repo
        self.milestone_repo = milestone_repo
        self.project_repo = project_repo
        self.task_repo = task_repo
        self.review_repo = review_repo
        self.activity_repo = activity_repo
        self.settings_repo = settings_repo
        self.goal_service = goal_service
        self.task_service = task_service
        self.review_service = review_service

    def export_to_json(self, target_path: str) -> str:
        """Exports all goals, milestones, projects, tasks, reviews, and settings to JSON."""
        payload: Dict = {
            "application": "GoalOS",
            "version": "1.0",
            "exported_at": date.today().isoformat(),
            "settings": self.settings_repo.get_all(),
            "goals": [asdict(g) for g in self.goal_repo.list_all()],
            "milestones": [asdict(m) for m in self.milestone_repo.list_all()],
            "projects": [asdict(p) for p in self.project_repo.list_all()],
            "tasks": [asdict(t) for t in self.task_repo.list_all(include_archived_goals=True)],
            "weekly_reviews": [asdict(r) for r in self.review_repo.list_all()],
            "recent_activity": [asdict(a) for a in self.activity_repo.list_recent(limit=100)],
        }
        out = Path(target_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.activity_repo.log(
            "system", "export", "exported_json", f"Exported data to {out.name}"
        )
        return str(out)

    def create_backup(self, backup_path: str) -> str:
        """Creates a consistent SQLite backup using file copy from active database."""
        if self.db.db_path == ":memory:":
            raise ValidationError("Cannot backup an in-memory database to file.")
        dest = Path(backup_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.db._active_db_path, str(dest))
        self.activity_repo.log(
            "system", "backup", "created_backup", f"Created SQLite backup {dest.name}"
        )
        return str(dest)

    def restore_backup(self, backup_path: str) -> None:
        """Validates a backup file before safely replacing the active database."""
        if not DatabaseManager.validate_sqlite_file(backup_path):
            raise ValidationError(
                "Selected file is not a valid or intact GoalOS SQLite database backup."
            )
        if self.db.db_path == ":memory:":
            raise ValidationError("Cannot restore file into an in-memory database.")
        shutil.copy2(backup_path, self.db._active_db_path)
        self.db._sync_to_target()
        self.db.initialize_database()
        self.activity_repo.log(
            "system",
            "restore",
            "restored_backup",
            f"Restored database from {Path(backup_path).name}",
        )

    def seed_sample_data_if_empty(self, force: bool = False) -> bool:
        """Populates realistic sample goals, milestones, projects, tasks, and reviews."""
        existing_goals = self.goal_repo.list_all()
        if existing_goals and not force:
            return False

        today = date.today()
        d = lambda offset: (today + timedelta(days=offset)).isoformat()
        ts = lambda offset: f"{d(offset)}T14:30:00"

        # Goal 1: Master Python & Software Engineering Portfolio
        g1 = self.goal_service.create_goal(
            title="Build a Full-Stack & Desktop Python Portfolio",
            description="Design, architect, and ship three production-grade Python applications with automated tests and clean documentation.",
            category="Career",
            start_date=d(-25),
            deadline=d(35),
            priority="high",
            target_value=3,
            target_unit="projects",
            color="#6366F1",
        )
        m1_1 = self.goal_service.create_milestone(
            goal_id=g1.id,
            title="Phase 1: Core Architecture & Database Layer",
            description="Establish clean layered architecture, SQLite schema, and unit test suite.",
            start_date=d(-25),
            deadline=d(-5),
        )
        p1_1 = self.goal_service.create_project(
            milestone_id=m1_1.id,
            title="Implement SQLite Persistence & Repositories",
            description="Create normalized tables, foreign keys, and CRUD repositories.",
            start_date=d(-25),
            deadline=d(-7),
            priority="high",
        )
        t1 = self.task_service.create_task(
            p1_1.id, "Design normalized SQLite schema with foreign keys", due_date=d(-14), scheduled_date=d(-15), estimated_minutes=60, priority="high"
        )
        self.task_service.complete_task(t1.id, completed_at=ts(-14))

        t2 = self.task_service.create_task(
            p1_1.id, "Implement Goal, Milestone, Project, and Task repositories", due_date=d(-8), scheduled_date=d(-9), estimated_minutes=90, priority="high"
        )
        self.task_service.complete_task(t2.id, completed_at=ts(-8))

        t3 = self.task_service.create_task(
            p1_1.id, "Write unit tests for progress and recommendation engines", due_date=d(-4), scheduled_date=d(-5), estimated_minutes=45, priority="medium"
        )
        self.task_service.complete_task(t3.id, completed_at=ts(-4))

        m1_2 = self.goal_service.create_milestone(
            goal_id=g1.id,
            title="Phase 2: Interactive Tkinter Frontend & Canvas Visualizers",
            description="Build custom Canvas charts, hierarchical node tree, and responsive dark/light themes.",
            start_date=d(-5),
            deadline=d(12),
        )
        p1_2 = self.goal_service.create_project(
            milestone_id=m1_2.id,
            title="Develop GoalOS Desktop Interface",
            description="Implement Dashboard, Goal Explorer Canvas, Task Planner, and Analytics.",
            start_date=d(-5),
            deadline=d(10),
            priority="high",
        )
        t4 = self.task_service.create_task(
            p1_2.id, "Build custom Canvas progress rings and interactive goal cards", due_date=d(-2), scheduled_date=d(-2), estimated_minutes=60, priority="high"
        )
        self.task_service.complete_task(t4.id, completed_at=ts(-2))

        t5 = self.task_service.create_task(
            p1_2.id, "Implement interactive zoom/pan Goal Explorer node graph", due_date=d(0), scheduled_date=d(0), estimated_minutes=75, priority="high"
        )
        self.task_service.update_task(
            t5.id, t5.title, t5.description, due_date=t5.due_date, scheduled_date=t5.scheduled_date, estimated_minutes=75, priority="high", status="in_progress"
        )

        self.task_service.create_task(
            p1_2.id, "Add Gantt timeline canvas and deadline performance charts", due_date=d(2), scheduled_date=d(1), estimated_minutes=60, priority="medium"
        )
        self.task_service.create_task(
            p1_2.id, "Polish dark/light theme switcher and keyboard shortcuts", due_date=d(5), scheduled_date=d(4), estimated_minutes=45, priority="low"
        )

        m1_3 = self.goal_service.create_milestone(
            goal_id=g1.id,
            title="Phase 3: Documentation & Portfolio Showcase",
            description="Record walkthrough demo and publish comprehensive technical README.",
            start_date=d(13),
            deadline=d(35),
        )
        p1_3 = self.goal_service.create_project(
            milestone_id=m1_3.id,
            title="Prepare Final Release Package",
            description="Package installation guide, screenshots, and architecture notes.",
            start_date=d(13),
            deadline=d(30),
            priority="medium",
        )
        self.task_service.create_task(
            p1_3.id, "Write architecture documentation and user guide", due_date=d(18), scheduled_date=d(15), estimated_minutes=60, priority="medium"
        )

        # Goal 2: Academic / Algorithms Mastery
        g2 = self.goal_service.create_goal(
            title="Complete Advanced Algorithms & Data Structures Prep",
            description="Master graph algorithms, dynamic programming, and system design fundamentals before finals.",
            category="Education",
            start_date=d(-15),
            deadline=d(21),
            priority="high",
            target_value=50,
            target_unit="problems",
            color="#10B981",
        )
        m2_1 = self.goal_service.create_milestone(
            goal_id=g2.id,
            title="Graph Theory & Shortest Path Mastery",
            description="Cover BFS, DFS, Dijkstra, A*, and Topological Sort.",
            start_date=d(-15),
            deadline=d(4),
        )
        p2_1 = self.goal_service.create_project(
            milestone_id=m2_1.id,
            title="Graph Problem Set & Implementations",
            description="Solve 15 core graph traversal and shortest-path problems.",
            start_date=d(-15),
            deadline=d(4),
            priority="high",
        )
        t2_1 = self.task_service.create_task(
            p2_1.id, "Implement Dijkstra and A* priority queue templates", due_date=d(-5), scheduled_date=d(-5), estimated_minutes=50, priority="high"
        )
        self.task_service.complete_task(t2_1.id, completed_at=ts(-3))  # Completed 2 days late!

        self.task_service.create_task(
            p2_1.id, "Solve 5 topological sort & cycle detection problems", due_date=d(-1), scheduled_date=d(-1), estimated_minutes=45, priority="high"
        )  # Overdue by 1 day!

        self.task_service.create_task(
            p2_1.id, "Review Minimum Spanning Tree (Kruskal & Prim)", due_date=d(3), scheduled_date=d(2), estimated_minutes=40, priority="medium"
        )

        m2_2 = self.goal_service.create_milestone(
            goal_id=g2.id,
            title="Dynamic Programming Patterns",
            description="Knapsack, LCS, interval DP, and state compression.",
            start_date=d(5),
            deadline=d(21),
        )
        p2_2 = self.goal_service.create_project(
            milestone_id=m2_2.id,
            title="DP Pattern Drills",
            description="Practice memoization and bottom-up tabulation.",
            start_date=d(5),
            deadline=d(20),
            priority="medium",
        )
        self.task_service.create_task(
            p2_2.id, "Complete 1D and 2D grid DP exercises", due_date=d(9), scheduled_date=d(6), estimated_minutes=60, priority="medium"
        )

        # Goal 3: Health & Endurance Routine
        g3 = self.goal_service.create_goal(
            title="10K Endurance & Mobility Conditioning",
            description="Build sustainable aerobic base, strength routine, and consistent sleep schedule.",
            category="Health and Wellness",
            start_date=d(-10),
            deadline=d(45),
            priority="medium",
            target_value=10,
            target_unit="km",
            color="#F59E0B",
        )
        m3_1 = self.goal_service.create_milestone(
            goal_id=g3.id,
            title="Base Mileage & Mobility Foundation",
            description="Complete 3 weekly runs and daily 15-minute mobility sessions.",
            start_date=d(-10),
            deadline=d(14),
        )
        p3_1 = self.goal_service.create_project(
            milestone_id=m3_1.id,
            title="Weekly Conditioning Block",
            description="Structured aerobic runs + core stability.",
            start_date=d(-10),
            deadline=d(14),
            priority="medium",
        )
        t3_1 = self.task_service.create_task(
            p3_1.id, "Complete 5K tempo run and log splits", due_date=d(-1), scheduled_date=d(-1), estimated_minutes=35, priority="medium"
        )
        self.task_service.complete_task(t3_1.id, completed_at=ts(-1))

        self.task_service.create_task(
            p3_1.id, "20-minute full-body mobility & hip opener routine", due_date=d(0), scheduled_date=d(0), estimated_minutes=20, priority="medium"
        )
        self.task_service.create_task(
            p3_1.id, "Weekend 7K long slow distance run", due_date=d(4), scheduled_date=d(3), estimated_minutes=50, priority="low"
        )

        # Sample Weekly Review
        self.review_service.save_weekly_review(
            period_start=d(-7),
            period_end=d(0),
            went_well="Completed the entire SQLite persistence layer and core progress calculation engine ahead of schedule.",
            challenges="Underestimated the time needed for graph algorithm practice problems, causing one task to slip by a day.",
            lessons_learned="Breaking projects into 30–60 minute tasks makes daily execution much smoother.",
            next_week_changes="Time-block 45 minutes every morning for high-priority tasks before checking messages.",
            planned_priorities="1. Finish Goal Explorer Canvas view\n2. Clear overdue topological sort practice set\n3. Maintain 3x weekly runs",
            selected_goal_ids=[g1.id, g2.id],
        )

        return True
