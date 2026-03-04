# app/erp/ERPCoach/utils/time.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def now_utc() -> datetime:
    """
    Returns timezone-aware UTC now.
    Using tz-aware datetimes helps avoid subtle bugs.
    """
    return datetime.now(timezone.utc)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensures datetime is tz-aware in UTC.
    If dt is naive, assume it's UTC and attach tzinfo=UTC.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_elapsed_seconds(
    *,
    status: str,
    accumulated_seconds: float,
    resumed_at: Optional[datetime],
    now: Optional[datetime] = None,
) -> float:
    """
    Implements your timer model:
      - accumulated_seconds: total time from previous running segments
      - resumed_at: when current segment started (only meaningful if status == 'running')

    Returns the "current displayed elapsed seconds".
    """
    now_dt = ensure_utc(now) or now_utc()
    base = float(accumulated_seconds or 0.0)

    if status == "running" and resumed_at is not None:
        ra = ensure_utc(resumed_at)
        delta = (now_dt - ra).total_seconds()
        if delta < 0:
            delta = 0.0
        return base + float(delta)

    return base


def seconds_since(dt: Optional[datetime], *, now: Optional[datetime] = None) -> Optional[float]:
    """
    Returns seconds since dt. If dt is None, returns None.
    """
    if dt is None:
        return None
    now_dt = ensure_utc(now) or now_utc()
    dtu = ensure_utc(dt)
    return max(0.0, (now_dt - dtu).total_seconds())