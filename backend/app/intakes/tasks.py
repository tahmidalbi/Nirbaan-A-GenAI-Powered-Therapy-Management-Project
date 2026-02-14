from __future__ import annotations

from datetime import datetime
from typing import Optional

from celery import Task
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.database.session import SessionLocal

from app.intakes.models import PatientIntake
from app.intakes.ai_summarizer import IntakeSummarizerAgent
# Import related models so SQLAlchemy metadata knows about foreign key tables
from app.patients.models import Patient
from app.therapists.models import Therapist


def _utcnow() -> datetime:
    return datetime.utcnow()


@celery_app.task(bind=True, name="summarize_patient_intake_task")
def summarize_patient_intake_task(
    self: Task,
    intake_id: int,
    *,
    requested_by_therapist_id: Optional[int] = None,
):
    """
    Background task:
      - Read PatientIntake from DB
      - Generate OCD-focused summary via IntakeSummarizerAgent
      - Store results back on the intake row

    Status transitions:
      pending/running -> done
      pending/running -> failed (ai_summary_error populated)

    Notes:
      - No DB access inside agent; DB read/write happens here
      - Errors are re-raised so Celery retry logic can apply
    """
    db: Session = SessionLocal()
    intake: Optional[PatientIntake] = None

    try:
        # ---------------------------
        # Step 1: Fetch intake row
        # ---------------------------
        intake = (
            db.query(PatientIntake)
            .filter(PatientIntake.id == intake_id)
            .first()
        )

        if not intake:
            raise ValueError(f"PatientIntake {intake_id} not found")

        # Optional security gate:
        # If caller provides therapist_id, ensure it's same therapist who owns this intake.
        if requested_by_therapist_id is not None and intake.therapist_id != requested_by_therapist_id:
            raise PermissionError(
                f"Therapist mismatch: intake.therapist_id={intake.therapist_id} "
                f"requested_by_therapist_id={requested_by_therapist_id}"
            )

        # Idempotency/efficiency:
        # If it's already done and you don't want auto-regeneration, just return.
        # Comment this out if you want to allow repeated regeneration.
        if intake.ai_summary_status == "done" and intake.ai_summary_text:
            return

        # Mark running
        intake.ai_summary_status = "running"
        intake.ai_summary_error = None
        db.add(intake)
        db.commit()
        db.refresh(intake)

        # ---------------------------
        # Step 2: Build payload for agent
        # ---------------------------
        intake_payload = {
            "your_story": intake.your_story,
            "when_started": intake.when_started,
            "tried_previous_therapy": intake.tried_previous_therapy,
            "previous_therapy_details": intake.previous_therapy_details,
            "taken_medication": intake.taken_medication,
            "medication_details": intake.medication_details,
            "affected_life_areas": intake.affected_life_areas,
            "other_conditions": intake.other_conditions,
            "issues": intake.issues,
        }

        # ---------------------------
        # Step 3: Run AI summarizer
        # ---------------------------
        agent = IntakeSummarizerAgent()
        summary_text, structured = agent.summarize(intake_payload)

        # ---------------------------
        # Step 4: Persist results
        # ---------------------------
        intake.ai_summary_text = summary_text
        intake.ai_summary_structured = structured
        intake.ai_summary_status = "done"
        intake.ai_summary_updated_at = _utcnow()
        intake.ai_summary_version = int(intake.ai_summary_version or 1)

        db.add(intake)
        db.commit()

    except Exception as e:
        # ---------------------------
        # Error handling + persistence
        # ---------------------------
        error_msg = str(e)

        try:
            if intake is None:
                intake = (
                    db.query(PatientIntake)
                    .filter(PatientIntake.id == intake_id)
                    .first()
                )

            if intake:
                intake.ai_summary_status = "failed"
                intake.ai_summary_error = error_msg
                intake.ai_summary_updated_at = _utcnow()
                db.add(intake)
                db.commit()
        except Exception:
            # Avoid masking the original error if DB write fails
            pass

        # Re-raise so Celery can retry if configured
        raise

    finally:
        db.close()
