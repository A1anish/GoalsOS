"""Input validation functions for GoalOS."""

from typing import Optional, Tuple

from models.entities import (
    GOAL_STATUSES,
    MILESTONE_STATUSES,
    PRIORITIES,
    PROJECT_STATUSES,
    TASK_STATUSES,
)
from utils.dates import parse_iso_date


class ValidationError(ValueError):
    """Raised when user input or entity data fails validation."""


def validate_non_empty(value: Optional[str], field_name: str = "Title") -> str:
    """Ensures a string field is not empty."""
    if value is None or not str(value).strip():
        raise ValidationError(f"{field_name} cannot be empty.")
    return str(value).strip()


def validate_optional_date(date_str: Optional[str], field_name: str = "Date") -> Optional[str]:
    """Validates an optional YYYY-MM-DD date string."""
    if date_str is None or not str(date_str).strip():
        return None
    cleaned = str(date_str).strip()
    parsed = parse_iso_date(cleaned)
    if parsed is None:
        raise ValidationError(
            f"{field_name} must be a valid date in YYYY-MM-DD format (got '{cleaned}')."
        )
    return parsed.isoformat()


def validate_date_range(
    start_date_str: Optional[str],
    end_date_str: Optional[str],
    start_label: str = "Start date",
    end_label: str = "Deadline",
) -> Tuple[Optional[str], Optional[str]]:
    """Validates that both dates are valid ISO dates and end_date >= start_date."""
    start_iso = validate_optional_date(start_date_str, start_label)
    end_iso = validate_optional_date(end_date_str, end_label)
    if start_iso and end_iso:
        start_d = parse_iso_date(start_iso)
        end_d = parse_iso_date(end_iso)
        if start_d and end_d and end_d < start_d:
            raise ValidationError(f"{end_label} ({end_iso}) cannot precede {start_label} ({start_iso}).")
    return start_iso, end_iso


def validate_priority(priority: str) -> str:
    """Validates priority is one of low, medium, high."""
    cleaned = str(priority).strip().lower()
    if cleaned not in PRIORITIES:
        raise ValidationError(f"Priority must be one of {PRIORITIES}, got '{priority}'.")
    return cleaned


def validate_status(status: str, allowed_statuses: list, entity_label: str = "Entity") -> str:
    """Validates status belongs to allowed_statuses."""
    cleaned = str(status).strip().lower()
    if cleaned not in allowed_statuses:
        raise ValidationError(
            f"{entity_label} status must be one of {allowed_statuses}, got '{status}'."
        )
    return cleaned


def validate_goal_status(status: str) -> str:
    return validate_status(status, GOAL_STATUSES, "Goal")


def validate_milestone_status(status: str) -> str:
    return validate_status(status, MILESTONE_STATUSES, "Milestone")


def validate_project_status(status: str) -> str:
    return validate_status(status, PROJECT_STATUSES, "Project")


def validate_task_status(status: str) -> str:
    return validate_status(status, TASK_STATUSES, "Task")


def validate_duration(minutes_val: object, field_name: str = "Estimated duration") -> int:
    """Validates non-negative integer duration in minutes."""
    if minutes_val is None or str(minutes_val).strip() == "":
        return 30
    try:
        val = int(float(str(minutes_val).strip()))
    except (ValueError, TypeError) as exc:
        raise ValidationError(f"{field_name} must be a valid number of minutes.") from exc
    if val < 0:
        raise ValidationError(f"{field_name} cannot be negative.")
    return val


def validate_optional_float(num_val: object, field_name: str = "Target value") -> Optional[float]:
    """Validates an optional numeric target value."""
    if num_val is None or str(num_val).strip() == "":
        return None
    try:
        val = float(str(num_val).strip())
    except (ValueError, TypeError) as exc:
        raise ValidationError(f"{field_name} must be a valid number.") from exc
    if val < 0:
        raise ValidationError(f"{field_name} cannot be negative.")
    return val
