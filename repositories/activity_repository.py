"""Repositories for ActivityLog and Settings persistence."""

import sqlite3
import uuid
from typing import Dict, List, Optional

from database.connection import DatabaseManager
from database.schema import DEFAULT_SETTINGS
from models.entities import ActivityEvent
from utils.dates import now_iso


class ActivityRepository:
    """Data access layer for user activity events."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> ActivityEvent:
        return ActivityEvent(
            id=row["id"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            action=row["action"],
            description=row["description"],
            created_at=row["created_at"],
        )

    def log(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        description: str,
        created_at: Optional[str] = None,
    ) -> ActivityEvent:
        event = ActivityEvent(
            id=str(uuid.uuid4()),
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            description=description,
            created_at=created_at or now_iso(),
        )
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO activity_log (id, entity_type, entity_id, action, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.entity_type,
                    event.entity_id,
                    event.action,
                    event.description,
                    event.created_at,
                ),
            )
        return event

    def list_recent(self, limit: int = 20) -> List[ActivityEvent]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [self._row_to_event(r) for r in rows]

    def list_by_entity(self, entity_id: str, limit: int = 25) -> List[ActivityEvent]:
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM activity_log
                WHERE entity_id = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (entity_id, limit),
            ).fetchall()
            return [self._row_to_event(r) for r in rows]


class SettingsRepository:
    """Data access layer for application preferences and settings."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def get(self, key: str, default: Optional[str] = None) -> str:
        fallback = default if default is not None else DEFAULT_SETTINGS.get(key, "")
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
            return str(row["value"]) if row else fallback

    def set(self, key: str, value: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, str(value)),
            )

    def get_all(self) -> Dict[str, str]:
        result = dict(DEFAULT_SETTINGS)
        with self.db.connection() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            for r in rows:
                result[r["key"]] = r["value"]
        return result
