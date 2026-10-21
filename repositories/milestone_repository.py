"""Repository for Milestone database persistence."""

import sqlite3
from typing import List, Optional

from database.connection import DatabaseManager
from models.entities import Milestone


class MilestoneRepository:
    """Data access layer for Milestone entities."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    @staticmethod
    def _row_to_milestone(row: sqlite3.Row) -> Milestone:
        return Milestone(
            id=row["id"],
            goal_id=row["goal_id"],
            title=row["title"],
            description=row["description"] or "",
            start_date=row["start_date"],
            deadline=row["deadline"],
            status=row["status"] or "active",
            position=row["position"] or 0,
            completion_notes=row["completion_notes"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            completed_at=row["completed_at"],
        )

    def create(self, milestone: Milestone) -> Milestone:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO milestones (
                    id, goal_id, title, description, start_date, deadline,
                    status, position, completion_notes, created_at, updated_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    milestone.id,
                    milestone.goal_id,
                    milestone.title,
                    milestone.description,
                    milestone.start_date,
                    milestone.deadline,
                    milestone.status,
                    milestone.position,
                    milestone.completion_notes,
                    milestone.created_at,
                    milestone.updated_at,
                    milestone.completed_at,
                ),
            )
        return milestone

    def update(self, milestone: Milestone) -> Milestone:
        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE milestones SET
                    goal_id = ?,
                    title = ?,
                    description = ?,
                    start_date = ?,
                    deadline = ?,
                    status = ?,
                    position = ?,
                    completion_notes = ?,
                    updated_at = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    milestone.goal_id,
                    milestone.title,
                    milestone.description,
                    milestone.start_date,
                    milestone.deadline,
                    milestone.status,
                    milestone.position,
                    milestone.completion_notes,
                    milestone.updated_at,
                    milestone.completed_at,
                    milestone.id,
                ),
            )
        return milestone

    def get_by_id(self, milestone_id: str) -> Optional[Milestone]:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM milestones WHERE id = ?", (milestone_id,)
            ).fetchone()
            return self._row_to_milestone(row) if row else None

    def list_by_goal(self, goal_id: str) -> List[Milestone]:
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM milestones
                WHERE goal_id = ?
                ORDER BY position ASC, COALESCE(deadline, '9999-12-31') ASC, created_at ASC
                """,
                (goal_id,),
            ).fetchall()
            return [self._row_to_milestone(r) for r in rows]

    def list_all(self) -> List[Milestone]:
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM milestones
                ORDER BY position ASC, COALESCE(deadline, '9999-12-31') ASC
                """
            ).fetchall()
            return [self._row_to_milestone(r) for r in rows]

    def get_next_position(self, goal_id: str) -> int:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 AS next_pos FROM milestones WHERE goal_id = ?",
                (goal_id,),
            ).fetchone()
            return int(row["next_pos"]) if row else 0

    def delete(self, milestone_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM milestones WHERE id = ?", (milestone_id,))
