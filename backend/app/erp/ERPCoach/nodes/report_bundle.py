# app/erp/ERPCoach/nodes/report_bundle.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import desc

from app.erp.ERPCoach.utils.summarization import safe_text_clip
from app.erp.ERPCoach.utils.transcript import format_transcript_block
from app.erp.models import ERPLiveSession


def format_session_report_block(rj: dict) -> str:
    """Format a single session's therapist_report_json dict into a readable text block."""
    parts = []

    overview = rj.get("session_overview", {})
    if overview:
        target = overview.get("exposure_target", "")
        peak = overview.get("peak_suds", "NA")
        end_suds = overview.get("end_suds", "NA")
        dur = overview.get("duration_minutes", "?")
        parts.append(f"Target: {target} | Peak SUDS: {peak} | End SUDS: {end_suds} | Duration: {dur}m")

    what_happened = rj.get("what_happened", []) or []
    if what_happened:
        parts.append("What happened: " + "; ".join(str(x) for x in what_happened[:4]))

    avoidance = rj.get("avoidance_or_safety_behaviors", []) or []
    if avoidance:
        parts.append("Avoidance/safety behaviors: " + "; ".join(str(x) for x in avoidance[:3]))

    compulsions = rj.get("compulsions_urges", []) or []
    if compulsions:
        parts.append("Compulsions/urges reported: " + "; ".join(str(x) for x in compulsions[:3]))

    rp = rj.get("response_prevention_successes", []) or []
    if rp:
        parts.append("Response prevention successes: " + "; ".join(str(x) for x in rp[:3]))

    kl = rj.get("key_learning", []) or []
    if kl:
        parts.append("Key learning: " + "; ".join(str(x) for x in kl[:2]))

    risk = rj.get("risk_flags", []) or []
    if risk:
        parts.append("Risk flags: " + "; ".join(str(x) for x in risk[:2]))

    return "\n".join(parts)


def build_prior_reports_block(prior_sessions: List[Any]) -> str:
    """
    Formats prior ended sessions' therapist_report_json into a readable text block
    for cross-session pattern analysis. Returns empty string if no prior sessions
    have reports.
    """
    if not prior_sessions:
        return ""

    blocks = []
    for i, s in enumerate(prior_sessions, 1):
        rj = getattr(s, "therapist_report_json", None) or {}
        if not rj:
            continue
        block = format_session_report_block(rj)
        if block:
            blocks.append(f"--- Prior Session {i} ---\n{block}")

    return "\n\n".join(blocks)


def assemble_report_bundle(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepares compact inputs for report generation.

    Expects (from load_context):
      - transcript_block (string)
      - suds_recent (list of ERPSUDSReading ORM)
      - prior_summaries (list of strings)
      - obsession, compulsions, exercise_text
      - elapsed_seconds, suds_peak, suds_latest

    Expects (for END_SESSION_REPORT):
      - patient_debrief_text (string)

    Produces:
      - suds_points_block: "elapsed -> value" lines
      - clipped_debrief_text
      - report_inputs: dict with everything needed for prompts
    """
    suds_recent = state.get("suds_recent", []) or []
    lines: List[str] = []
    for r in suds_recent:
        try:
            lines.append(f"{float(r.elapsed_seconds):.0f}s -> {int(r.suds_value)}")
        except Exception:
            continue
    suds_points_block = "\n".join(lines)

    patient_debrief_text = safe_text_clip(state.get("patient_debrief_text"), max_chars=2000) or ""

    # Fresh targeted query: only sessions that actually have a therapist report.
    # This avoids stale ORM objects from state AND sessions ended without a debrief.
    prior_reports_block = ""
    storage = state.get("storage")
    erp_item_id = state.get("erp_item_id")
    session_id = state.get("session_id")
    if storage and erp_item_id and session_id:
        sessions_with_reports = (
            storage.db.query(ERPLiveSession)
            .filter(
                ERPLiveSession.erp_item_id == int(erp_item_id),
                ERPLiveSession.status == "ended",
                ERPLiveSession.id != int(session_id),
                ERPLiveSession.therapist_report_json.isnot(None),
            )
            .order_by(desc(ERPLiveSession.ended_at))
            .limit(5)
            .all()
        )
        prior_reports_block = build_prior_reports_block(sessions_with_reports)

    report_inputs = {
        "obsession": state.get("obsession", "") or "",
        "compulsions": state.get("compulsions", []) or [],
        "exercise_text": safe_text_clip(state.get("exercise_text"), max_chars=1200),
        "transcript_block": state.get("transcript_block", "") or "",
        "suds_points_block": suds_points_block,
        "patient_debrief_text": patient_debrief_text,
        "prior_summaries": state.get("prior_summaries", []) or [],
        "prior_reports_block": prior_reports_block,
        "elapsed_seconds": float(state.get("elapsed_seconds", 0.0)),
        "suds_peak": state.get("suds_peak"),
        "suds_latest": state.get("suds_latest"),
    }

    state["suds_points_block"] = suds_points_block
    state["clipped_debrief_text"] = patient_debrief_text
    state["report_inputs"] = report_inputs
    return state