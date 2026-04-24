"""
Bangladesh Standard Time (BST) utility — UTC+6
All timestamps displayed to users / stored in audit logs use BST.
Internal processing uses UTC (stored in DB as UTC, displayed as BST).
BFIU Circular No. 29 — all audit timestamps in local Bangladesh time.
"""
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

BST = ZoneInfo("Asia/Dhaka")   # UTC+6
UTC = timezone.utc


def now_bst() -> datetime:
    """Current time in Bangladesh Standard Time."""
    return datetime.now(BST)


def now_utc() -> datetime:
    """Current time in UTC (for DB storage)."""
    return datetime.now(UTC)


def to_bst(dt: datetime) -> datetime:
    """Convert any datetime to BST."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(BST)


def to_utc(dt: datetime) -> datetime:
    """Convert any datetime to UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BST)
    return dt.astimezone(UTC)


def bst_isoformat(dt: datetime = None) -> str:
    """Return BST ISO 8601 string for audit logs and API responses."""
    if dt is None:
        dt = now_bst()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC).astimezone(BST)
    else:
        dt = dt.astimezone(BST)
    return dt.isoformat()


def bst_display(dt: datetime = None) -> str:
    """Human-readable BST timestamp for reports."""
    if dt is None:
        dt = now_bst()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC).astimezone(BST)
    else:
        dt = dt.astimezone(BST)
    return dt.strftime("%d %b %Y %I:%M %p BST")
