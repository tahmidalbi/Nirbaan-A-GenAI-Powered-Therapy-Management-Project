# app/erp/router.py
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.auth.utils import get_current_patient, get_current_therapist
from app.database.deps import get_db
from app.patients.models import Patient
from app.therapists.models import Therapist

from app.erp.models import (
    ERPExerciseNote,
    ERPImaginalCard,
    ERPItem,
    ERPLiveSession,
    ERPSUDSReading,
    ERPChatMessage,  # make sure this model exists in app/erp/models.py
)
from app.erp.schemas import (
    # ERP core
    ERPItemCreate,
    ERPItemUpdate,
    ERPItemResponse,
    ERPImaginalCardCreate,
    ERPImaginalCardUpdate,
    ERPImaginalCardResponse,
    ERPSessionNoteUpdate,
    ERPLiveSessionResponse,
    ERPSUDSReadingCreate,
    ERPSUDSReadingResponse,
    ERPPatientSummary,
    ERPItemWithSUDSResponse,
    ERPExerciseNoteCreate,
    ERPExerciseNoteResponse,
    # Coach + reports
    ERPUserMessageRequest,
    ERPDebriefSubmitRequest,
    CoachResponse,
    ERPEndReportResponse,
    PatientFeedbackJSON,
    TherapistReportJSON,
    ERPChatMessageResponse,
    ERPSessionTranscriptResponse,
    # Session detail
    ERPSessionDetailResponse,
    TherapistSessionDetailResponse,
    CrossSessionOverviewResult,
)

from app.erp.ERPCoach.graph import invoke_erp_coach
from app.erp.ERPCoach.llm.client import LLMClient
from app.erp.ERPCoach.nodes.report_bundle import build_prior_reports_block, format_session_report_block
from app.erp.ERPCoach.prompts.report_prompts import build_cross_session_overview_prompt

