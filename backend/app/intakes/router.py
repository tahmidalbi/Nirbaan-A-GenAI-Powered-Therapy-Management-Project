from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.deps import get_db
from app.auth.utils import get_current_user

from app.intakes.schemas import (
    PatientIntakeCreate,
    PatientIntakeUpdate,
    PatientIntakeResponse,
    PatientIntakeListItem,
    IntakeSubmitResponse,
)
from app.intakes.models import PatientIntake
from app.patients.models import Patient

from app.intakes.tasks import summarize_patient_intake_task


router = APIRouter(prefix="/api/intakes", tags=["intakes"])


@router.post("", response_model=IntakeSubmitResponse, status_code=status.HTTP_201_CREATED)
async def create_intake(
    intake_data: PatientIntakeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create a new patient intake (Patient only).
    Saves intake and triggers AI summarization asynchronously (Celery).
    """
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can create intake forms",
        )

    patient = current_user

    existing_intake = (
        db.query(PatientIntake)
        .filter(PatientIntake.patient_id == patient.id)
        .first()
    )

    if existing_intake:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Intake form already exists. Use update endpoint instead.",
        )

    intake = PatientIntake(
        patient_id=patient.id,
        therapist_id=patient.therapist_id,
        your_story=intake_data.your_story,
        when_started=intake_data.when_started,
        tried_previous_therapy=intake_data.tried_previous_therapy,
        previous_therapy_details=intake_data.previous_therapy_details,
        taken_medication=intake_data.taken_medication,
        medication_details=intake_data.medication_details,
        affected_life_areas=intake_data.affected_life_areas,
        other_conditions=intake_data.other_conditions,
        issues=[issue.model_dump() for issue in intake_data.issues],
        # AI summary initial state
        ai_summary_status="pending",
        ai_summary_text=None,
        ai_summary_structured=None,
        ai_summary_error=None,
        ai_summary_version=1,
        ai_summary_updated_at=None,
    )

    db.add(intake)
    db.commit()
    db.refresh(intake)

    # Trigger AI summarization in background
    summarize_patient_intake_task.delay(intake.id)

    return IntakeSubmitResponse(intake_id=intake.id, ai_summary_status=intake.ai_summary_status)


@router.get("/me", response_model=PatientIntakeResponse)
async def get_my_intake(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get current patient's intake form (includes AI summary fields)."""
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can access their intake",
        )

    patient = current_user

    intake = (
        db.query(PatientIntake)
        .filter(PatientIntake.patient_id == patient.id)
        .first()
    )

    if not intake:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intake form not found",
        )

    return intake


@router.put("/me", response_model=IntakeSubmitResponse)
async def update_my_intake(
    intake_data: PatientIntakeUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Update current patient's intake form.
    After updating, re-triggers AI summarization (Celery).
    """
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can update their intake",
        )

    patient = current_user

    intake = (
        db.query(PatientIntake)
        .filter(PatientIntake.patient_id == patient.id)
        .first()
    )

    if not intake:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intake form not found. Create one first.",
        )

    update_data = intake_data.model_dump(exclude_unset=True)

    if "issues" in update_data and update_data["issues"] is not None:
        update_data["issues"] = [issue.model_dump() for issue in intake_data.issues]

    for field, value in update_data.items():
        setattr(intake, field, value)

    # Reset AI summary fields (so UI shows pending/spinner)
    intake.ai_summary_status = "pending"
    intake.ai_summary_text = None
    intake.ai_summary_structured = None
    intake.ai_summary_error = None
    intake.ai_summary_version = int(intake.ai_summary_version or 1)  # keep same version unless you bump manually
    intake.ai_summary_updated_at = None

    db.commit()
    db.refresh(intake)

    # Re-trigger AI summary
    summarize_patient_intake_task.delay(intake.id)

    return IntakeSubmitResponse(intake_id=intake.id, ai_summary_status=intake.ai_summary_status)


@router.post("/me/retry-summary", response_model=IntakeSubmitResponse)
async def retry_my_intake_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Retry AI summary for current patient's intake (Patient only).
    Useful if ai_summary_status == failed.
    """
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can retry their intake summary",
        )

    patient = current_user

    intake = (
        db.query(PatientIntake)
        .filter(PatientIntake.patient_id == patient.id)
        .first()
    )

    if not intake:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intake form not found",
        )

    intake.ai_summary_status = "pending"
    intake.ai_summary_text = None
    intake.ai_summary_structured = None
    intake.ai_summary_error = None
    intake.ai_summary_updated_at = None

    db.commit()
    db.refresh(intake)

    summarize_patient_intake_task.delay(intake.id)

    return IntakeSubmitResponse(intake_id=intake.id, ai_summary_status=intake.ai_summary_status)


@router.get("/patient/{patient_id}", response_model=PatientIntakeResponse)
async def get_patient_intake(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get intake for a specific patient (Therapist only)."""
    if current_user.role != "therapist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only therapists can view patient intakes",
        )

    therapist = current_user

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    if patient.therapist_id != therapist.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view intakes for your own patients",
        )

    intake = (
        db.query(PatientIntake)
        .filter(PatientIntake.patient_id == patient_id)
        .first()
    )

    if not intake:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intake form not found for this patient",
        )

    return intake


@router.post("/patient/{patient_id}/retry-summary", response_model=IntakeSubmitResponse)
async def retry_patient_intake_summary(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Retry AI summary for a specific patient's intake (Therapist only, own patient).
    """
    if current_user.role != "therapist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only therapists can retry patient intake summaries",
        )

    therapist = current_user

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if patient.therapist_id != therapist.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only retry summaries for your own patients",
        )

    intake = (
        db.query(PatientIntake)
        .filter(PatientIntake.patient_id == patient_id)
        .first()
    )

    if not intake:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intake form not found for this patient",
        )

    intake.ai_summary_status = "pending"
    intake.ai_summary_text = None
    intake.ai_summary_structured = None
    intake.ai_summary_error = None
    intake.ai_summary_updated_at = None

    db.commit()
    db.refresh(intake)

    # pass therapist id for extra safety in the task
    summarize_patient_intake_task.delay(intake.id, requested_by_therapist_id=therapist.id)

    return IntakeSubmitResponse(intake_id=intake.id, ai_summary_status=intake.ai_summary_status)


@router.get("/my-patients", response_model=List[PatientIntakeListItem])
async def get_my_patients_intakes(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all intakes for therapist's patients (Therapist only)."""
    if current_user.role != "therapist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only therapists can access this endpoint",
        )

    therapist = current_user

    intakes = (
        db.query(PatientIntake)
        .filter(PatientIntake.therapist_id == therapist.id)
        .order_by(PatientIntake.updated_at.desc())
        .all()
    )

    return intakes
