"""Repository for Task database persistence."""

import sqlite3
from typing import List, Optional

from database.connection import DatabaseManager
from models.entities import Task


class TaskRepository:
    """Data access layer for Task entities."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        keys = row.keys()
        return Task(
            id=row["id"],
            project_id=row["project_id"],
            title=row["title"],
            description=row["description"] or "",
            due_date=row["due_date"],
            scheduled_date=row["scheduled_date"],
            estimated_minutes=row["estimated_minutes"] if row["estimated_minutes"] is not None else 30,
            actual_minutes=row["actual_minutes"] or 0,
            priority=row["priority"] or "medium",
            status=row["status"] or "todo",
            position=row["position"] or 0,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            completed_at=row["completed_at"],
            project_title=row["project_title"] if "project_title" in keys and row["project_title"] else "",
            milestone_id=row["milestone_id"] if "milestone_id" in keys and row["milestone_id"] else "",
            milestone_title=row["milestone_title"] if "milestone_title" in keys and row["milestone_title"] else "",
            goal_id=row["goal_id"] if "goal_id" in keys and row["goal_id"] else "",
            goal_title=row["goal_title"] if "goal_title" in keys and row["goal_title"] else "",
            goal_color=row["goal_color"] if "goal_color" in keys and row["goal_color"] else "#6366F1",
            goal_status=row["goal_status"] if "goal_status" in keys and row["goal_status"] else "active",
            goal_priority=row["goal_priority"] if "goal_priority" in keys and row["goal_priority"] else "medium",
        )

    _ENRICHED_SELECT = """
        SELECT
            t.*,
            p.title AS project_title,
            m.id AS milestone_id,
            m.title AS milestone_title,
            g.id AS goal_id,
            g.title AS goal_title,
            g.color AS goal_color,
            g.status AS goal_status,
            g.priority AS goal_priority
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        JOIN milestones m ON p.milestone_id = m.id
        JOIN goals g ON m.goal_id = g.id
    """

    def create(self, task: Task) -> Task:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO tasks (
                    id, project_id, title, description, due_date, scheduled_date,
                    estimated_minutes, actual_minutes, priority, status, position,
                    created_at, updated_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id,
                    task.project_id,
                    task.title,
                    task.description,
                    task.due_date,
                    task.scheduled_date,
                    task.estimated_minutes,
                    task.actual_minutes,
                    task.priority,
                    task.status,
                    task.position,
                    task.created_at,
                    task.updated_at,
                    task.completed_at,
                ),
            )
        return self.get_by_id(task.id) or task

    def update(self, task: Task) -> Task:
        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE tasks SET
                    project_id = ?,
                    title = ?,
                    description = ?,
                    due_date = ?,
                    scheduled_date = ?,
                    estimated_minutes = ?,
                    actual_minutes = ?,
                    priority = ?,
                    status = ?,
                    position = ?,
                    updated_at = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    task.project_id,
                    task.title,
                    task.description,
                    task.due_date,
                    task.scheduled_date,
                    task.estimated_minutes,
                    task.actual_minutes,
                    task.priority,
                    task.status,
                    task.position,
                    task.updated_at,
                    task.completed_at,
                    task.id,
                ),
            )
        return self.get_by_id(task.id) or task

    def get_by_id(self, task_id: str) -> Optional[Task]:
        with self.db.connection() as conn:
            row = conn.execute(
                self._ENRICHED_SELECT + " WHERE t.id = ?", (task_id,)
            ).fetchone()
            return self._row_to_task(row) if row else None

    def list_by_project(self, project_id: str) -> List[Task]:
        with self.db.connection() as conn:
            rows = conn.execute(
                self._ENRICHED_SELECT
                + " WHERE t.project_id = ? ORDER BY t.position ASC, COALESCE(t.due_date, '9999-12-31') ASC, t.created_at ASC",
                (project_id,),
            ).fetchall()
            return [self._row_to_task(r) for r in rows]

    def list_by_milestone(self, milestone_id: str) -> List[Task]:
        with self.db.connection() as conn:
            rows = conn.execute(
                self._ENRICHED_SELECT
                + " WHERE m.id = ? ORDER BY p.position ASC, t.position ASC",
                (milestone_id,),
            ).fetchall()
            return [self._row_to_task(r) for r in rows]

    def list_by_goal(self, goal_id: str) -> List[Task]:
        with self.db.connection() as conn:
            rows = conn.execute(
                self._ENRICHED_SELECT
                + " WHERE g.id = ? ORDER BY m.position ASC, p.position ASC, t.position ASC",
                (goal_id,),
            ).fetchall()
            return [self._row_to_task(r) for r in rows]

    def list_all(self, include_archived_goals: bool = False) -> List[Task]:
        query = self._ENRICHED_SELECT
        if not include_archived_goals:
            query += " WHERE g.status != 'archived'"
        query += " ORDER BY COALESCE(t.due_date, '9999-12-31') ASC, CASE t.priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, t.created_at DESC"
        with self.db.connection() as conn:
            rows = conn.execute(query).fetchall()
            return [self._row_to_task(r) for r in rows]

    def get_next_position(self, project_id: str) -> int:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 AS next_pos FROM tasks WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            return int(row["next_pos"]) if row else 0

    def delete(self, task_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
