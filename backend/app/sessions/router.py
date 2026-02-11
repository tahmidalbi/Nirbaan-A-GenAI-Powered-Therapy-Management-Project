"""
Session Router - API endpoints for therapy session transcripts
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from typing import List

from app.database.deps import get_db
from app.auth.utils import get_current_user
from app.sessions.models import TherapySession
from app.sessions.schemas import SessionCreate, SessionUpdate, SessionResponse, SessionListItem, PatientSessionData
from app.patients.models import Patient
from app.therapists.models import Therapist

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/create", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new therapy session transcript
    Only therapists can create sessions
    """
    if current_user["user_type"] != "therapist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only therapists can create sessions"
        )
    
    therapist_id = current_user["user_id"]
    
    # Check if patient exists
    patient = db.execute(select(Patient).where(Patient.id == session_data.patient_id)).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    # Check if session for this week already exists
    existing_session = db.execute(
        select(TherapySession).where(
            TherapySession.patient_id == session_data.patient_id,
            TherapySession.week_number == session_data.week_number
        )
    ).scalar_one_or_none()
    
    if existing_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session for Week {session_data.week_number} already exists"
        )
    
    # Create new session
    new_session = TherapySession(
        patient_id=session_data.patient_id,
        therapist_id=therapist_id,
        week_number=session_data.week_number,
        transcript=session_data.transcript,
        session_date=session_data.session_date or datetime.utcnow()
    )
    
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    return new_session


@router.get("/my-sessions", response_model=List[SessionResponse])
async def get_my_sessions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all sessions for the current patient
    """
    if current_user["user_type"] != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can access this endpoint"
        )
    
    patient_id = current_user["user_id"]
    
    sessions = db.execute(
        select(TherapySession)
        .where(TherapySession.patient_id == patient_id)
        .order_by(TherapySession.week_number)
    ).scalars().all()
    
    return sessions


@router.get("/patient/{patient_id}", response_model=List[SessionResponse])
async def get_patient_sessions(
    patient_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all sessions for a specific patient
    Only therapists can access this
    """
    if current_user["user_type"] != "therapist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only therapists can access patient sessions"
        )
    
    # Check if patient exists
    patient = db.execute(select(Patient).where(Patient.id == patient_id)).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    sessions = db.execute(
        select(TherapySession)
        .where(TherapySession.patient_id == patient_id)
        .order_by(TherapySession.week_number)
    ).scalars().all()
    
    return sessions


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session_detail(
    session_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get specific session details
    Patients can only access their own sessions
    Therapists can access any session
    """
    session = db.execute(
        select(TherapySession).where(TherapySession.id == session_id)
    ).scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check permissions
    if current_user["user_type"] == "patient":
        if session.patient_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own sessions"
            )
    elif current_user["user_type"] != "therapist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized access"
        )
    
    return session


@router.put("/session/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: int,
    session_update: SessionUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing session transcript
    Only therapists can update sessions
    """
    if current_user["user_type"] != "therapist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only therapists can update sessions"
        )
    
    session = db.execute(
        select(TherapySession).where(TherapySession.id == session_id)
    ).scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Update transcript
    session.transcript = session_update.transcript
    session.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(session)
    
    return session


@router.get("/patients-with-sessions")
async def get_patients_with_sessions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all patients who have sessions (for therapist sidebar)
    Returns list of patients with their session counts
    """
    if current_user["user_type"] != "therapist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only therapists can access this endpoint"
        )
    
    therapist_id = current_user["user_id"]
    
    # Get all patients with their sessions
    patients = db.execute(select(Patient)).scalars().all()
    
    result = []
    for patient in patients:
        sessions = db.execute(
            select(TherapySession)
            .where(TherapySession.patient_id == patient.id)
            .order_by(TherapySession.week_number)
        ).scalars().all()
        
        if sessions:  # Only include patients who have sessions
            result.append({
                "patient_id": patient.id,
                "patient_name": patient.name,
                "patient_email": patient.email,
                "session_count": len(sessions),
                "conditions": patient.conditions or []
            })
    
    return result
