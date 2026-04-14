# ai_ladder_review_v2/ladder_review_agent/nodes/finalizer.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from ..state import LadderReviewState

from app.fear_ladder.models import (
    AILadderReview,
    AILadderReviewStatus,
    AILadderSuggestion,
    AILadderEvidence,
)


def _evidence_to_rows(
    suggestion_id: int,
    ev_list: List[Dict[str, Any]],
) -> List[AILadderEvidence]:
    rows: List[AILadderEvidence] = []
    for ev in ev_list or []:
        # We designed log lines like [E123] so source_id can be entry id (int).
        source_type = ev.get("source_type") or "daily_log"
        source_id_raw = ev.get("source_id") or "0"
        try:
            source_id = int(str(source_id_raw).replace("E", "").strip())
        except Exception:
            source_id = 0

        # source_date in schema is "YYYY-MM-DD"; DB expects DateTime nullable
        source_date = None
        try:
            sd = ev.get("source_date")
            if sd:
                source_date = datetime.fromisoformat(sd)
        except Exception:
            source_date = None

        rows.append(
            AILadderEvidence(
                suggestion_id=suggestion_id,
                source_type=source_type,
                source_id=source_id,
                source_date=source_date,
                field_name=ev.get("field_name"),
                quote_text=ev.get("quote_text") or "",
            )
        )
    return rows


def finalizer_node(db: Session, state: LadderReviewState) -> LadderReviewState:
    """
    NO LLM.
    Persists:
      - AILadderSuggestion rows for missing candidates
      - AILadderEvidence rows for each suggestion

    Also updates AILadderReview.status to completed.
    """
    if not state.review_id:
        raise RuntimeError("state.review_id missing")

    review: Optional[AILadderReview] = db.get(AILadderReview, int(state.review_id))
    if not review:
        raise RuntimeError(f"AILadderReview not found id={state.review_id}")

    missing_set = set(state.missing_ids or [])
    missing_candidates = [c for c in (state.candidates_all or []) if c.get("id") in missing_set]

    # Clear old suggestions for this review (optional: only if you want idempotent reruns)
    # If you don't want auto-delete, remove this block.
    for s in list(review.suggestions or []):
        db.delete(s)
    db.flush()

    created_suggestions = 0
    for cand in missing_candidates:
        obsession_label = (cand.get("obsession") or "").strip()
        compulsions = cand.get("compulsions") or []
        compulsion_summary = "; ".join([str(x).strip() for x in compulsions if str(x).strip()]) or "UNKNOWN / NOT STATED"

        rationale = (cand.get("label") or "").strip()
        if cand.get("potential_pattern"):
            rationale = (rationale + " (Potential pattern; compulsion unclear)").strip()

        sug = AILadderSuggestion(
            review_id=review.id,
            obsession_label=obsession_label or "UNKNOWN",
            compulsion_summary=compulsion_summary,
            rationale=rationale or "Extracted from intake/logs with evidence.",
        )
        db.add(sug)
        db.flush()  # to get sug.id

        ev_rows = _evidence_to_rows(sug.id, cand.get("evidence") or [])
        for ev in ev_rows:
            db.add(ev)

        created_suggestions += 1

    review.status = AILadderReviewStatus.completed
    review.model_name = review.model_name or "gpt-5.3"
    review.error_message = None

    db.commit()

    state.result_payload = {
        "review_id": review.id,
        "status": str(review.status),
        "missing_count": created_suggestions,
    }

    state.log_trace("finalizer", {"created_suggestions": created_suggestions})
    return state