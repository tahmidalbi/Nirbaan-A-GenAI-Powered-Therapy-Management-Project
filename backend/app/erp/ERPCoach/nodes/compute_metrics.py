# app/erp/ERPCoach/nodes/compute_metrics.py
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional

from app.erp.ERPCoach.utils.time import now_utc, seconds_since


def compute_metrics_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: compute_metrics

    Computes deterministic routing signals used by live_intent_router:
      - recently_engaged: patient sent a message OR rated SUDS within 5 minutes
        → when True, all auto check-ins are suppressed (NO_MESSAGE)
      - rate_reminder_flag: no SUDS rating for too long (only relevant when not engaged)
      - spike_flag: SUDS rising fast / large jump AND not already notified for this spike
      - cooldown_ok: avoid agent speaking too frequently
      - suds_trend_hint: simple text hint for prompts

    Expects these fields already in state (from load_context):
      - session (ERPLiveSession ORM object)
      - suds_stats (SudsStats dataclass from utils.summarization)
      - last_suds_at
      - last_patient_message_at
      - last_spike_notified_suds
      - elapsed_seconds
    """
    session = state["session"]
    suds_stats = state.get("suds_stats")

    # ── Thresholds ────────────────────────────────────────────────────────────
    # TODO: change reminder_seconds back to 300 (5 min) for production
    reminder_seconds = int(state.get("rate_reminder_seconds", 120))  # 2 minutes
    # Cooldown must be less than reminder_seconds so it doesn't block the next reminder.
    # Default: 60 s (half the reminder window) so the agent can't spam but reminders still fire.
    cooldown_seconds = int(state.get("checkin_cooldown_seconds", 60))
    spike_delta_threshold = int(state.get("spike_delta_threshold", 15))
    spike_slope_threshold = float(state.get("spike_slope_per_min_threshold", 8.0))
    # Engagement window: suppress non-reminder check-ins if patient engaged recently
    engagement_window = float(state.get("engagement_window_seconds", 300.0))  # 5 minutes

    now = now_utc()

    # ── SUDS timing ───────────────────────────────────────────────────────────
    last_suds_at = state.get("last_suds_at") or getattr(session, "last_suds_at", None)
    since_last_suds = seconds_since(last_suds_at, now=now)

    # ── Patient engagement check ──────────────────────────────────────────────
    # "Engaged" = patient sent a chat message OR rated SUDS in the last 5 minutes.
    # When engaged, the patient is actively participating → suppress all auto check-ins.
    last_patient_message_at = state.get("last_patient_message_at")
    since_last_patient_msg = seconds_since(last_patient_message_at, now=now)

    recently_engaged = (
        (since_last_patient_msg is not None and since_last_patient_msg < engagement_window)
        or
        (since_last_suds is not None and since_last_suds < engagement_window)
    )

    # ── Rate-reminder flag ────────────────────────────────────────────────────
    rate_reminder_flag = False
    if since_last_suds is None:
        rate_reminder_flag = float(state.get("elapsed_seconds", 0.0)) >= float(reminder_seconds)
    else:
        rate_reminder_flag = since_last_suds >= float(reminder_seconds)

    # ── Cooldown (avoids speaking too close to last agent message) ────────────
    last_agent_run_at = getattr(session, "last_agent_run_at", None)
    since_last_agent = seconds_since(last_agent_run_at, now=now)
    cooldown_ok = True
    if since_last_agent is not None and since_last_agent < float(cooldown_seconds):
        cooldown_ok = False

    # ── SUDS values ───────────────────────────────────────────────────────────
    suds_latest: Optional[int] = getattr(suds_stats, "latest", None) if suds_stats else None
    suds_previous: Optional[int] = getattr(suds_stats, "previous", None) if suds_stats else None
    suds_delta: Optional[int] = getattr(suds_stats, "delta", None) if suds_stats else None
    suds_slope_per_min: Optional[float] = getattr(suds_stats, "slope_per_min", None) if suds_stats else None

    # ── Spike detection with deduplication ───────────────────────────────────
    # Step 1: detect a raw spike from the latest readings
    raw_spike = False
    if suds_delta is not None and suds_delta >= spike_delta_threshold:
        raw_spike = True
    if suds_slope_per_min is not None and suds_slope_per_min >= spike_slope_threshold:
        raw_spike = True

    # Step 2: deduplicate — suppress if we already notified for this SUDS level.
    # A new spike notification is warranted only when suds_latest has risen above
    # the level we last notified about (i.e. a genuinely new / higher spike).
    spike_flag = False
    if raw_spike:
        last_spike_notified_suds = state.get("last_spike_notified_suds")
        if last_spike_notified_suds is None:
            # Never notified before → allow first spike message
            spike_flag = True
        elif suds_latest is not None and suds_latest > last_spike_notified_suds:
            # SUDS climbed higher than the last notification level → new spike
            spike_flag = True
        # else: same or lower SUDS than what we already notified → suppress

    # ── Trend hint ────────────────────────────────────────────────────────────
    trend = "stable"
    if suds_delta is not None:
        if suds_delta >= 10:
            trend = "rising"
        elif suds_delta <= -10:
            trend = "falling"
    suds_trend_hint = f"{trend} (delta={suds_delta if suds_delta is not None else 'NA'})"

    # ── Write all computed signals into state ─────────────────────────────────
    state.update(
        {
            "recently_engaged": bool(recently_engaged),
            "since_last_patient_msg_seconds": since_last_patient_msg,
            "rate_reminder_flag": bool(rate_reminder_flag),
            "spike_flag": bool(spike_flag),
            "cooldown_ok": bool(cooldown_ok),
            "since_last_suds_seconds": since_last_suds,
            "since_last_agent_seconds": since_last_agent,
            "suds_latest": suds_latest,
            "suds_previous": suds_previous,
            "suds_delta": suds_delta,
            "suds_slope_per_min": suds_slope_per_min,
            "suds_trend_hint": suds_trend_hint,
            "suds_stats_dict": asdict(suds_stats) if suds_stats else {},
        }
    )
    return state