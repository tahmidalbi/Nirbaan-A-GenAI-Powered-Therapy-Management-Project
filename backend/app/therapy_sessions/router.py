from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.deps import get_db
from app.schemas.therapy_session import (
    AppendTranscriptRequest,
    TherapySessionResponse,
    TherapySessionCreate,
    TranscriptEntry
)
from app.therapy_sessions.models import TherapySession
from app.patients.models import Patient
from app.therapists.models import Therapist

router = APIRouter(prefix="/sessions", tags=["Therapy Sessions"])

@router.post("/", response_model=TherapySessionResponse, status_code=status.HTTP_201_CREATED)
async def create_therapy_session(
    session_data: TherapySessionCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new therapy session
    
    Required fields:
    - therapist_id: ID of the therapist
    - patient_id: ID of the patient
    """
    # Verify therapist exists
    therapist = db.query(Therapist).filter(Therapist.id == session_data.therapist_id).first()
    if not therapist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Therapist with id {session_data.therapist_id} not found"
        )
    
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.id == session_data.patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with id {session_data.patient_id} not found"
        )
    
    # Create new therapy session
    new_session = TherapySession(
        therapist_id=session_data.therapist_id,
        patient_id=session_data.patient_id,
        transcript=[]
    )
    
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    return new_session

@router.post("/{session_id}/append-transcript", response_model=TherapySessionResponse)
async def append_transcript(
    session_id: int,
    request: AppendTranscriptRequest,
    db: Session = Depends(get_db)
):
    """
    Append a transcript entry to an existing therapy session
    
    Parameters:
    - session_id: ID of the therapy session
    - transcript_entry: Object containing speaker, text, emotion, and timestamp
    
    Returns the updated therapy session with the new transcript entry appended
    """
    # Fetch the therapy session
    session = db.query(TherapySession).filter(TherapySession.id == session_id).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Therapy session with id {session_id} not found"
        )
    
    # Convert the transcript entry to dict
    transcript_entry_dict = request.transcript_entry.model_dump(mode='json')
    
    # Append the new entry to the transcript list
    if session.transcript is None:
        session.transcript = []
    
    # Create a copy of the list and append
    current_transcript = list(session.transcript)
    current_transcript.append(transcript_entry_dict)
    session.transcript = current_transcript
    
    # Mark the column as modified to trigger update
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(session, "transcript")
    
    # Commit to database
    db.commit()
    db.refresh(session)
    
    return session

@router.get("/{session_id}", response_model=TherapySessionResponse)
async def get_therapy_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a therapy session by ID
    """
    session = db.query(TherapySession).filter(TherapySession.id == session_id).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Therapy session with id {session_id} not found"
        )
    
    return session

@router.get("/", response_model=List[TherapySessionResponse])
async def list_therapy_sessions(
    therapist_id: int = None,
    patient_id: int = None,
    db: Session = Depends(get_db)
):
    """
    List therapy sessions with optional filtering
    
    Query parameters:
    - therapist_id: Filter by therapist ID
    - patient_id: Filter by patient ID
    """
    query = db.query(TherapySession)
    
    if therapist_id:
        query = query.filter(TherapySession.therapist_id == therapist_id)
    
    if patient_id:
        query = query.filter(TherapySession.patient_id == patient_id)
    
    sessions = query.all()
    return sessions
