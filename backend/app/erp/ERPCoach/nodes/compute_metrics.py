# app/erp/ERPCoach/nodes/compute_metrics.py
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional

from app.erp.ERPCoach.utils.time import now_utc, seconds_since


def compute_metrics_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: compute_metrics

    Computes deterministic routing signals used by live_intent_router:
      - rate_reminder_flag: no SUDS rating for too long
      - spike_flag: SUDS rising fast or large jump
      - cooldown_ok: avoid spamming check-ins too frequently
      - suds_trend_hint: simple text hint for prompts

    Expects these fields already in state (from load_context):
      - session (ERPLiveSession ORM object)
      - suds_stats (SudsStats dataclass from utils.summarization)
      - last_suds_at
      - elapsed_seconds

    Produces:
      - rate_reminder_flag, spike_flag, cooldown_ok
      - suds_latest, suds_previous, suds_delta, suds_slope_per_min
      - suds_trend_hint
    """
    session = state["session"]
    suds_stats = state.get("suds_stats")

    # Thresholds (tweak anytime)
    # TODO: change reminder_seconds back to 300 (5 min) for production
    reminder_seconds = int(state.get("rate_reminder_seconds", 120))  # 2 minutes
    cooldown_seconds = int(state.get("checkin_cooldown_seconds", 100))  # 100 s
    spike_delta_threshold = int(state.get("spike_delta_threshold", 15))  # jump >= 15
    spike_slope_threshold = float(state.get("spike_slope_per_min_threshold", 8.0))  # >= 8 per min

    now = now_utc()

    # Time since last SUDS rating
    last_suds_at = state.get("last_suds_at") or getattr(session, "last_suds_at", None)
    since_last_suds = seconds_since(last_suds_at, now=now)

    rate_reminder_flag = False
    if since_last_suds is None:
        # If they never rated, remind after some elapsed time
        rate_reminder_flag = float(state.get("elapsed_seconds", 0.0)) >= float(reminder_seconds)
    else:
        rate_reminder_flag = since_last_suds >= float(reminder_seconds)

    # Cooldown for speaking (prevents multiple check-ins too close)
    last_agent_run_at = getattr(session, "last_agent_run_at", None)
    since_last_agent = seconds_since(last_agent_run_at, now=now)
    cooldown_ok = True
    if since_last_agent is not None and since_last_agent < float(cooldown_seconds):
        cooldown_ok = False

    # Spike detection (deterministic)
    suds_latest: Optional[int] = getattr(suds_stats, "latest", None) if suds_stats else None
    suds_previous: Optional[int] = getattr(suds_stats, "previous", None) if suds_stats else None
    suds_delta: Optional[int] = getattr(suds_stats, "delta", None) if suds_stats else None
    suds_slope_per_min: Optional[float] = getattr(suds_stats, "slope_per_min", None) if suds_stats else None

    spike_flag = False
    if suds_delta is not None and suds_delta >= spike_delta_threshold:
        spike_flag = True
    if suds_slope_per_min is not None and suds_slope_per_min >= spike_slope_threshold:
        spike_flag = True

    # Simple trend hint for prompt conditioning
    trend = "stable"
    if suds_delta is not None:
        if suds_delta >= 10:
            trend = "rising"
        elif suds_delta <= -10:
            trend = "falling"
        else:
            trend = "stable"
    suds_trend_hint = f"{trend} (delta={suds_delta if suds_delta is not None else 'NA'})"

    # Save computed metrics
    state.update(
        {
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
            # Useful for logging/debug
            "suds_stats_dict": asdict(suds_stats) if suds_stats else {},
        }
    )
    return state