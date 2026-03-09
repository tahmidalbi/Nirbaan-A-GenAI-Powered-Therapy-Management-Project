from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.deps import get_db
from app.auth.utils import get_current_patient, get_current_therapist
from app.therapy_sessions.models import TherapySession
from app.therapy_sessions.schemas import (
    TherapySessionCreate,
    TherapySessionUpdate,
    TherapySessionTherapistResponse,
    TherapySessionPatientResponse,
)
from app.patients.models import Patient

router = APIRouter(prefix="/api/therapy-sessions", tags=["therapy-sessions"])


# ──────────────────────────────────────────────────────────────────────────────
# THERAPIST ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=TherapySessionTherapistResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    data: TherapySessionCreate,
    db: Session = Depends(get_db),
    current_therapist=Depends(get_current_therapist),
):
    """Therapist logs a therapy session transcript for one of their patients."""
    # Ensure the patient belongs to this therapist
    patient = (
        db.query(Patient)
        .filter(
            Patient.id == data.patient_id,
            Patient.therapist_id == current_therapist.id,
        )
        .first()
    )
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found or does not belong to you",
        )

    # Auto-calculate session number (how many sessions already exist for this patient + 1)
    existing_count = (
        db.query(TherapySession)
        .filter(TherapySession.patient_id == data.patient_id)
        .count()
    )

    new_session = TherapySession(
        patient_id=data.patient_id,
        therapist_id=current_therapist.id,
        session_date=data.session_date,
        session_number=existing_count + 1,
        title=data.title,
        transcript=data.transcript,
        therapist_notes=data.therapist_notes,
    )

    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


@router.get(
    "/patient/{patient_id}",
    response_model=List[TherapySessionTherapistResponse],
)
async def get_patient_sessions_therapist(
    patient_id: int,
    db: Session = Depends(get_db),
    current_therapist=Depends(get_current_therapist),
):
    """Get all therapy sessions for a specific patient (therapist view, includes notes)."""
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
            detail="Patient not found or does not belong to you",
        )

    sessions = (
        db.query(TherapySession)
        .filter(TherapySession.patient_id == patient_id)
        .order_by(TherapySession.session_number.desc())
        .all()
    )
    return sessions


@router.put(
    "/{session_id}",
    response_model=TherapySessionTherapistResponse,
)
async def update_session(
    session_id: int,
    data: TherapySessionUpdate,
    db: Session = Depends(get_db),
    current_therapist=Depends(get_current_therapist),
):
    """Therapist edits an existing therapy session."""
    session = (
        db.query(TherapySession)
        .filter(
            TherapySession.id == session_id,
            TherapySession.therapist_id == current_therapist.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if data.session_date is not None:
        session.session_date = data.session_date
    if data.title is not None:
        session.title = data.title
    if data.transcript is not None:
        session.transcript = data.transcript
    if data.therapist_notes is not None:
        session.therapist_notes = data.therapist_notes

    db.commit()
    db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_therapist=Depends(get_current_therapist),
):
    """Therapist deletes a therapy session."""
    session = (
        db.query(TherapySession)
        .filter(
            TherapySession.id == session_id,
            TherapySession.therapist_id == current_therapist.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    db.delete(session)
    db.commit()


# ──────────────────────────────────────────────────────────────────────────────
# PATIENT ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/my-sessions",
    response_model=List[TherapySessionPatientResponse],
)
async def get_my_sessions(
    db: Session = Depends(get_db),
    current_patient=Depends(get_current_patient),
):
    """Patient retrieves their own therapy session transcripts (therapist notes hidden)."""
    sessions = (
        db.query(TherapySession)
        .filter(TherapySession.patient_id == current_patient.id)
        .order_by(TherapySession.session_number.desc())
        .all()
    )
    return sessions
