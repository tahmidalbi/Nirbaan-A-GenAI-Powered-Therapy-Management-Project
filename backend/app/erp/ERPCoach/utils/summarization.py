# app/erp/ERPCoach/utils/summarization.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from app.erp.models import ERPLiveSession, ERPSUDSReading


@dataclass
class SudsStats:
    latest: Optional[int]
    previous: Optional[int]
    peak: Optional[int]
    delta: Optional[int]          # latest - previous
    slope_per_min: Optional[float]
    points: int


def compute_suds_stats(suds: Sequence[ERPSUDSReading]) -> SudsStats:
    """
    Deterministically compute useful SUDS stats from a chronological list of readings.
    This is used by compute_metrics node and by report bundle assembly.

    Expects suds in chronological order (oldest -> newest).
    """
    if not suds:
        return SudsStats(latest=None, previous=None, peak=None, delta=None, slope_per_min=None, points=0)

    vals = [int(s.suds_value) for s in suds]
    latest = vals[-1]
    previous = vals[-2] if len(vals) >= 2 else None
    peak = max(vals) if vals else None
    delta = (latest - previous) if previous is not None else None

    # slope: (latest - first) / minutes_elapsed_between_first_and_last
    first = suds[0]
    last = suds[-1]
    seconds = max(0.0, float(getattr(last, "elapsed_seconds", 0.0) - getattr(first, "elapsed_seconds", 0.0)))
    minutes = seconds / 60.0 if seconds > 0 else 0.0
    slope_per_min = None
    if minutes > 0:
        slope_per_min = float(latest - int(first.suds_value)) / minutes

    return SudsStats(
        latest=latest,
        previous=previous,
        peak=peak,
        delta=delta,
        slope_per_min=slope_per_min,
        points=len(vals),
    )


def compact_prior_session_summaries(prior_sessions: Sequence[ERPLiveSession], *, limit: int = 3) -> List[str]:
    """
    Creates short deterministic summaries from prior session rows.
    Uses stored report JSON if present; otherwise uses duration + ended_at.

    This avoids needing to send long transcripts from old sessions.
    """
    out: List[str] = []
    for s in list(prior_sessions)[:limit]:
        ended = s.ended_at.isoformat() if s.ended_at else "unknown_time"
        mins = int((s.accumulated_seconds or 0.0) // 60)

        # If therapist report exists, pull 1–2 key bullets (if available)
        rpt = getattr(s, "therapist_report_json", None) or {}
        what = rpt.get("what_happened") if isinstance(rpt, dict) else None
        key = rpt.get("key_learning") if isinstance(rpt, dict) else None

        bullets: List[str] = []
        if isinstance(what, list) and what:
            bullets.append(str(what[0])[:160])
        if isinstance(key, list) and key:
            bullets.append(str(key[0])[:160])

        if bullets:
            out.append(f"{ended} • {mins}m • " + " | ".join(bullets))
        else:
            out.append(f"{ended} • {mins}m")

    return out


def safe_text_clip(text: Optional[str], *, max_chars: int = 1000) -> Optional[str]:
    """
    Clip long free-text fields (like exercise note or debrief) so prompts stay small.
    """
    if text is None:
        return None
    t = text.strip()
    if len(t) <= max_chars:
        return t
    return t[:max_chars].rstrip() + "…"