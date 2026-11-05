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

    def reset_sample_data(self) -> None:
        """Clears existing records and seeds fresh sample data."""
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM review_goals;")
            conn.execute("DELETE FROM weekly_reviews;")
            conn.execute("DELETE FROM tasks;")
            conn.execute("DELETE FROM projects;")
            conn.execute("DELETE FROM milestones;")
            conn.execute("DELETE FROM goals;")
            conn.execute("DELETE FROM activity_log;")
        self.seed_sample_data_if_empty(force=True)

    def seed_sample_data_if_empty(self, force: bool = False) -> bool:
        """Populates clean sample goals, milestones, projects, tasks, and reviews."""
        existing_goals = self.goal_repo.list_all()
        if existing_goals and not force:
            return False

        today = date.today()
        d = lambda offset: (today + timedelta(days=offset)).isoformat()
        ts = lambda offset: f"{d(offset)}T14:30:00"

        # Goal 1: Build Python Desktop Application
        g1 = self.goal_service.create_goal(
            title="Build Python Desktop Application",
            description="Design and implement GoalOS using Python, Tkinter, and SQLite.",
            category="Projects",
            start_date=d(-7),
            deadline=d(7),
            priority="high",
            target_value=1,
            target_unit="app",
            color="#6366F1",
        )
        m1_1 = self.goal_service.create_milestone(
            goal_id=g1.id,
            title="Database & Core Services",
            description="SQLite schema, repositories, and progress engine.",
            start_date=d(-7),
            deadline=d(-1),
        )
        p1_1 = self.goal_service.create_project(
            milestone_id=m1_1.id,
            title="SQLite Storage Layer",
            description="Normalized tables and CRUD repositories.",
            start_date=d(-7),
            deadline=d(-1),
            priority="high",
        )
        t1 = self.task_service.create_task(
            p1_1.id, "Create SQLite schema and tables", due_date=d(-4), scheduled_date=d(-4), estimated_minutes=45, priority="high"
        )
        self.task_service.complete_task(t1.id, completed_at=ts(-4))

        t2 = self.task_service.create_task(
            p1_1.id, "Implement progress calculation service", due_date=d(-2), scheduled_date=d(-2), estimated_minutes=60, priority="high"
        )
        self.task_service.complete_task(t2.id, completed_at=ts(-2))

        m1_2 = self.goal_service.create_milestone(
            goal_id=g1.id,
            title="Tkinter Frontend Interface",
            description="Dashboard, Goal Explorer, and Canvas charts.",
            start_date=d(0),
            deadline=d(6),
        )
        p1_2 = self.goal_service.create_project(
            milestone_id=m1_2.id,
            title="UI Pages & Canvas Widgets",
            description="Build main pages and custom Canvas components.",
            start_date=d(0),
            deadline=d(6),
            priority="high",
        )
        t3 = self.task_service.create_task(
            p1_2.id, "Build Dashboard and Goal Cards", due_date=d(-1), scheduled_date=d(-1), estimated_minutes=50, priority="high"
        )
        self.task_service.complete_task(t3.id, completed_at=ts(-1))

        t4 = self.task_service.create_task(
            p1_2.id, "Design Goal Explorer hierarchy canvas", due_date=d(1), scheduled_date=d(0), estimated_minutes=60, priority="high"
        )
        self.task_service.update_task(
            t4.id, t4.title, t4.description, due_date=t4.due_date, scheduled_date=t4.scheduled_date, estimated_minutes=60, priority="high", status="in_progress"
        )

        self.task_service.create_task(
            p1_2.id, "Test 7-day timeline and analytics charts", due_date=d(3), scheduled_date=d(2), estimated_minutes=45, priority="medium"
        )

        # Goal 2: APP (Advanced Programming Practice)
        g2 = self.goal_service.create_goal(
            title="APP",
            description="Advanced Programming Practice — Multi-paradigm programming across Java and Python.",
            category="Education",
            start_date=d(-6),
            deadline=d(7),
            priority="high",
            target_value=5,
            target_unit="units",
            color="#10B981",
        )
        m2_1 = self.goal_service.create_milestone(
            goal_id=g2.id,
            title="Unit 1 & 2: Imperative & Java OOP Paradigms",
            description="Programming language theory, Bohm-Jacopini theorem, and Java OOP.",
            start_date=d(-6),
            deadline=d(-1),
        )
        p2_1 = self.goal_service.create_project(
            milestone_id=m2_1.id,
            title="Procedural & Object-Oriented Java",
            description="Classes, inheritance, polymorphism, interfaces, and packages.",
            start_date=d(-6),
            deadline=d(-1),
            priority="high",
        )
        t2_1 = self.task_service.create_task(
            p2_1.id, "Study Bohm-Jacopini theorem & paradigm hierarchy", due_date=d(-4), scheduled_date=d(-4), estimated_minutes=40, priority="high"
        )
        self.task_service.complete_task(t2_1.id, completed_at=ts(-4))

        t2_2 = self.task_service.create_task(
            p2_1.id, "Implement Java OOP classes, interfaces, and packages", due_date=d(-2), scheduled_date=d(-2), estimated_minutes=50, priority="high"
        )
        self.task_service.complete_task(t2_2.id, completed_at=ts(-2))

        m2_2 = self.goal_service.create_milestone(
            goal_id=g2.id,
            title="Unit 3 & 4: Concurrent Java & Pythonic Paradigms",
            description="Multithreading, JDBC, Java Swing MVC, functional Python, and TCP/UDP sockets.",
            start_date=d(-1),
            deadline=d(4),
        )
        p2_2 = self.goal_service.create_project(
            milestone_id=m2_2.id,
            title="Multithreading, JDBC & Functional Python",
            description="Practice concurrent threads, MySQL connectivity, and higher-order functions.",
            start_date=d(-1),
            deadline=d(4),
            priority="high",
        )
        t2_3 = self.task_service.create_task(
            p2_2.id, "Practice Java multithreading and JDBC MySQL queries", due_date=d(1), scheduled_date=d(0), estimated_minutes=45, priority="high"
        )
        self.task_service.update_task(
            t2_3.id, t2_3.title, t2_3.description, due_date=t2_3.due_date, scheduled_date=t2_3.scheduled_date, estimated_minutes=45, priority="high", status="in_progress"
        )

        self.task_service.create_task(
            p2_2.id, "Write pure higher-order functions and TCP/UDP client-server sockets", due_date=d(3), scheduled_date=d(2), estimated_minutes=50, priority="medium"
        )

        m2_3 = self.goal_service.create_milestone(
            goal_id=g2.id,
            title="Unit 5: Formal, Symbolic & Event-Driven Paradigm",
            description="DFA/NFA finite automata, SymPy symbolic algebra, and Tkinter event-driven GUI.",
            start_date=d(2),
            deadline=d(7),
        )
        p2_3 = self.goal_service.create_project(
            milestone_id=m2_3.id,
            title="Automata, SymPy & Tkinter Dissertation",
            description="Implement finite automata, symbolic calculus, and event handlers in Tkinter.",
            start_date=d(2),
            deadline=d(7),
            priority="high",
        )
        self.task_service.create_task(
            p2_3.id, "Implement DFA/NFA automata and SymPy algebraic expressions", due_date=d(5), scheduled_date=d(4), estimated_minutes=45, priority="medium"
        )
        self.task_service.create_task(
            p2_3.id, "Develop Python Tkinter event-driven project dissertation", due_date=d(6), scheduled_date=d(5), estimated_minutes=60, priority="high"
        )

        # Goal 3: Daily Fitness & Running Routine
        g3 = self.goal_service.create_goal(
            title="5K Running & Fitness Routine",
            description="Maintain consistent morning runs and stretching sessions.",
            category="Health and Wellness",
            start_date=d(-6),
            deadline=d(7),
            priority="medium",
            target_value=5,
            target_unit="km",
            color="#F59E0B",
        )
        m3_1 = self.goal_service.create_milestone(
            goal_id=g3.id,
            title="Weekly Running Target",
            description="Complete 3 runs this week.",
            start_date=d(-6),
            deadline=d(6),
        )
        p3_1 = self.goal_service.create_project(
            milestone_id=m3_1.id,
            title="Morning Runs",
            description="Cardio and mobility sessions.",
            start_date=d(-6),
            deadline=d(6),
            priority="medium",
        )
        t3_1 = self.task_service.create_task(
            p3_1.id, "Complete 3K morning run", due_date=d(-1), scheduled_date=d(-1), estimated_minutes=30, priority="medium"
        )
        self.task_service.complete_task(t3_1.id, completed_at=ts(-1))

        self.task_service.create_task(
            p3_1.id, "20-minute mobility and stretching", due_date=d(0), scheduled_date=d(0), estimated_minutes=20, priority="medium"
        )
        self.task_service.create_task(
            p3_1.id, "Weekend 5K endurance run", due_date=d(4), scheduled_date=d(4), estimated_minutes=40, priority="low"
        )

        # Sample Weekly Review
        self.review_service.save_weekly_review(
            period_start=d(-7),
            period_end=d(0),
            went_well="Completed the database schema and core progress calculation service.",
            challenges="Balancing exam revision with project coding.",
            lessons_learned="Breaking projects into 30–60 minute tasks keeps daily progress steady.",
            next_week_changes="Finish the remaining UI testing tasks early in the week.",
            planned_priorities="1. Finish Goal Explorer canvas\n2. Solve graph practice sheet\n3. Complete weekend 5K run",
            selected_goal_ids=[g1.id, g2.id],
        )

        return True
