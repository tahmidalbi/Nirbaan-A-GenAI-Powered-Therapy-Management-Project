from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.deps import get_db
from app.auth.utils import get_current_user

from app.self_monitoring.schemas import (
    SelfMonitoringDayCreate,
    SelfMonitoringDayResponse,
    SelfMonitoringDayListItem,
    SelfMonitoringEntryCreate,
    SelfMonitoringEntryResponse,
    PatientSelfMonitoringSummary,
)
from app.self_monitoring.models import SelfMonitoringDay, SelfMonitoringEntry
from app.patients.models import Patient
from app.therapists.models import Therapist


router = APIRouter(prefix="/api/self-monitoring", tags=["self-monitoring"])


# ==================== PATIENT ENDPOINTS ====================

@router.post("/days", response_model=SelfMonitoringDayResponse, status_code=status.HTTP_201_CREATED)
async def create_monitoring_day(
    day_data: SelfMonitoringDayCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new monitoring day (Patient only)."""
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can create monitoring days",
        )

    patient = current_user

    # Check if day number already exists for this patient
    existing_day = (
        db.query(SelfMonitoringDay)
        .filter(
            SelfMonitoringDay.patient_id == patient.id,
            SelfMonitoringDay.day_number == day_data.day_number
        )
        .first()
    )

    if existing_day:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Day {day_data.day_number} already exists",
        )

    new_day = SelfMonitoringDay(
        patient_id=patient.id,
        day_number=day_data.day_number,
    )

    db.add(new_day)
    db.commit()
    db.refresh(new_day)

    return new_day


@router.get("/days", response_model=List[SelfMonitoringDayResponse])
async def get_my_monitoring_days(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all monitoring days for current patient."""
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can access their monitoring days",
        )

    patient = current_user

    days = (
        db.query(SelfMonitoringDay)
        .filter(SelfMonitoringDay.patient_id == patient.id)
        .order_by(SelfMonitoringDay.day_number)
        .all()
    )

    return days


@router.get("/days/{day_id}", response_model=SelfMonitoringDayResponse)
async def get_monitoring_day(
    day_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get a specific monitoring day with all entries."""
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can access their monitoring days",
        )

    patient = current_user

    day = (
        db.query(SelfMonitoringDay)
        .filter(
            SelfMonitoringDay.id == day_id,
            SelfMonitoringDay.patient_id == patient.id
        )
        .first()
    )

    if not day:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring day not found",
        )

    return day


@router.post("/days/{day_id}/entries", response_model=SelfMonitoringEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_monitoring_entry(
    day_id: int,
    entry_data: SelfMonitoringEntryCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Add a new entry to a monitoring day (Patient only)."""
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can create monitoring entries",
        )

    patient = current_user

    # Verify day exists and belongs to current patient
    day = (
        db.query(SelfMonitoringDay)
        .filter(
            SelfMonitoringDay.id == day_id,
            SelfMonitoringDay.patient_id == patient.id
        )
        .first()
    )

    if not day:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring day not found",
        )

    new_entry = SelfMonitoringEntry(
        day_id=day_id,
        date=entry_data.date,
        time=entry_data.time,
        event=entry_data.event,
        ritual=entry_data.ritual,
        time_spent=entry_data.time_spent,
        anxiety_level=entry_data.anxiety_level,
    )

    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)

    return new_entry


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_monitoring_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete a monitoring entry (Patient only)."""
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can delete their entries",
        )

    patient = current_user

    # Find entry and verify ownership through day
    entry = (
        db.query(SelfMonitoringEntry)
        .join(SelfMonitoringDay)
        .filter(
            SelfMonitoringEntry.id == entry_id,
            SelfMonitoringDay.patient_id == patient.id
        )
        .first()
    )

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found",
        )

    db.delete(entry)
    db.commit()

    return None


# ==================== THERAPIST ENDPOINTS ====================

@router.get("/patients", response_model=List[PatientSelfMonitoringSummary])
async def get_all_patients_monitoring(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get monitoring summary for all patients (Therapist only)."""
    if current_user.role != "therapist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only therapists can access patient monitoring data",
        )

    therapist = current_user

    # Get all patients assigned to this therapist
    patients = (
        db.query(Patient)
        .filter(Patient.therapist_id == therapist.id)
        .all()
    )

    summaries = []
    for patient in patients:
        days = (
            db.query(SelfMonitoringDay)
            .filter(SelfMonitoringDay.patient_id == patient.id)
            .order_by(SelfMonitoringDay.day_number)
            .all()
        )

        # Count total entries
        total_entries = sum(len(day.entries) for day in days)

        # Create list items with entry count
        day_list_items = [
            SelfMonitoringDayListItem(
                id=day.id,
                patient_id=day.patient_id,
                day_number=day.day_number,
                entry_count=len(day.entries),
                created_at=day.created_at,
                updated_at=day.updated_at,
            )
            for day in days
        ]

        summaries.append(
            PatientSelfMonitoringSummary(
                patient_id=patient.id,
                patient_name=patient.name,
                total_days=len(days),
                total_entries=total_entries,
                days=day_list_items,
            )
        )

    return summaries


@router.get("/patients/{patient_id}/days", response_model=List[SelfMonitoringDayResponse])
async def get_patient_monitoring_days(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all monitoring days for a specific patient (Therapist only)."""
    if current_user.role != "therapist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only therapists can access patient monitoring data",
        )

    therapist = current_user

    # Verify patient belongs to this therapist
    patient = (
        db.query(Patient)
        .filter(
            Patient.id == patient_id,
            Patient.therapist_id == therapist.id
        )
        .first()
    )

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found or not assigned to you",
        )

    days = (
        db.query(SelfMonitoringDay)
        .filter(SelfMonitoringDay.patient_id == patient_id)
        .order_by(SelfMonitoringDay.day_number)
        .all()
    )

    return days


@router.get("/patients/{patient_id}/days/{day_id}", response_model=SelfMonitoringDayResponse)
async def get_patient_monitoring_day(
    patient_id: int,
    day_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get a specific monitoring day for a patient (Therapist only)."""
    if current_user.role != "therapist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only therapists can access patient monitoring data",
        )

    therapist = current_user

    # Verify patient belongs to this therapist
    patient = (
        db.query(Patient)
        .filter(
            Patient.id == patient_id,
            Patient.therapist_id == therapist.id
        )
        .first()
    )

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found or not assigned to you",
        )

    day = (
        db.query(SelfMonitoringDay)
        .filter(
            SelfMonitoringDay.id == day_id,
            SelfMonitoringDay.patient_id == patient_id
        )
        .first()
    )

    if not day:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring day not found",
        )

    return day