router = APIRouter(prefix="/erp", tags=["ERP Workspace"])


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _get_owned_item(item_id: int, patient_id: int, db: Session) -> ERPItem:
    item = (
        db.query(ERPItem)
        .options(joinedload(ERPItem.imaginal_cards))
        .filter(ERPItem.id == item_id, ERPItem.patient_id == patient_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ERP item not found")
    return item


def _get_session_owned(session_id: int, patient_id: int, db: Session) -> ERPLiveSession:
    session = (
        db.query(ERPLiveSession)
        .filter(ERPLiveSession.id == session_id, ERPLiveSession.patient_id == patient_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


def _end_session_obj(session: ERPLiveSession) -> None:
    now = datetime.utcnow()
    if session.status == "running" and session.resumed_at:
        session.accumulated_seconds += (now - session.resumed_at).total_seconds()
    session.resumed_at = None
    session.status = "ended"
    session.ended_at = now


def _get_active_session(item_id: int, patient_id: int, db: Session) -> Optional[ERPLiveSession]:
    return (
        db.query(ERPLiveSession)
        .filter(
            ERPLiveSession.erp_item_id == item_id,
            ERPLiveSession.patient_id == patient_id,
            ERPLiveSession.status.in_(["running", "paused", "ending"]),
        )
        .order_by(ERPLiveSession.created_at.desc())
        .first()
    )


# ──────────────────────────────────────────────────────────────────────────────
# ERP Items
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/items", response_model=List[ERPItemResponse])
async def list_erp_items(
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    items = (
        db.query(ERPItem)
        .options(joinedload(ERPItem.imaginal_cards))
        .filter(ERPItem.patient_id == current_patient.id)
        .order_by(ERPItem.created_at.desc())
        .all()
    )
    return items


@router.get("/items/{item_id}", response_model=ERPItemResponse)
async def get_erp_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    return _get_owned_item(item_id, current_patient.id, db)


@router.post("/items", response_model=ERPItemResponse, status_code=status.HTTP_201_CREATED)
async def create_erp_item(
    payload: ERPItemCreate,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    item = ERPItem(
        patient_id=current_patient.id,
        obsession=payload.obsession,
        compulsions=payload.compulsions,
        suds=payload.suds,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _get_owned_item(item.id, current_patient.id, db)


@router.put("/items/{item_id}", response_model=ERPItemResponse)
async def update_erp_item(
    item_id: int,
    payload: ERPItemUpdate,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    item = _get_owned_item(item_id, current_patient.id, db)
    if payload.obsession is not None:
        item.obsession = payload.obsession
    if payload.compulsions is not None:
        item.compulsions = payload.compulsions
    if payload.suds is not None:
        item.suds = payload.suds
    db.commit()
    return _get_owned_item(item.id, current_patient.id, db)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_erp_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    item = _get_owned_item(item_id, current_patient.id, db)
    db.delete(item)
    db.commit()


# ──────────────────────────────────────────────────────────────────────────────
# Session Note (legacy field on ERPItem)
# ──────────────────────────────────────────────────────────────────────────────

@router.patch("/items/{item_id}/session-note", response_model=ERPItemResponse)
async def update_session_note(
    item_id: int,
    payload: ERPSessionNoteUpdate,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    item = _get_owned_item(item_id, current_patient.id, db)
    item.session_exercise_note = payload.session_exercise_note
    db.commit()
    return _get_owned_item(item.id, current_patient.id, db)


# ──────────────────────────────────────────────────────────────────────────────
# Imaginal Cards
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/items/{item_id}/imaginal-cards", response_model=List[ERPImaginalCardResponse])
async def list_imaginal_cards(
    item_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    _get_owned_item(item_id, current_patient.id, db)
    return (
        db.query(ERPImaginalCard)
        .filter(ERPImaginalCard.erp_item_id == item_id)
        .order_by(ERPImaginalCard.order_index)
        .all()
    )


@router.post(
    "/items/{item_id}/imaginal-cards",
    response_model=ERPImaginalCardResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_imaginal_card(
    item_id: int,
    payload: ERPImaginalCardCreate,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    _get_owned_item(item_id, current_patient.id, db)
    max_order = (
        db.query(ERPImaginalCard.order_index)
        .filter(ERPImaginalCard.erp_item_id == item_id)
        .order_by(ERPImaginalCard.order_index.desc())
        .first()
    )
    next_order = (max_order[0] + 1) if max_order else 0
    card = ERPImaginalCard(erp_item_id=item_id, content=payload.content, order_index=next_order)
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


@router.put("/imaginal-cards/{card_id}", response_model=ERPImaginalCardResponse)
async def update_imaginal_card(
    card_id: int,
    payload: ERPImaginalCardUpdate,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    card = db.query(ERPImaginalCard).filter(ERPImaginalCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    _get_owned_item(card.erp_item_id, current_patient.id, db)

    if payload.content is not None:
        card.content = payload.content
    if payload.order_index is not None:
        card.order_index = payload.order_index

    db.commit()
    db.refresh(card)
    return card


@router.delete("/imaginal-cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_imaginal_card(
    card_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    card = db.query(ERPImaginalCard).filter(ERPImaginalCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    _get_owned_item(card.erp_item_id, current_patient.id, db)
    db.delete(card)
    db.commit()


# ──────────────────────────────────────────────────────────────────────────────
# Live Sessions
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/items/{item_id}/sessions/active", response_model=ERPLiveSessionResponse)
async def get_active_session(
    item_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    _get_owned_item(item_id, current_patient.id, db)
    session = _get_active_session(item_id, current_patient.id, db)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active session")
    return session


@router.post(
    "/items/{item_id}/sessions/start",
    response_model=ERPLiveSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_session(
    item_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    _get_owned_item(item_id, current_patient.id, db)
    existing = _get_active_session(item_id, current_patient.id, db)
    if existing:
        _end_session_obj(existing)
        db.commit()

    new_session = ERPLiveSession(
        erp_item_id=item_id,
        patient_id=current_patient.id,
        status="running",
        accumulated_seconds=0.0,
        resumed_at=datetime.utcnow(),
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


@router.patch("/sessions/{session_id}/pause", response_model=ERPLiveSessionResponse)
async def pause_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    session = _get_session_owned(session_id, current_patient.id, db)
    if session.status != "running":
        raise HTTPException(status_code=400, detail="Session is not running")

    now = datetime.utcnow()
    if session.resumed_at:
        session.accumulated_seconds += (now - session.resumed_at).total_seconds()
    session.resumed_at = None
    session.status = "paused"

    db.commit()
    db.refresh(session)
    return session


@router.patch("/sessions/{session_id}/resume", response_model=ERPLiveSessionResponse)
async def resume_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    session = _get_session_owned(session_id, current_patient.id, db)
    if session.status != "paused":
        raise HTTPException(status_code=400, detail="Session is not paused")

    session.resumed_at = datetime.utcnow()
    session.status = "running"

    db.commit()
    db.refresh(session)
    return session


@router.patch("/sessions/{session_id}/end", response_model=ERPLiveSessionResponse)
async def end_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    session = _get_session_owned(session_id, current_patient.id, db)
    _end_session_obj(session)
    db.commit()
    db.refresh(session)
    return session


# ──────────────────────────────────────────────────────────────────────────────
# SUDS Readings
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/sessions/{session_id}/suds",
    response_model=ERPSUDSReadingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_suds(
    session_id: int,
    payload: ERPSUDSReadingCreate,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    session = _get_session_owned(session_id, current_patient.id, db)

    reading = ERPSUDSReading(
        session_id=session.id,
        erp_item_id=session.erp_item_id,
        patient_id=current_patient.id,
        suds_value=payload.suds_value,
        elapsed_seconds=payload.elapsed_seconds,
    )
    db.add(reading)

    # ✅ update session.last_suds_at (for reminders)
    session.last_suds_at = datetime.utcnow()

    db.commit()
    db.refresh(reading)

    # Run graph immediately to check for SUDS spike
    if session.status in ("running", "paused"):
        try:
            invoke_erp_coach(
                {"session_id": session_id, "event_type": "SUDS_SUBMITTED"}
            )
        except Exception:
            logger.exception(
                "Spike check failed after SUDS recording (session=%s)",
                session_id,
            )

    return reading


@router.get("/items/{item_id}/suds-history", response_model=List[ERPSUDSReadingResponse])
async def get_suds_history(
    item_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    _get_owned_item(item_id, current_patient.id, db)
    return (
        db.query(ERPSUDSReading)
        .filter(
            ERPSUDSReading.erp_item_id == item_id,
            ERPSUDSReading.patient_id == current_patient.id,
        )
        .order_by(ERPSUDSReading.recorded_at.asc())
        .all()
    )


# ──────────────────────────────────────────────────────────────────────────────
# Exercise Notes
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/items/{item_id}/exercise-notes/latest", response_model=Optional[ERPExerciseNoteResponse])
async def get_latest_exercise_note(
    item_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    _get_owned_item(item_id, current_patient.id, db)
    return (
        db.query(ERPExerciseNote)
        .filter(
            ERPExerciseNote.erp_item_id == item_id,
            ERPExerciseNote.patient_id == current_patient.id,
        )
        .order_by(ERPExerciseNote.created_at.desc())
        .first()
    )


@router.get("/items/{item_id}/exercise-notes", response_model=List[ERPExerciseNoteResponse])
async def list_exercise_notes(
    item_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    _get_owned_item(item_id, current_patient.id, db)
    return (
        db.query(ERPExerciseNote)
        .filter(
            ERPExerciseNote.erp_item_id == item_id,
            ERPExerciseNote.patient_id == current_patient.id,
        )
        .order_by(ERPExerciseNote.created_at.desc())
        .all()
    )


@router.post(
    "/items/{item_id}/exercise-notes",
    response_model=ERPExerciseNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_exercise_note(
    item_id: int,
    payload: ERPExerciseNoteCreate,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    _get_owned_item(item_id, current_patient.id, db)
    note = ERPExerciseNote(erp_item_id=item_id, patient_id=current_patient.id, content=payload.content)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.patch("/exercise-notes/{note_id}", response_model=ERPExerciseNoteResponse)
async def update_exercise_note(
    note_id: int,
    payload: ERPExerciseNoteCreate,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    note = (
        db.query(ERPExerciseNote)
        .filter(ERPExerciseNote.id == note_id, ERPExerciseNote.patient_id == current_patient.id)
        .first()
    )
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise note not found")

    note.content = payload.content
    db.commit()
    db.refresh(note)
    return note


# ──────────────────────────────────────────────────────────────────────────────
# Coach + Chat (LangGraph integration)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/coach/message", response_model=CoachResponse)
async def coach_user_message(
    session_id: int,
    payload: ERPUserMessageRequest,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    _get_session_owned(session_id, current_patient.id, db)

    out = invoke_erp_coach(
        {
            "session_id": session_id,
            "event_type": "USER_MESSAGE",
            "user_message": payload.message,
        }
    )
    return CoachResponse.model_validate(out.get("coach_response_json") or {})


@router.post("/sessions/{session_id}/coach/end-click", response_model=CoachResponse)
async def coach_end_click_prompt(
    session_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    """
    Patient clicked "End Session" (Option A).
    This endpoint only generates the debrief prompt message + SHOW_DEBRIEF_FORM next_action.
    (Your /sessions/{id}/end endpoint still ends the timer/status.)
    """
    session = _get_session_owned(session_id, current_patient.id, db)
    if session.status in ("running", "paused"):
        # Stop the timer BEFORE changing status so accumulated_seconds is correct
        if session.status == "running" and session.resumed_at:
            now = datetime.utcnow()
            session.accumulated_seconds += (now - session.resumed_at).total_seconds()
        session.resumed_at = None
        session.status = "ending"
        db.commit()

    out = invoke_erp_coach(
        {
            "session_id": session_id,
            "event_type": "END_SESSION_DEBRIEF_PROMPT",
        }
    )
    return CoachResponse.model_validate(out.get("coach_response_json") or {})


@router.post("/sessions/{session_id}/coach/debrief-submit", response_model=ERPEndReportResponse)
async def coach_debrief_submit_generate_reports(
    session_id: int,
    payload: ERPDebriefSubmitRequest,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    """
    Patient submits debrief text.
    This triggers END_SESSION_REPORT and persists therapist_report_json + patient_feedback_json.
    """
    session = _get_session_owned(session_id, current_patient.id, db)

    out = invoke_erp_coach(
        {
            "session_id": session_id,
            "event_type": "END_SESSION_REPORT",
            "patient_debrief_text": payload.patient_debrief_text,
        }
    )

    # End the session definitively after report generation (if not already ended)
    if session.status != "ended":
        _end_session_obj(session)
        db.commit()

    pf = PatientFeedbackJSON.model_validate(out.get("patient_feedback_json") or {})
    # We don't return the whole therapist report to patient in this response.
    # The therapist fetches it from therapist UI (or you add a therapist endpoint later).

    return ERPEndReportResponse(
        patient_feedback=pf,
        therapist_report_saved=True,
        latest_session_id_updated=True,
    )


@router.get("/sessions/{session_id}/transcript", response_model=ERPSessionTranscriptResponse)
async def get_session_transcript(
    session_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    """
    Returns the chat transcript for this session.
    Frontend can use this to show chat history.
    """
    _get_session_owned(session_id, current_patient.id, db)

    msgs = (
        db.query(ERPChatMessage)
        .filter(
            ERPChatMessage.session_id == session_id,
            ERPChatMessage.patient_id == current_patient.id,
        )
        .order_by(ERPChatMessage.created_at.asc())
        .all()
    )
    return ERPSessionTranscriptResponse(
        session_id=session_id,
        messages=[ERPChatMessageResponse.model_validate(m) for m in msgs],
    )


# ──────────────────────────────────────────────────────────────────────────────
# Patient Session History
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/items/{item_id}/sessions", response_model=List[ERPLiveSessionResponse])
async def list_item_sessions(
    item_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    """List all sessions (active and ended) for an ERP item, newest first."""
    _get_owned_item(item_id, current_patient.id, db)
    return (
        db.query(ERPLiveSession)
        .filter(
            ERPLiveSession.erp_item_id == item_id,
            ERPLiveSession.patient_id == current_patient.id,
        )
        .order_by(ERPLiveSession.created_at.desc())
        .all()
    )


@router.get("/sessions/{session_id}", response_model=ERPLiveSessionResponse)
async def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    """Get a single session's basic info (status, timer, timestamps)."""
    return _get_session_owned(session_id, current_patient.id, db)


@router.get("/sessions/{session_id}/detail", response_model=ERPSessionDetailResponse)
async def get_session_detail(
    session_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    """
    Full session detail for the patient:
      - session info (status, timer)
      - SUDS readings
      - patient feedback (if session ended and report was generated)
    """
    session = _get_session_owned(session_id, current_patient.id, db)

    suds = (
        db.query(ERPSUDSReading)
        .filter(ERPSUDSReading.session_id == session_id)
        .order_by(ERPSUDSReading.recorded_at.asc())
        .all()
    )

    patient_feedback = None
    if session.patient_feedback_json:
        patient_feedback = PatientFeedbackJSON.model_validate(session.patient_feedback_json)

    return ERPSessionDetailResponse(
        session=ERPLiveSessionResponse.model_validate(session),
        suds_readings=[ERPSUDSReadingResponse.model_validate(r) for r in suds],
        patient_feedback=patient_feedback,
    )


@router.get("/sessions/{session_id}/suds", response_model=List[ERPSUDSReadingResponse])
async def get_session_suds(
    session_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    """Get SUDS readings for a specific session (chronological order)."""
    _get_session_owned(session_id, current_patient.id, db)
    return (
        db.query(ERPSUDSReading)
        .filter(ERPSUDSReading.session_id == session_id)
        .order_by(ERPSUDSReading.recorded_at.asc())
        .all()
    )


# ──────────────────────────────────────────────────────────────────────────────
# Therapist endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/therapist/patients", response_model=List[ERPPatientSummary])
async def therapist_list_erp_patients(
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist),
):
    from sqlalchemy import func as sqlfunc

    patient_counts = (
        db.query(Patient, sqlfunc.count(ERPItem.id).label("item_count"))
        .join(ERPItem, ERPItem.patient_id == Patient.id)
        .filter(Patient.therapist_id == current_therapist.id)
        .group_by(Patient.id)
        .all()
    )

    return [
        ERPPatientSummary(
            patient_id=p.id,
            patient_name=p.name,
            patient_email=p.email,
            item_count=count,
        )
        for p, count in patient_counts
    ]


@router.get("/therapist/patients/{patient_id}/items", response_model=List[ERPItemResponse])
async def therapist_list_patient_erp_items(
    patient_id: int,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist),
):
    patient = (
        db.query(Patient)
        .filter(Patient.id == patient_id, Patient.therapist_id == current_therapist.id)
        .first()
    )
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    items = (
        db.query(ERPItem)
        .options(joinedload(ERPItem.imaginal_cards))
        .filter(ERPItem.patient_id == patient_id)
        .order_by(ERPItem.created_at.desc())
        .all()
    )
    return items


@router.get("/therapist/patients/{patient_id}/items/{item_id}", response_model=ERPItemWithSUDSResponse)
async def therapist_get_erp_item_detail(
    patient_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist),
):
    patient = (
        db.query(Patient)
        .filter(Patient.id == patient_id, Patient.therapist_id == current_therapist.id)
        .first()
    )
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    item = (
        db.query(ERPItem)
        .options(joinedload(ERPItem.imaginal_cards))
        .filter(ERPItem.id == item_id, ERPItem.patient_id == patient_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ERP item not found")

    suds_readings = (
        db.query(ERPSUDSReading)
        .filter(
            ERPSUDSReading.erp_item_id == item_id,
            ERPSUDSReading.patient_id == patient_id,
        )
        .order_by(ERPSUDSReading.recorded_at.asc())
        .all()
    )

    item.suds_readings = suds_readings  # type: ignore[attr-defined]

    # Optional convenience: include latest report JSON in therapist item detail response
    # If ERPItem.latest_session_id is set, fetch that session and attach its report JSON.
    if getattr(item, "latest_session_id", None):
        latest_session = (
            db.query(ERPLiveSession)
            .filter(
                ERPLiveSession.id == item.latest_session_id,
                ERPLiveSession.patient_id == patient_id,
            )
            .first()
        )
        if latest_session:
            item.latest_therapist_report_json = latest_session.therapist_report_json  # type: ignore[attr-defined]
            item.latest_patient_feedback_json = latest_session.patient_feedback_json  # type: ignore[attr-defined]

    return ERPItemWithSUDSResponse.model_validate(item)


def _therapist_owns_patient(patient_id: int, therapist_id: int, db: Session) -> Patient:
    """Verify a therapist owns this patient, return Patient or 404."""
    patient = (
        db.query(Patient)
        .filter(Patient.id == patient_id, Patient.therapist_id == therapist_id)
        .first()
    )
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient


@router.get(
    "/therapist/patients/{patient_id}/items/{item_id}/sessions",
    response_model=List[ERPLiveSessionResponse],
)
async def therapist_list_item_sessions(
    patient_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist),
):
    """List all sessions for a patient's ERP item (newest first)."""
    _therapist_owns_patient(patient_id, current_therapist.id, db)

    item = (
        db.query(ERPItem)
        .filter(ERPItem.id == item_id, ERPItem.patient_id == patient_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ERP item not found")

    return (
        db.query(ERPLiveSession)
        .filter(
            ERPLiveSession.erp_item_id == item_id,
            ERPLiveSession.patient_id == patient_id,
        )
        .order_by(ERPLiveSession.created_at.desc())
        .all()
    )


@router.get(
    "/therapist/sessions/{session_id}",
    response_model=TherapistSessionDetailResponse,
)
async def therapist_get_session_detail(
    session_id: int,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist),
):
    """
    Full session detail for therapist: session info, transcript, SUDS,
    therapist report, and patient feedback.
    """
    session = db.query(ERPLiveSession).filter(ERPLiveSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Verify therapist owns the patient
    _therapist_owns_patient(session.patient_id, current_therapist.id, db)

    # Transcript
    msgs = (
        db.query(ERPChatMessage)
        .filter(ERPChatMessage.session_id == session_id)
        .order_by(ERPChatMessage.created_at.asc())
        .all()
    )
    transcript = ERPSessionTranscriptResponse(
        session_id=session_id,
        messages=[ERPChatMessageResponse.model_validate(m) for m in msgs],
    )

    # SUDS
    suds = (
        db.query(ERPSUDSReading)
        .filter(ERPSUDSReading.session_id == session_id)
        .order_by(ERPSUDSReading.recorded_at.asc())
        .all()
    )

    therapist_report = None
    if session.therapist_report_json:
        therapist_report = TherapistReportJSON.model_validate(session.therapist_report_json)

    patient_feedback = None
    if session.patient_feedback_json:
        patient_feedback = PatientFeedbackJSON.model_validate(session.patient_feedback_json)

    return TherapistSessionDetailResponse(
        session=ERPLiveSessionResponse.model_validate(session),
        transcript=transcript,
        suds_readings=[ERPSUDSReadingResponse.model_validate(r) for r in suds],
        therapist_report=therapist_report,
        patient_feedback=patient_feedback,
    )


@router.get(
    "/therapist/sessions/{session_id}/transcript",
    response_model=ERPSessionTranscriptResponse,
)
async def therapist_get_session_transcript(
    session_id: int,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist),
):
    """Get transcript for a session (therapist view)."""
    session = db.query(ERPLiveSession).filter(ERPLiveSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    _therapist_owns_patient(session.patient_id, current_therapist.id, db)

    msgs = (
        db.query(ERPChatMessage)
        .filter(ERPChatMessage.session_id == session_id)
        .order_by(ERPChatMessage.created_at.asc())
        .all()
    )
    return ERPSessionTranscriptResponse(
        session_id=session_id,
        messages=[ERPChatMessageResponse.model_validate(m) for m in msgs],
    )


@router.get(
    "/therapist/sessions/{session_id}/report",
    response_model=TherapistReportJSON,
)
async def therapist_get_session_report(
    session_id: int,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist),
):
    """Get the therapist report JSON for an ended session."""
    session = db.query(ERPLiveSession).filter(ERPLiveSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    _therapist_owns_patient(session.patient_id, current_therapist.id, db)

    if not session.therapist_report_json:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No therapist report available for this session",
        )

    return TherapistReportJSON.model_validate(session.therapist_report_json)


# ──────────────────────────────────────────────────────────────────────────────
# Generate (or backfill) cross-session overview for an existing report
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/therapist/sessions/{session_id}/cross-session-overview",
    response_model=CrossSessionOverviewResult,
)
async def therapist_generate_cross_session_overview(
    session_id: int,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist),
):
    """
    Computes (or recomputes) the cross_session_overview for a session whose
    therapist_report_json was generated before the feature existed.
    Patches the stored JSON and returns the new cross_session_overview.
    """
    session = db.query(ERPLiveSession).filter(ERPLiveSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    _therapist_owns_patient(session.patient_id, current_therapist.id, db)

    if not session.therapist_report_json:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No therapist report available for this session",
        )

    # Fetch prior ended sessions for the same obsession item (up to 5, with reports)
    prior_sessions = (
        db.query(ERPLiveSession)
        .filter(
            ERPLiveSession.erp_item_id == session.erp_item_id,
            ERPLiveSession.status == "ended",
            ERPLiveSession.id != session_id,
            ERPLiveSession.therapist_report_json.isnot(None),
        )
        .order_by(desc(ERPLiveSession.ended_at))
        .limit(5)
        .all()
    )

    prior_reports_block = build_prior_reports_block(prior_sessions)

    if not prior_reports_block.strip():
        # First session — no cross-session data possible
        result = CrossSessionOverviewResult()
        overview_dict = None
    else:
        current_session_block = format_session_report_block(session.therapist_report_json)
        prompt = build_cross_session_overview_prompt(
            current_session_block=current_session_block,
            prior_reports_block=prior_reports_block,
        )
        llm = LLMClient()
        result = llm.structured_call(schema=CrossSessionOverviewResult, prompt=prompt)
        overview_dict = result.model_dump()

    # Patch only the cross_session_overview field in the stored JSON
    updated_json = dict(session.therapist_report_json)
    updated_json["cross_session_overview"] = overview_dict
    session.therapist_report_json = updated_json
    db.commit()

    return result