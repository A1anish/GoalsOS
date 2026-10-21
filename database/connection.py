"""Database connection and transaction management for GoalOS."""

from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import sqlite3
from typing import Iterator, Optional

from database.schema import DEFAULT_SETTINGS, SCHEMA_SQL


class DatabaseManager:
    """Manages SQLite connections, initialization, and transactions.
    Supports both native POSIX/Windows paths and \\\\wsl.localhost UNC network paths.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path is None:
            base_dir = Path(__file__).resolve().parent.parent / "data"
            base_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(base_dir / "goalos.db")
        else:
            self.db_path = str(db_path)
            if self.db_path != ":memory:":
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._active_db_path: str = self.db_path
        self._sync_target_path: Optional[str] = None
        self._persistent_conn: Optional[sqlite3.Connection] = None

        if self.db_path == ":memory:":
            self._persistent_conn = self._create_connection()
        else:
            self._configure_lock_safe_path()

        self.initialize_database()

    def _configure_lock_safe_path(self) -> None:
        """Detects if SQLite byte-range locking fails on a Windows \\\\wsl.localhost UNC share
        and transparently mirrors to a local lock-safe SQLite file synced on commit.
        """
        try:
            conn = sqlite3.connect(self.db_path, timeout=2.0)
            conn.execute("PRAGMA schema_version;")
            conn.execute("CREATE TABLE IF NOT EXISTS _lock_probe (id INTEGER);")
            conn.execute("DROP TABLE IF EXISTS _lock_probe;")
            conn.commit()
            conn.close()
        except sqlite3.OperationalError:
            fallback_dir = Path.home() / ".goalos_cache"
            fallback_dir.mkdir(parents=True, exist_ok=True)
            local_file = fallback_dir / Path(self.db_path).name
            if os.path.isfile(self.db_path) and os.path.getsize(self.db_path) > 0:
                try:
                    shutil.copy2(self.db_path, local_file)
                except Exception:
                    pass
            self._active_db_path = str(local_file)
            self._sync_target_path = self.db_path

    def _sync_to_target(self) -> None:
        """Copies the active database back to the UNC target path if mirroring is active."""
        if self._sync_target_path and os.path.isfile(self._active_db_path):
            try:
                shutil.copy2(self._active_db_path, self._sync_target_path)
            except Exception:
                pass

    def _create_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._active_db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def get_connection(self) -> sqlite3.Connection:
        """Returns a configured SQLite connection with foreign keys enabled."""
        if self._persistent_conn is not None:
            return self._persistent_conn
        return self._create_connection()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Context manager providing an atomic transaction."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            if self._persistent_conn is None:
                conn.close()
                self._sync_to_target()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Context manager for read operations."""
        conn = self.get_connection()
        try:
            yield conn
        finally:
            if self._persistent_conn is None:
                conn.close()

    def initialize_database(self) -> None:
        """Creates tables, indexes, and default settings if they do not exist."""
        with self.transaction() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.execute("PRAGMA foreign_keys = ON;")
            for key, value in DEFAULT_SETTINGS.items():
                conn.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, value),
                )

    def close(self) -> None:
        """Closes persistent in-memory connection if present."""
        if self._persistent_conn is not None:
            self._persistent_conn.close()
            self._persistent_conn = None

    @staticmethod
    def validate_sqlite_file(file_path: str) -> bool:
        """Validates that a file is a valid GoalOS SQLite database."""
        if not os.path.isfile(file_path):
            return False
        probe_path = file_path
        temp_copy: Optional[Path] = None
        if str(file_path).startswith("\\\\"):
            fallback_dir = Path.home() / ".goalos_cache"
            fallback_dir.mkdir(parents=True, exist_ok=True)
            temp_copy = fallback_dir / "_validate_probe.db"
            try:
                shutil.copy2(file_path, temp_copy)
                probe_path = str(temp_copy)
            except Exception:
                return False
        try:
            conn = sqlite3.connect(probe_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            integrity = cursor.fetchone()
            if not integrity or integrity[0] != "ok":
                conn.close()
                return False

            required_tables = {
                "goals",
                "milestones",
                "projects",
                "tasks",
                "weekly_reviews",
                "activity_log",
            }
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            )
            existing_tables = {row[0] for row in cursor.fetchall()}
            conn.close()
            return required_tables.issubset(existing_tables)
        except Exception:
            return False
        finally:
            if temp_copy and temp_copy.exists():
                try:
                    temp_copy.unlink()
                except Exception:
                    pass
