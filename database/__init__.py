"""Database package for GoalOS."""

from database.connection import DatabaseManager
from database.schema import DEFAULT_SETTINGS, SCHEMA_SQL

__all__ = ["DatabaseManager", "DEFAULT_SETTINGS", "SCHEMA_SQL"]
