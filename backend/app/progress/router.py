from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.deps import get_db
from app.auth.utils import get_current_patient, get_current_therapist
from app.progress.models import WeeklyProgress
from app.progress.schemas import WeeklyProgressCreate, WeeklyProgressResponse
from app.patients.models import Patient

router = APIRouter(prefix="/api/progress", tags=["progress"])


# ==================== PATIENT ENDPOINTS ====================

@router.post("/", response_model=WeeklyProgressResponse, status_code=status.HTTP_201_CREATED)
async def create_weekly_progress(
    progress_data: WeeklyProgressCreate,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    """Patient submits a weekly progress update."""
    # Auto-calculate week number (how many updates has this patient submitted + 1)
    existing_count = (
        db.query(WeeklyProgress)
        .filter(WeeklyProgress.patient_id == current_patient.id)
        .count()
    )
    week_number = existing_count + 1

    suds_list = None
    if progress_data.suds_snapshot:
        suds_list = [item.model_dump() for item in progress_data.suds_snapshot]

    new_progress = WeeklyProgress(
        patient_id=current_patient.id,
        week_number=week_number,
        week_start_date=progress_data.week_start_date,
        detailed_progress=progress_data.detailed_progress,
        homework_reflection=progress_data.homework_reflection,
        suds_snapshot=suds_list,
    )

    db.add(new_progress)
    db.commit()
    db.refresh(new_progress)

    return new_progress


@router.get("/my-progress", response_model=List[WeeklyProgressResponse])
async def get_my_progress(
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    """Get all weekly progress updates for the current patient."""
    updates = (
        db.query(WeeklyProgress)
        .filter(WeeklyProgress.patient_id == current_patient.id)
        .order_by(WeeklyProgress.week_number.desc())
        .all()
    )
    return updates


# ==================== THERAPIST ENDPOINTS ====================

@router.get("/patient/{patient_id}", response_model=List[WeeklyProgressResponse])
async def get_patient_progress(
    patient_id: int,
    db: Session = Depends(get_db),
    current_therapist=Depends(get_current_therapist),
):
    """Get all weekly progress updates for a specific patient (Therapist only)."""
    # Verify patient belongs to this therapist
    patient = (
        db.query(Patient)
        .filter(
            Patient.id == patient_id,
            Patient.therapist_id == current_therapist.id,
        )
        .first()
    )

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found or not assigned to you",
        )

    updates = (
        db.query(WeeklyProgress)
        .filter(WeeklyProgress.patient_id == patient_id)
        .order_by(WeeklyProgress.week_number.desc())
        .all()
    )
    return updates
