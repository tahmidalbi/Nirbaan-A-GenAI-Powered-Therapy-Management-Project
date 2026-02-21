# app/ai_ladder_review/repo.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.fear_ladder.models import (
    AILadderEvidence,
    AILadderReview,
    AILadderReviewStatus,
    AILadderSuggestion,
)
from app.ai_ladder_review.llm_schemas import EvidenceItem


def _utcnow() -> datetime:
    return datetime.utcnow()


def set_review_status(
    db: Session,
    review: AILadderReview,
    status: AILadderReviewStatus,
    *,
    error_message: Optional[str] = None,
    model_name: Optional[str] = None,
) -> None:
    review.status = status
    if model_name is not None:
        review.model_name = model_name
    review.error_message = error_message
    review.updated_at = _utcnow()
    db.add(review)
    db.commit()
    db.refresh(review)


def create_suggestion(
    db: Session,
    *,
    review_id: int,
    obsession_label: str,
    compulsion_summary: str,
    rationale: str,
) -> AILadderSuggestion:
    s = AILadderSuggestion(
        review_id=review_id,
        obsession_label=obsession_label,
        compulsion_summary=compulsion_summary,
        rationale=rationale,
        created_at=_utcnow(),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def create_evidence(
    db: Session,
    *,
    suggestion_id: int,
    evidence: EvidenceItem,
) -> AILadderEvidence:
    # Model stores source_date as DateTime; LLM gives "YYYY-MM-DD" or null.
    source_date_dt = None
    if evidence.date:
        try:
            # Store midnight UTC of that date for consistency
            source_date_dt = datetime.fromisoformat(evidence.date)
        except Exception:
            source_date_dt = None

    # Your DB model uses Integer for source_id; LLM schema uses str.
    # We try to coerce. If it fails, store 0 (still keeps quote for therapist).
    try:
        source_id_int = int(evidence.source_id)
    except Exception:
        source_id_int = 0

    row = AILadderEvidence(
        suggestion_id=suggestion_id,
        source_type=evidence.source_type,
        source_id=source_id_int,
        source_date=source_date_dt,
        field_name=evidence.field_name,
        quote_text=evidence.quote_text,
        created_at=_utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row