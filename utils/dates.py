"""Date parsing, calculation, and formatting utilities for GoalOS."""

from datetime import date, datetime, timedelta
from typing import Optional, Tuple


def today_iso() -> str:
    """Returns today's local date in YYYY-MM-DD format."""
    return date.today().isoformat()


def now_iso() -> str:
    """Returns current local timestamp in ISO-8601 format (seconds precision)."""
    return datetime.now().replace(microsecond=0).isoformat()


def parse_iso_date(date_str: Optional[str]) -> Optional[date]:
    """Parses a YYYY-MM-DD date string or ISO timestamp prefix safely."""
    if not date_str or not str(date_str).strip():
        return None
    cleaned = str(date_str).strip()[:10]
    try:
        return datetime.strptime(cleaned, "%Y-%m-%d").date()
    except ValueError:
        return None


def days_until(target_date_str: Optional[str], reference_date: Optional[date] = None) -> Optional[int]:
    """Calculates signed integer days from reference_date (default today) to target_date_str.
    Negative means in the past (overdue if incomplete), 0 means today, positive means future.
    """
    target = parse_iso_date(target_date_str)
    if target is None:
        return None
    ref = reference_date or date.today()
    return (target - ref).days


def classify_deadline(
    due_date_str: Optional[str],
    is_completed: bool = False,
    reference_date: Optional[date] = None,
) -> str:
    """Classifies a deadline into one of:
    'completed', 'overdue', 'today', 'next_7_days', 'later', 'unscheduled'.
    Completed tasks are never classified as 'overdue'.
    """
    if is_completed:
        return "completed"
    diff = days_until(due_date_str, reference_date=reference_date)
    if diff is None:
        return "unscheduled"
    if diff < 0:
        return "overdue"
    if diff == 0:
        return "today"
    if diff <= 7:
        return "next_7_days"
    return "later"


def format_relative_deadline(
    due_date_str: Optional[str],
    is_completed: bool = False,
    reference_date: Optional[date] = None,
) -> Tuple[str, str]:
    """Returns (human_readable_label, semantic_state) for a deadline.
    semantic_state is one of: 'positive', 'danger', 'warning', 'info', 'muted'.
    """
    if not due_date_str:
        return ("No deadline", "muted")
    if is_completed:
        return (f"Completed ({due_date_str[:10]})", "positive")

    diff = days_until(due_date_str, reference_date=reference_date)
    if diff is None:
        return ("No deadline", "muted")
    if diff < -1:
        return (f"{abs(diff)}d overdue", "danger")
    if diff == -1:
        return ("1d overdue", "danger")
    if diff == 0:
        return ("Due today", "warning")
    if diff == 1:
        return ("Due tomorrow", "warning")
    if diff <= 7:
        return (f"In {diff} days", "info")
    return (due_date_str[:10], "muted")


def format_display_date(date_str: Optional[str], fmt: str = "YYYY-MM-DD") -> str:
    """Formats an ISO date string into the user's preferred display format."""
    parsed = parse_iso_date(date_str)
    if parsed is None:
        return "—"
    if fmt == "DD/MM/YYYY":
        return parsed.strftime("%d/%m/%Y")
    if fmt == "MMM D, YYYY":
        return parsed.strftime("%b %d, %Y")
    return parsed.isoformat()


def format_duration(minutes: Optional[int]) -> str:
    """Formats minutes into a concise string like '45m' or '2h 15m'."""
    if minutes is None or minutes <= 0:
        return "0m"
    hrs = minutes // 60
    mins = minutes % 60
    if hrs > 0 and mins > 0:
        return f"{hrs}h {mins}m"
    if hrs > 0:
        return f"{hrs}h"
    return f"{mins}m"


def get_week_bounds(ref_date: Optional[date] = None) -> Tuple[str, str]:
    """Returns (monday_iso, sunday_iso) for the week containing ref_date."""
    ref = ref_date or date.today()
    monday = ref - timedelta(days=ref.weekday())
    sunday = monday + timedelta(days=6)
    return monday.isoformat(), sunday.isoformat()
