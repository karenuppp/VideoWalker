"""Timezone helpers (统一使用东八区)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

TZ = timezone(timedelta(hours=8))


def now() -> datetime:
    """Return current time in UTC+8."""
    return datetime.now(TZ)


def today_date():
    return now().date()


def ensure_tz(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime is timezone-aware in UTC+8."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)
