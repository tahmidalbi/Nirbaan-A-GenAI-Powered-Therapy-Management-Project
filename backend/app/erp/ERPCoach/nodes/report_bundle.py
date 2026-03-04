# app/erp/ERPCoach/nodes/report_bundle.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.erp.ERPCoach.utils.summarization import safe_text_clip
from app.erp.ERPCoach.utils.transcript import format_transcript_block


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

    report_inputs = {
        "obsession": state.get("obsession", "") or "",
        "compulsions": state.get("compulsions", []) or [],
        "exercise_text": safe_text_clip(state.get("exercise_text"), max_chars=1200),
        "transcript_block": state.get("transcript_block", "") or "",
        "suds_points_block": suds_points_block,
        "patient_debrief_text": patient_debrief_text,
        "prior_summaries": state.get("prior_summaries", []) or [],
        "elapsed_seconds": float(state.get("elapsed_seconds", 0.0)),
        "suds_peak": state.get("suds_peak"),
        "suds_latest": state.get("suds_latest"),
    }

    state["suds_points_block"] = suds_points_block
    state["clipped_debrief_text"] = patient_debrief_text
    state["report_inputs"] = report_inputs
    return state