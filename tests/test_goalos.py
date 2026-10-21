"""Comprehensive automated test suite for GoalOS core business logic and persistence."""

from datetime import date, timedelta
import os
import tempfile
import unittest

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
from utils.dates import classify_deadline, days_until
from utils.validators import ValidationError


class GoalOSTestCase(unittest.TestCase):
    """Tests progress calculations, deadline logic, recommendations, and persistence."""

    def setUp(self) -> None:
        self.db = DatabaseManager(":memory:")
        self.goal_repo = GoalRepository(self.db)
        self.milestone_repo = MilestoneRepository(self.db)
        self.project_repo = ProjectRepository(self.db)
        self.task_repo = TaskRepository(self.db)
        self.review_repo = ReviewRepository(self.db)
        self.activity_repo = ActivityRepository(self.db)
        self.settings_repo = SettingsRepository(self.db)

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

    def tearDown(self) -> None:
        self.db.close()

    # --- 1. Progress Calculation Tests ---

    def test_project_progress_four_tasks_two_completed(self) -> None:
        g = self.goal_service.create_goal("Learn Rust")
        m = self.goal_service.create_milestone(g.id, "Basics")
        p = self.goal_service.create_project(m.id, "Exercises")

        t1 = self.task_service.create_task(p.id, "Task 1")
        t2 = self.task_service.create_task(p.id, "Task 2")
        self.task_service.create_task(p.id, "Task 3")
        self.task_service.create_task(p.id, "Task 4")

        self.task_service.complete_task(t1.id)
        self.task_service.complete_task(t2.id)

        stats = self.progress_service.get_project_progress(p.id)
        self.assertEqual(stats.completed_tasks, 2)
        self.assertEqual(stats.total_eligible_tasks, 4)
        self.assertAlmostEqual(stats.percentage, 50.0)

    def test_goal_aggregates_tasks_by_count_not_average_of_projects(self) -> None:
        g = self.goal_service.create_goal("Build App")
        m = self.goal_service.create_milestone(g.id, "M1")
        p1 = self.goal_service.create_project(m.id, "Small Project")
        p2 = self.goal_service.create_project(m.id, "Large Project")

        # p1 has 1 task (completed -> 100%)
        t_small = self.task_service.create_task(p1.id, "Only task")
        self.task_service.complete_task(t_small.id)

        # p2 has 3 tasks (0 completed -> 0%)
        for i in range(3):
            self.task_service.create_task(p2.id, f"Task {i}")

        # Total tasks across goal = 4, completed = 1 -> 25% (NOT 50%)
        goal_stats = self.progress_service.get_goal_progress(g.id)
        self.assertEqual(goal_stats.total_eligible_tasks, 4)
        self.assertEqual(goal_stats.completed_tasks, 1)
        self.assertAlmostEqual(goal_stats.percentage, 25.0)

    def test_cancelled_tasks_excluded_from_denominator(self) -> None:
        g = self.goal_service.create_goal("Goal X")
        m = self.goal_service.create_milestone(g.id, "M1")
        p = self.goal_service.create_project(m.id, "P1")

        t1 = self.task_service.create_task(p.id, "T1")
        t2 = self.task_service.create_task(p.id, "T2")
        t3 = self.task_service.create_task(p.id, "T3")

        self.task_service.complete_task(t1.id)
        self.task_service.update_task(t3.id, t3.title, status="cancelled")

        stats = self.progress_service.get_project_progress(p.id)
        self.assertEqual(stats.total_eligible_tasks, 2)
        self.assertEqual(stats.completed_tasks, 1)
        self.assertEqual(stats.cancelled_tasks, 1)
        self.assertAlmostEqual(stats.percentage, 50.0)

        # If all tasks are cancelled, do not report 100%
        self.task_service.update_task(t1.id, t1.title, status="cancelled")
        self.task_service.update_task(t2.id, t2.title, status="cancelled")
        all_cancelled = self.progress_service.get_project_progress(p.id)
        self.assertFalse(all_cancelled.has_eligible_tasks)
        self.assertAlmostEqual(all_cancelled.percentage, 0.0)
        self.assertIn("cancelled", all_cancelled.status_label)

    def test_empty_entity_progress_and_reopen_task(self) -> None:
        g = self.goal_service.create_goal("Empty Goal")
        empty_stats = self.progress_service.get_goal_progress(g.id)
        self.assertFalse(empty_stats.has_eligible_tasks)
        self.assertEqual(empty_stats.status_label, "No tasks yet")

        m = self.goal_service.create_milestone(g.id, "M1")
        p = self.goal_service.create_project(m.id, "P1")
        t = self.task_service.create_task(p.id, "Action")

        res = self.task_service.complete_task(t.id)
        self.assertTrue(res["suggest_goal_completion"])
        self.assertAlmostEqual(res["goal_progress"].percentage, 100.0)

        reopen_res = self.task_service.reopen_task(t.id)
        self.assertAlmostEqual(reopen_res["goal_progress"].percentage, 0.0)

    # --- 2. Deadline Calculations ---

    def test_deadline_classification(self) -> None:
        ref = date(2026, 10, 21)
        self.assertEqual(
            classify_deadline("2026-10-21", is_completed=False, reference_date=ref),
            "today",
        )
        self.assertEqual(
            classify_deadline("2026-10-19", is_completed=False, reference_date=ref),
            "overdue",
        )
        self.assertEqual(
            classify_deadline("2026-10-19", is_completed=True, reference_date=ref),
            "completed",
        )
        self.assertEqual(
            classify_deadline(None, is_completed=False, reference_date=ref),
            "unscheduled",
        )
        self.assertIsNone(days_until(None, reference_date=ref))

    def test_paused_goals_excluded_from_workload_warnings(self) -> None:
        ref = date(2026, 10, 21)
        g = self.goal_service.create_goal("Paused Goal")
        m = self.goal_service.create_milestone(g.id, "M1")
        p = self.goal_service.create_project(m.id, "P1")
        self.task_service.create_task(p.id, "Overdue Task", due_date="2026-10-15")

        # Active -> counts as 1 overdue
        summary_active = self.analytics_service.get_dashboard_summary(ref_date=ref)
        self.assertEqual(summary_active["overdue_count"], 1)

        # Pause goal -> excluded from overdue warning count
        self.goal_service.change_goal_status(g.id, "paused")
        summary_paused = self.analytics_service.get_dashboard_summary(ref_date=ref)
        self.assertEqual(summary_paused["overdue_count"], 0)

    # --- 3. Recommendation Engine Tests ---

    def test_recommendation_scoring_and_exclusions(self) -> None:
        ref = date(2026, 10, 21)
        g_active = self.goal_service.create_goal("Active High Goal", priority="high")
        m = self.goal_service.create_milestone(g_active.id, "M1")
        p = self.goal_service.create_project(m.id, "P1")

        t_overdue_high = self.task_service.create_task(
            p.id, "Urgent Overdue Task", due_date="2026-10-20", priority="high"
        )
        t_low_later = self.task_service.create_task(
            p.id, "Low Later Task", due_date="2026-11-15", priority="low"
        )
        t_future_sched = self.task_service.create_task(
            p.id,
            "Future Scheduled Task",
            due_date="2026-10-25",
            scheduled_date="2026-10-24",
            priority="high",
        )

        # Paused goal task
        g_paused = self.goal_service.create_goal("Paused Goal", priority="high")
        self.goal_service.change_goal_status(g_paused.id, "paused")
        mp = self.goal_service.create_milestone(g_paused.id, "MP")
        pp = self.goal_service.create_project(mp.id, "PP")
        t_paused = self.task_service.create_task(
            pp.id, "Task Under Paused", due_date="2026-10-19", priority="high"
        )

        recs = self.recommendation_service.get_recommendations(
            limit=5, include_future_scheduled=False, ref_date=ref
        )
        rec_ids = [r.task.id for r in recs]

        self.assertIn(t_overdue_high.id, rec_ids)
        self.assertIn(t_low_later.id, rec_ids)
        self.assertNotIn(t_future_sched.id, rec_ids)
        self.assertNotIn(t_paused.id, rec_ids)

        # Overdue high priority task must rank first and explain why
        top_rec = recs[0]
        self.assertEqual(top_rec.task.id, t_overdue_high.id)
        self.assertGreater(top_rec.total_score, recs[1].total_score)
        self.assertIn("overdue", top_rec.explanation.lower())
        self.assertIn("high priority", top_rec.explanation.lower())

    # --- 4. Persistence, Validation & Foreign Keys ---

    def test_persistence_across_restart_and_foreign_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_file = os.path.join(tmpdir, "test_goalos.db")
            db1 = DatabaseManager(db_file)
            g_repo1 = GoalRepository(db1)
            m_repo1 = MilestoneRepository(db1)
            p_repo1 = ProjectRepository(db1)
            t_repo1 = TaskRepository(db1)
            a_repo1 = ActivityRepository(db1)
            s_repo1 = SettingsRepository(db1)
            prog1 = ProgressService(t_repo1, g_repo1, s_repo1)
            g_srv1 = GoalService(g_repo1, m_repo1, p_repo1, t_repo1, a_repo1, prog1)
            t_srv1 = TaskService(t_repo1, p_repo1, m_repo1, g_repo1, a_repo1, prog1)

            g = g_srv1.create_goal("Persisted Goal", start_date="2026-10-01", deadline="2026-12-01")
            m = g_srv1.create_milestone(g.id, "Persisted Milestone")
            p = g_srv1.create_project(m.id, "Persisted Project")
            t = t_srv1.create_task(p.id, "Persisted Task", estimated_minutes=45)
            orig_created_at = t.created_at

            # Reopen with a brand new DatabaseManager instance
            db2 = DatabaseManager(db_file)
            t_repo2 = TaskRepository(db2)
            loaded_task = t_repo2.get_by_id(t.id)
            self.assertIsNotNone(loaded_task)
            self.assertEqual(loaded_task.title, "Persisted Task")
            self.assertEqual(loaded_task.goal_id, g.id)
            self.assertEqual(loaded_task.created_at, orig_created_at)

            # Updating task preserves ID and created_at
            t_srv2 = TaskService(
                t_repo2,
                ProjectRepository(db2),
                MilestoneRepository(db2),
                GoalRepository(db2),
                ActivityRepository(db2),
                ProgressService(t_repo2, GoalRepository(db2), SettingsRepository(db2)),
            )
            updated = t_srv2.update_task(t.id, "Renamed Task", estimated_minutes=60)
            self.assertEqual(updated.id, t.id)
            self.assertEqual(updated.created_at, orig_created_at)
            self.assertEqual(updated.title, "Renamed Task")

            # Invalid foreign key relationship is rejected
            with self.assertRaises(ValidationError):
                t_srv2.create_task("non-existent-project-id", "Orphan Task")

            # Date validation: deadline before start_date fails
            with self.assertRaises(ValidationError):
                g_srv1.create_goal(
                    "Invalid Dates", start_date="2026-10-20", deadline="2026-10-10"
                )


if __name__ == "__main__":
    unittest.main()
