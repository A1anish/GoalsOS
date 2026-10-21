"""Repository for Project database persistence."""

import sqlite3
from typing import List, Optional

from database.connection import DatabaseManager
from models.entities import Project


class ProjectRepository:
    """Data access layer for Project entities."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    @staticmethod
    def _row_to_project(row: sqlite3.Row) -> Project:
        return Project(
            id=row["id"],
            milestone_id=row["milestone_id"],
            title=row["title"],
            description=row["description"] or "",
            start_date=row["start_date"],
            deadline=row["deadline"],
            priority=row["priority"] or "medium",
            status=row["status"] or "active",
            position=row["position"] or 0,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            completed_at=row["completed_at"],
        )

    def create(self, project: Project) -> Project:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO projects (
                    id, milestone_id, title, description, start_date, deadline,
                    priority, status, position, created_at, updated_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project.id,
                    project.milestone_id,
                    project.title,
                    project.description,
                    project.start_date,
                    project.deadline,
                    project.priority,
                    project.status,
                    project.position,
                    project.created_at,
                    project.updated_at,
                    project.completed_at,
                ),
            )
        return project

    def update(self, project: Project) -> Project:
        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE projects SET
                    milestone_id = ?,
                    title = ?,
                    description = ?,
                    start_date = ?,
                    deadline = ?,
                    priority = ?,
                    status = ?,
                    position = ?,
                    updated_at = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    project.milestone_id,
                    project.title,
                    project.description,
                    project.start_date,
                    project.deadline,
                    project.priority,
                    project.status,
                    project.position,
                    project.updated_at,
                    project.completed_at,
                    project.id,
                ),
            )
        return project

    def get_by_id(self, project_id: str) -> Optional[Project]:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            return self._row_to_project(row) if row else None

    def list_by_milestone(self, milestone_id: str) -> List[Project]:
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM projects
                WHERE milestone_id = ?
                ORDER BY position ASC, COALESCE(deadline, '9999-12-31') ASC, created_at ASC
                """,
                (milestone_id,),
            ).fetchall()
            return [self._row_to_project(r) for r in rows]

    def list_by_goal(self, goal_id: str) -> List[Project]:
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT p.* FROM projects p
                JOIN milestones m ON p.milestone_id = m.id
                WHERE m.goal_id = ?
                ORDER BY m.position ASC, p.position ASC
                """,
                (goal_id,),
            ).fetchall()
            return [self._row_to_project(r) for r in rows]

    def list_all(self) -> List[Project]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM projects ORDER BY position ASC, created_at ASC"
            ).fetchall()
            return [self._row_to_project(r) for r in rows]

    def get_next_position(self, milestone_id: str) -> int:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 AS next_pos FROM projects WHERE milestone_id = ?",
                (milestone_id,),
            ).fetchone()
            return int(row["next_pos"]) if row else 0

    def delete(self, project_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
