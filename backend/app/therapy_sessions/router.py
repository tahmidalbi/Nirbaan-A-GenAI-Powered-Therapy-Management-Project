from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List, Optional
from datetime import datetime

from app.database.deps import get_db
from app.auth.utils import get_current_patient, get_current_therapist
from app.therapy_sessions.models import TherapySession, TherapyTranscript, TherapySessionAnalysis
from app.therapy_sessions.schemas import (
    TherapySessionCreate,
    TherapySessionUpdate,
    TherapySessionTherapistResponse,
    TherapySessionPatientResponse,
)
from app.patients.models import Patient
from app.therapists.models import Therapist

try:
    from app.therapy_sessions.transcription_service import transcription_service
    from app.therapy_sessions.analysis_service import generate_session_analysis
except ImportError:
    transcription_service = None
    generate_session_analysis = None

# Create two routers: one for manual/manual logging, one for videocall
router = APIRouter(tags=["therapy-sessions"])
manual_router = APIRouter(prefix="/api/therapy-sessions", tags=["therapy-sessions-manual"])
videocall_router = APIRouter(prefix="/sessions", tags=["therapy-sessions-videocall"])


# ──────────────────────────────────────────────────────────────────────────────
# MANUAL LOGGING ENDPOINTS (Plus sign UI)
# ──────────────────────────────────────────────────────────────────────────────

@manual_router.post(
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

    # Auto-calculate session number
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


@manual_router.get(
    "/patient/{patient_id}",
    response_model=List[TherapySessionTherapistResponse],
)
async def get_patient_sessions_therapist(
    patient_id: int,
    db: Session = Depends(get_db),
    current_therapist=Depends(get_current_therapist),
):
    """Get all therapy sessions for a specific patient (therapist view)."""
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


@manual_router.put(
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


@manual_router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
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


@manual_router.get(
    "/my-sessions",
    response_model=List[TherapySessionPatientResponse],
)
async def get_my_sessions(
    db: Session = Depends(get_db),
    current_patient=Depends(get_current_patient),
):
    """Patient retrieves their own therapy session transcripts."""
    sessions = (
        db.query(TherapySession)
        .filter(TherapySession.patient_id == current_patient.id)
        .order_by(TherapySession.session_number.desc())
        .all()
    )
    return sessions


# ──────────────────────────────────────────────────────────────────────────────
# VIDEOCALL ENDPOINTS (Real-time transcription)
# ──────────────────────────────────────────────────────────────────────────────

@videocall_router.post("/start", status_code=status.HTTP_201_CREATED)
async def start_session(
    therapist_id: int,
    patient_id: int,
    db: Session = Depends(get_db)
):
    """Start a new videocall therapy session."""
    therapist = db.query(Therapist).filter(Therapist.id == therapist_id).first()
    if not therapist:
        raise HTTPException(status_code=404, detail="Therapist not found")

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if patient.therapist_id != therapist_id:
        raise HTTPException(status_code=400, detail="Patient not assigned to therapist")

    # Auto-calculate session number for videocall
    existing_count = (
        db.query(TherapySession)
        .filter(TherapySession.patient_id == patient_id)
        .count()
    )

    new_session = TherapySession(
        therapist_id=therapist_id,
        patient_id=patient_id,
        started_at=datetime.utcnow(),
        session_number=existing_count + 1,  # Also auto-number videocall sessions
        session_date=datetime.now().strftime("%Y-%m-%d")  # Auto-set date for videocalls
    )

    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return {"id": new_session.id, "therapist_id": new_session.therapist_id, "patient_id": new_session.patient_id}


@videocall_router.post("/{session_id}/append-transcript", status_code=status.HTTP_201_CREATED)
async def append_transcript(
    session_id: int,
    speaker: str,
    text: str,
    confidence: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Append a transcript entry from videocall."""
    session = db.query(TherapySession).filter(TherapySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.ended_at is not None:
        raise HTTPException(status_code=400, detail="Session already ended")

    if speaker not in ["therapist", "patient"]:
        raise HTTPException(status_code=400, detail="Speaker must be 'therapist' or 'patient'")

    transcript = TherapyTranscript(
        session_id=session_id,
        speaker=speaker,
        text=text,
        confidence=confidence
    )

    db.add(transcript)
    db.commit()
    db.refresh(transcript)

    return {"id": transcript.id, "speaker": transcript.speaker, "text": transcript.text}


@videocall_router.post("/{session_id}/end", status_code=status.HTTP_200_OK)
async def end_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """End a videocall session and generate full transcript."""
    session = db.query(TherapySession).filter(TherapySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.ended_at:
        raise HTTPException(status_code=400, detail="Session already ended")

    # End the session
    session.ended_at = func.now()

    # Auto-generate full transcript from granular entries
    transcripts = (
        db.query(TherapyTranscript)
        .filter(TherapyTranscript.session_id == session_id)
        .order_by(TherapyTranscript.timestamp)
        .all()
    )

    if transcripts:
        transcript_lines = []
        for t in transcripts:
            speaker_label = "Therapist" if t.speaker == "therapist" else "Patient"
            transcript_lines.append(f"{speaker_label}: {t.text}")
        session.transcript = "\n".join(transcript_lines)

    # Auto-generate title if not set
    if not session.title:
        session.title = f"Session {session.session_number} - {session.session_date}"

    db.commit()
    db.refresh(session)

    # Generate AI analysis if available
    if generate_session_analysis:
        generate_session_analysis(session_id, db)

    return {"id": session.id, "ended_at": session.ended_at, "transcript_generated": bool(transcripts)}


@videocall_router.post("/transcribe-audio")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form(None),
    session_id: int = Form(None),
    speaker: str = Form(None),
    db: Session = Depends(get_db)
):
    """Transcribe audio and save to session."""
    if not transcription_service or not transcription_service.is_available:
        raise HTTPException(status_code=503, detail="Transcription service unavailable")

    allowed_formats = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
    file_ext = audio.filename.split(".")[-1].lower() if audio.filename else "webm"

    if file_ext not in allowed_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {file_ext}"
        )

    try:
        audio_bytes = await audio.read()
        result = transcription_service.transcribe_audio_bytes(
            audio_bytes=audio_bytes,
            filename=audio.filename or "audio.webm",
            language=language
        )

        if not result.get("success"):
            raise HTTPException(status_code=500, detail="Transcription failed")

        transcribed_text = result.get("text", "")
        transcript_entry = None

        if session_id and speaker and transcribed_text:
            session = db.query(TherapySession).filter(TherapySession.id == session_id).first()
            if session and not session.ended_at:
                if speaker not in ["therapist", "patient"]:
                    raise HTTPException(status_code=400, detail="Invalid speaker")

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

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# Register both routers
__all__ = [router, manual_router, videocall_router]
