# app/ai_ladder_review_v2/tasks.py
from __future__ import annotations

import os
from typing import Optional

from celery import Task

from app.core.celery_app import celery_app
from app.database.session import SessionLocal
from app.fear_ladder.models import AILadderReview, AILadderReviewStatus

# Import related models so SQLAlchemy knows all FK targets
from app.patients.models import Patient       # noqa: F401
from app.therapists.models import Therapist   # noqa: F401


@celery_app.task(bind=True, name="run_ladder_review_agent_v2_task")
def run_ladder_review_agent_v2_task(
    self: Task,
    review_id: int,
    *,
    requested_by_therapist_id: Optional[int] = None,
    taxonomy_version: str = "1.1",
    taxonomy_top_k: int = 6,
    max_entries_per_batch: int = 40,
):
    """
    Celery task: runs the LangGraph v2 ladder review agent for a given review_id.

    Status transitions:
      queued -> running -> completed
      queued -> running -> failed  (error_message set)

    This task is idempotent: if the review is already completed with suggestions,
    it exits immediately.
    """
    db = SessionLocal()
    review: Optional[AILadderReview] = None

    try:
        review = db.get(AILadderReview, review_id)
        if not review:
            raise ValueError(f"AILadderReview {review_id} not found")

        # Security: validate therapist ownership
        if (
            requested_by_therapist_id is not None
            and review.therapist_id != requested_by_therapist_id
        ):
            raise PermissionError(
                f"Therapist mismatch: review.therapist_id={review.therapist_id}, "
                f"requested={requested_by_therapist_id}"
            )

        # Idempotency: skip if already completed with suggestions
        if review.status == AILadderReviewStatus.completed and review.suggestions:
            return {"review_id": review_id, "status": "already_completed", "skipped": True}

        # Mark running
        review.status = AILadderReviewStatus.running
        review.error_message = None
        db.commit()
        db.close()

        # Run the agent (it opens its own session internally)
        from app.ai_ladder_review_v2.ladder_review_agent.graph import run_ladder_review_agent

        result = run_ladder_review_agent(
            db_session_factory=SessionLocal,
            review_id=review_id,
            taxonomy_version=taxonomy_version,
            taxonomy_top_k=taxonomy_top_k,
            max_entries_per_batch=max_entries_per_batch,
        )

        return result

    except Exception as exc:
        # Best-effort: mark review as failed using a fresh session
        try:
            _db = SessionLocal()
            r = _db.get(AILadderReview, review_id)
            if r:
                r.status = AILadderReviewStatus.failed
                r.error_message = str(exc)[:1000]
                _db.commit()
        except Exception:
            pass
        finally:
            try:
                _db.close()
            except Exception:
                pass
        raise

    finally:
        try:
            db.close()
        except Exception:
            pass
