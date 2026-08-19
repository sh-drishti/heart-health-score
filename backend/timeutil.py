"""
Timestamp formatting shared by the Mongo-backed modules.

Kept in one place because the reason for it is subtle: pymongo returns naive
datetimes, and `str()` on one yields a space-separated string that JavaScript
parses as *local* time. Every endpoint that returns a stored timestamp has to
format it the same way, or a displayed time shifts between saving and
reloading.
"""

from datetime import datetime, timezone
from typing import Any


def iso_utc(value: Any) -> str:
    """Format a stored timestamp as ISO-8601 UTC. Non-datetimes pass through."""

    if isinstance(value, datetime):
        aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return aware.isoformat()
    return str(value or "")
