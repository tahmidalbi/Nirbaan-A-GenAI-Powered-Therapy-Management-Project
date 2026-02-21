# app/ai_ladder_review/tasks.py
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from celery import Task
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.database.session import SessionLocal

from app.ai_ladder_review.data_loader import (
    ladder_text as build_ladder_text,
    load_intake,
    load_ladder_items,
    load_last_7_days_logs,
    normalize_payload,
)
from app.ai_ladder_review.service import AILadderReviewService
from app.ai_ladder_review import repo as review_repo

from app.fear_ladder.models import (
    AILadderReview,
    AILadderReviewStatus,
    FearLadder,
)
# Import related models so SQLAlchemy metadata knows about foreign key tables
from app.patients.models import Patient
from app.therapists.models import Therapist

DEFAULT_MODEL = os.getenv("LLM_MODEL", "gpt-5.2")


def _utcnow() -> datetime:
    return datetime.utcnow()


@celery_app.task(bind=True, name="detect_missing_ocd_structures_task")
def detect_missing_ocd_structures_task(
    self: Task,
    review_id: int,
    *,
    requested_by_therapist_id: Optional[int] = None,
):
    """
    Background task:
      - Read AILadderReview from DB
      - Load intake + last 7 days logs + ladder items
      - Run 2 LLM calls (extract -> compare)
      - Persist missing obsession+compulsion suggestions with evidence

    Status transitions:
      queued/running -> completed
      queued/running -> failed (error_message populated)
    """
    db: Session = SessionLocal()
    review: Optional[AILadderReview] = None

    try:
        # ---------------------------
        # Step 1: Fetch review row
        # ---------------------------
        review = (
            db.query(AILadderReview)
            .filter(AILadderReview.id == review_id)
            .first()
        )
        if not review:
            raise ValueError(f"AILadderReview {review_id} not found")

        # Optional security gate: ensure correct therapist owns this review
        if requested_by_therapist_id is not None and review.therapist_id != requested_by_therapist_id:
            raise PermissionError(
                f"Therapist mismatch: review.therapist_id={review.therapist_id} "
                f"requested_by_therapist_id={requested_by_therapist_id}"
            )

        # Idempotency: if completed and has suggestions, do nothing
        if review.status == AILadderReviewStatus.completed and (review.suggestions or []):
            return

        # ---------------------------
        # Step 2: Mark running
        # ---------------------------
        review_repo.set_review_status(
            db,
            review,
            AILadderReviewStatus.running,
            error_message=None,
            model_name=DEFAULT_MODEL,
        )

        # ---------------------------
        # Step 3: Validate ladder ownership matches review (extra safety)
        # ---------------------------
        ladder = db.query(FearLadder).filter(FearLadder.id == review.ladder_id).first()
        if not ladder:
            raise ValueError(f"FearLadder {review.ladder_id} not found")
        if ladder.patient_id != review.patient_id:
            raise PermissionError(
                f"Ladder patient mismatch: ladder.patient_id={ladder.patient_id} review.patient_id={review.patient_id}"
            )

        # ---------------------------
        # Step 4: Load data
        # ---------------------------
        intake = load_intake(db, patient_id=review.patient_id)
        logs = load_last_7_days_logs(db, patient_id=review.patient_id)
        items = load_ladder_items(db, ladder_id=review.ladder_id)

        payload = normalize_payload(intake=intake, log_entries=logs)
        ladder_text = build_ladder_text(items)

        # ---------------------------
        # Step 5: Run AI service (2 calls)
        # ---------------------------
        service = AILadderReviewService()
        missing_structures = service.run_review(payload=payload, ladder_text=ladder_text)

        # ---------------------------
        # Step 6: Persist results
        # ---------------------------
        for s in missing_structures:
            compulsion_summary = "; ".join([c.strip() for c in s.compulsions if c and c.strip()]) or "Unknown"

            suggestion = review_repo.create_suggestion(
                db,
                review_id=review.id,
                obsession_label=s.obsession,
                compulsion_summary=compulsion_summary,
                rationale=s.rationale,
            )

            for ev in s.evidence:
                review_repo.create_evidence(
                    db,
                    suggestion_id=suggestion.id,
                    evidence=ev,
                )

        # ---------------------------
        # Step 7: Mark completed
        # ---------------------------
        review_repo.set_review_status(
            db,
            review,
            AILadderReviewStatus.completed,
            error_message=None,
            model_name=DEFAULT_MODEL,
        )

    except Exception as e:
        # ---------------------------
        # Error handling + persistence
        # ---------------------------
        error_msg = str(e)

        try:
            if review is None:
                review = (
                    db.query(AILadderReview)
                    .filter(AILadderReview.id == review_id)
                    .first()
                )
            if review:
                review_repo.set_review_status(
                    db,
                    review,
                    AILadderReviewStatus.failed,
                    error_message=error_msg,
                    model_name=DEFAULT_MODEL,
                )
        except Exception:
            pass

        raise

    finally:
        db.close()