# app/erp/ERPCoach/nodes/load_context.py
from __future__ import annotations

from typing import Any, Dict

from app.erp.services.coach_storage import CoachStorage

from app.erp.ERPCoach.utils.transcript import format_transcript_block
from app.erp.ERPCoach.utils.summarization import (
    compute_suds_stats,
    compact_prior_session_summaries,
    safe_text_clip,
)
from app.erp.ERPCoach.utils.time import compute_elapsed_seconds, now_utc


def load_context_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Uses db/storage/llm already injected into state by invoke_erp_coach().
    Loads session bundle and writes context fields into state.

    IMPORTANT:
    - Do NOT create SessionLocal() here.
    - Do NOT close db here (invoke_erp_coach closes it).
    """
    storage: CoachStorage = state.get("storage")  # type: ignore[assignment]
    if storage is None:
        raise RuntimeError("storage missing from state. invoke_erp_coach must inject it.")

    session_id = int(state["session_id"])
    bundle = storage.get_session_bundle(
        session_id,
        message_limit=int(state.get("message_limit", 20)),
        suds_limit=int(state.get("suds_limit", 12)),
        prior_sessions_limit=int(state.get("prior_sessions_limit", 3)),
        include_transcript=True,
    )

    transcript_block = format_transcript_block(
        bundle.messages,
        max_messages=int(state.get("message_limit", 20)),
        max_chars_per_message=int(state.get("max_chars_per_message", 1200)),
    )

    prior_summaries = compact_prior_session_summaries(bundle.prior_sessions, limit=3)
    if bundle.prior_session_summaries:
        # Optional safety clip if you fear it can grow
        prior_summaries = bundle.prior_session_summaries

    suds_stats = compute_suds_stats(bundle.suds_recent)

    elapsed = compute_elapsed_seconds(
        status=bundle.session.status,
        accumulated_seconds=float(bundle.session.accumulated_seconds or 0.0),
        resumed_at=bundle.session.resumed_at,
        now=now_utc(),
    )

    exercise_text = safe_text_clip(bundle.exercise_text, max_chars=1200)

    last_patient_message_at = storage.get_last_patient_message_at(session_id)
    last_spike_notified_suds = getattr(bundle.session, "last_spike_notified_suds", None)

    state.update(
        {
            "session": bundle.session,
            "item": bundle.item,
            "erp_item_id": bundle.item.id,
            "patient_id": bundle.session.patient_id,
            "obsession": bundle.obsession,
            "compulsions": bundle.compulsions or [],
            "exercise_text": exercise_text,
            "messages_tail": bundle.messages,
            "transcript_block": transcript_block,
            "suds_recent": bundle.suds_recent,
            "suds_stats": suds_stats,
            "suds_peak": bundle.suds_peak,
            "last_suds_at": bundle.last_suds_at,
            "latest_report_session": bundle.latest_report_session,
            "prior_sessions": bundle.prior_sessions,
            "prior_summaries": prior_summaries,
            "elapsed_seconds": float(elapsed),
            "last_patient_message_at": last_patient_message_at,
            "last_spike_notified_suds": last_spike_notified_suds,
        }
    )
    return state