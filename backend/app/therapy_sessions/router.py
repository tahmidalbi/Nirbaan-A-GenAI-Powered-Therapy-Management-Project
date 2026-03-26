from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List
from datetime import datetime, timezone

from app.database.deps import get_db
from app.auth.utils import get_current_patient, get_current_therapist
from app.schemas.therapy_session import (
    SessionStart,
    TranscriptAppend,
    SessionResponse,
    TranscriptResponse,
    SessionAnalysisResponse
)
from app.therapy_sessions.models import TherapySession, TherapyTranscript, TherapySessionAnalysis
from app.therapy_sessions.schemas import (
    TherapySessionCreate,
    TherapySessionUpdate,
    TherapySessionTherapistResponse,
    TherapySessionPatientResponse,
)
from app.therapists.models import Therapist
from app.patients.models import Patient
from app.therapy_sessions.transcription_service import transcription_service
from app.therapy_sessions.analysis_service import generate_session_analysis

router = APIRouter(prefix="/api/therapy-sessions", tags=["therapy-sessions"])


# ══════════════════════════════════════════════════════════════════════════════
# VIDEO SESSION ENDPOINTS (Real-time transcription)
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/video/start", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def start_video_session(
    session_data: SessionStart,
    db: Session = Depends(get_db)
):
    """
    Start a new video therapy session.

    Creates a new therapy session with the specified therapist and patient.
    The session is automatically timestamped with started_at.
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

    # Verify patient is assigned to this therapist
    if patient.therapist_id != session_data.therapist_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient is not assigned to this therapist"
        )

    # Create new video session
    new_session = TherapySession(
        therapist_id=session_data.therapist_id,
        patient_id=session_data.patient_id,
        session_type='video'
    )

    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return new_session


@router.post("/video/{session_id}/append-transcript", response_model=TranscriptResponse, status_code=status.HTTP_201_CREATED)
async def append_transcript(
    session_id: int,
    transcript_data: TranscriptAppend,
    db: Session = Depends(get_db)
):
    """
    Append a transcript entry to a video therapy session.

    Adds a new transcript entry with speaker label ("therapist" or "patient"),
    text content, and automatic timestamp.
    """
    # Verify session exists
    session = db.query(TherapySession).filter(TherapySession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found"
        )

    # Check if session has ended
    if session.ended_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot append transcript to an ended session"
        )

    # Create new transcript entry
    new_transcript = TherapyTranscript(
        session_id=session_id,
        speaker=transcript_data.speaker,
        text=transcript_data.text
    )

    db.add(new_transcript)
    db.commit()
    db.refresh(new_transcript)

    return new_transcript


@router.get("/video/{session_id}", response_model=SessionResponse)
async def get_video_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a video therapy session with full transcript.

    Returns the session details along with all transcript entries
    ordered by timestamp.
    """
    session = db.query(TherapySession).filter(TherapySession.id == session_id).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found"
        )

    return session


@router.get("/video/{session_id}/transcripts", response_model=List[TranscriptResponse])
async def get_transcripts(
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all transcript entries for a video session, ordered by timestamp.
    """
    session = db.query(TherapySession).filter(TherapySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Session {session_id} not found")
    return sorted(session.transcripts, key=lambda t: t.timestamp)


@router.post("/transcribe-audio")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form(None),
    session_id: int = Form(None),
    speaker: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    Transcribe audio using OpenAI Whisper API.

    Accepts multipart/form-data with:
      - audio: audio file (webm, wav, mp3, ...)
      - session_id: therapy session id (optional — saves to DB if provided)
      - speaker: "therapist" or "patient" (required when session_id given)
      - language: BCP-47 language code, e.g. "en" (optional)

    Returns { success, text, transcript_id }
    """
    if not transcription_service.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Transcription service unavailable: OPENAI_API_KEY not configured"
        )

    allowed_formats = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
    file_ext = audio.filename.split(".")[-1].lower() if audio.filename else "webm"

    if file_ext not in allowed_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format: {file_ext}. Allowed: {', '.join(allowed_formats)}"
        )

    try:
        # Read audio file
        audio_bytes = await audio.read()

        # Transcribe
        result = transcription_service.transcribe_audio_bytes(
            audio_bytes=audio_bytes,
            filename=audio.filename or "audio.webm",
            language=language
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Transcription failed: {result.get('error', 'Unknown error')}"
            )

        transcribed_text = result.get("text", "")

        # Optionally save to session
        transcript_entry = None
        if session_id and speaker and transcribed_text:
            # Verify session exists
            session = db.query(TherapySession).filter(TherapySession.id == session_id).first()
            if session:
                # Validate speaker
                if speaker not in ["therapist", "patient"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Speaker must be 'therapist' or 'patient'"
                    )

                # Save transcript
                transcript_entry = TherapyTranscript(
                    session_id=session_id,
                    speaker=speaker,
                    text=transcribed_text
                )
                db.add(transcript_entry)
                db.commit()
                db.refresh(transcript_entry)

        return {
            "success": True,
            "text": transcribed_text,
            "transcript_id": transcript_entry.id if transcript_entry else None
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing audio: {str(e)}"
        )


@router.post("/video/{session_id}/end", response_model=SessionResponse)
async def end_video_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    End a video therapy session.
    Sets ended_at timestamp and triggers AI analysis in the background.
    """
    session = db.query(TherapySession).filter(TherapySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.ended_at:
        raise HTTPException(status_code=400, detail="Session already ended")

    session.ended_at = func.now()
    db.commit()
    db.refresh(session)

    # Generate AI analysis (synchronous for now – could be Celery task)
    generate_session_analysis(session_id, db)
    db.refresh(session)

    return session


@router.get("/video/{session_id}/analysis", response_model=SessionAnalysisResponse)
async def get_session_analysis(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve the AI-generated analysis for a video session."""
    analysis = (
        db.query(TherapySessionAnalysis)
        .filter(TherapySessionAnalysis.session_id == session_id)
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found for this session")
    return analysis


@router.post("/video/{session_id}/analysis/generate", response_model=SessionAnalysisResponse)
async def trigger_session_analysis(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Manually trigger AI analysis for a video session (re-generates if exists)."""
    session = db.query(TherapySession).filter(TherapySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Delete existing analysis if any
    existing = (
        db.query(TherapySessionAnalysis)
        .filter(TherapySessionAnalysis.session_id == session_id)
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()

    analysis = generate_session_analysis(session_id, db)
    if not analysis:
        raise HTTPException(status_code=500, detail="Failed to generate analysis")
    return analysis


# ══════════════════════════════════════════════════════════════════════════════
# MANUAL SESSION ENDPOINTS (Logged by therapist)
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/",
    response_model=TherapySessionTherapistResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_manual_session(
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
        session_type='manual',
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
async def update_manual_session(
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


# ══════════════════════════════════════════════════════════════════════════════
# PATIENT ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

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
