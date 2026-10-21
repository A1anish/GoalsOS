"""Repository for Goal database persistence."""

import sqlite3
from typing import List, Optional

from database.connection import DatabaseManager
from models.entities import Goal


class GoalRepository:
    """Data access layer for Goal entities."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    @staticmethod
    def _row_to_goal(row: sqlite3.Row) -> Goal:
        return Goal(
            id=row["id"],
            title=row["title"],
            description=row["description"] or "",
            category=row["category"] or "Other",
            start_date=row["start_date"],
            deadline=row["deadline"],
            priority=row["priority"] or "medium",
            status=row["status"] or "active",
            target_value=row["target_value"],
            target_unit=row["target_unit"] or "",
            color=row["color"] or "#6366F1",
            completion_notes=row["completion_notes"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            completed_at=row["completed_at"],
        )

    def create(self, goal: Goal) -> Goal:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO goals (
                    id, title, description, category, start_date, deadline,
                    priority, status, target_value, target_unit, color,
                    completion_notes, created_at, updated_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    goal.id,
                    goal.title,
                    goal.description,
                    goal.category,
                    goal.start_date,
                    goal.deadline,
                    goal.priority,
                    goal.status,
                    goal.target_value,
                    goal.target_unit,
                    goal.color,
                    goal.completion_notes,
                    goal.created_at,
                    goal.updated_at,
                    goal.completed_at,
                ),
            )
        return goal

    def update(self, goal: Goal) -> Goal:
        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE goals SET
                    title = ?,
                    description = ?,
                    category = ?,
                    start_date = ?,
                    deadline = ?,
                    priority = ?,
                    status = ?,
                    target_value = ?,
                    target_unit = ?,
                    color = ?,
                    completion_notes = ?,
                    updated_at = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    goal.title,
                    goal.description,
                    goal.category,
                    goal.start_date,
                    goal.deadline,
                    goal.priority,
                    goal.status,
                    goal.target_value,
                    goal.target_unit,
                    goal.color,
                    goal.completion_notes,
                    goal.updated_at,
                    goal.completed_at,
                    goal.id,
                ),
            )
        return goal

    def get_by_id(self, goal_id: str) -> Optional[Goal]:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM goals WHERE id = ?", (goal_id,)
            ).fetchone()
            return self._row_to_goal(row) if row else None

    def list_all(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Goal]:
        query = "SELECT * FROM goals WHERE 1=1"
        params: list = []
        if status and status != "all":
            query += " AND status = ?"
            params.append(status)
        if category and category != "All":
            query += " AND category = ?"
            params.append(category)
        if search and search.strip():
            q = f"%{search.strip()}%"
            query += " AND (title LIKE ? OR description LIKE ? OR category LIKE ?)"
            params.extend([q, q, q])
        query += " ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, COALESCE(deadline, '9999-12-31') ASC, created_at DESC"

        with self.db.connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_goal(r) for r in rows]

    def get_distinct_categories(self) -> List[str]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT category FROM goals ORDER BY category ASC"
            ).fetchall()
            return [r["category"] for r in rows if r["category"]]

    def delete(self, goal_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
