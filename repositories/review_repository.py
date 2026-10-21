"""Repository for WeeklyReview database persistence."""

import sqlite3
from typing import List, Optional

from database.connection import DatabaseManager
from models.entities import WeeklyReview


class ReviewRepository:
    """Data access layer for WeeklyReview entities and their associated goals."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def _row_to_review(
        self, row: sqlite3.Row, conn: sqlite3.Connection
    ) -> WeeklyReview:
        goal_rows = conn.execute(
            "SELECT goal_id FROM review_goals WHERE review_id = ?",
            (row["id"],),
        ).fetchall()
        selected_ids = [r["goal_id"] for r in goal_rows]
        return WeeklyReview(
            id=row["id"],
            period_start=row["period_start"],
            period_end=row["period_end"],
            went_well=row["went_well"] or "",
            challenges=row["challenges"] or "",
            lessons_learned=row["lessons_learned"] or "",
            next_week_changes=row["next_week_changes"] or "",
            planned_priorities=row["planned_priorities"] or "",
            selected_goal_ids=selected_ids,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create(self, review: WeeklyReview) -> WeeklyReview:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO weekly_reviews (
                    id, period_start, period_end, went_well, challenges,
                    lessons_learned, next_week_changes, planned_priorities,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review.id,
                    review.period_start,
                    review.period_end,
                    review.went_well,
                    review.challenges,
                    review.lessons_learned,
                    review.next_week_changes,
                    review.planned_priorities,
                    review.created_at,
                    review.updated_at,
                ),
            )
            for goal_id in review.selected_goal_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO review_goals (review_id, goal_id) VALUES (?, ?)",
                    (review.id, goal_id),
                )
        return review

    def get_by_id(self, review_id: str) -> Optional[WeeklyReview]:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM weekly_reviews WHERE id = ?", (review_id,)
            ).fetchone()
            return self._row_to_review(row, conn) if row else None

    def list_all(self) -> List[WeeklyReview]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM weekly_reviews ORDER BY period_end DESC, created_at DESC"
            ).fetchall()
            return [self._row_to_review(r, conn) for r in rows]

    def delete(self, review_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM weekly_reviews WHERE id = ?", (review_id,))
