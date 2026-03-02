from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime

from app.database.deps import get_db
from app.auth.utils import get_current_patient, get_current_therapist
from app.patients.models import Patient
from app.therapists.models import Therapist
from app.erp.models import ERPItem, ERPImaginalCard, ERPLiveSession, ERPSUDSReading, ERPExerciseNote
from app.erp.schemas import (
    ERPItemCreate, ERPItemUpdate, ERPItemResponse,
    ERPImaginalCardCreate, ERPImaginalCardUpdate, ERPImaginalCardResponse,
    ERPSessionNoteUpdate,
    ERPLiveSessionResponse,
    ERPSUDSReadingCreate, ERPSUDSReadingResponse,
    ERPPatientSummary, ERPItemWithSUDSResponse,
    ERPExerciseNoteCreate, ERPExerciseNoteResponse,
)

router = APIRouter(prefix="/erp", tags=["ERP Workspace"])


# ─── helpers ──────────────────────────────────────────────────────────────────

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


# ─── ERP Items ────────────────────────────────────────────────────────────────

@router.get("/items", response_model=List[ERPItemResponse])
async def list_erp_items(
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    """List all ERP items for the current patient, newest first."""
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
    """Get a single ERP item (patient must own it)."""
    return _get_owned_item(item_id, current_patient.id, db)


@router.post("/items", response_model=ERPItemResponse, status_code=status.HTTP_201_CREATED)
async def create_erp_item(
    payload: ERPItemCreate,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    """Create a new ERP item for the current patient."""
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
    """Update an existing ERP item (patient must own it)."""
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
    """Delete an ERP item (patient must own it)."""
    item = _get_owned_item(item_id, current_patient.id, db)
    db.delete(item)
    db.commit()


# ─── Session Note ─────────────────────────────────────────────────────────────

@router.patch("/items/{item_id}/session-note", response_model=ERPItemResponse)
async def update_session_note(
    item_id: int,
    payload: ERPSessionNoteUpdate,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    """Update the patient's exercise note for the current session."""
    item = _get_owned_item(item_id, current_patient.id, db)
    item.session_exercise_note = payload.session_exercise_note
    db.commit()
    return _get_owned_item(item.id, current_patient.id, db)


# ─── Imaginal Cards ───────────────────────────────────────────────────────────

@router.get("/items/{item_id}/imaginal-cards", response_model=List[ERPImaginalCardResponse])
async def list_imaginal_cards(
    item_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    """List imaginal cards for an ERP item."""
    _get_owned_item(item_id, current_patient.id, db)  # ownership check
    cards = (
        db.query(ERPImaginalCard)
        .filter(ERPImaginalCard.erp_item_id == item_id)
        .order_by(ERPImaginalCard.order_index)
        .all()
    )
    return cards


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
    """Add a new imaginal exposure card to an ERP item."""
    _get_owned_item(item_id, current_patient.id, db)  # ownership check

    # auto-assign order_index as next slot
    max_order = (
        db.query(ERPImaginalCard.order_index)
        .filter(ERPImaginalCard.erp_item_id == item_id)
        .order_by(ERPImaginalCard.order_index.desc())
        .first()
    )
    next_order = (max_order[0] + 1) if max_order else 0

    card = ERPImaginalCard(
        erp_item_id=item_id,
        content=payload.content,
        order_index=next_order,
    )
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
    """Update an imaginal card (patient must own the parent ERP item)."""
    card = db.query(ERPImaginalCard).filter(ERPImaginalCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    _get_owned_item(card.erp_item_id, current_patient.id, db)  # ownership check

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
    """Delete an imaginal card (patient must own the parent ERP item)."""
    card = db.query(ERPImaginalCard).filter(ERPImaginalCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    _get_owned_item(card.erp_item_id, current_patient.id, db)  # ownership check
    db.delete(card)
    db.commit()


# ─── Live Sessions ─────────────────────────────────────────────────────────────

def _get_active_session(item_id: int, patient_id: int, db: Session):
    """Return the running/paused session for this item, or None."""
    return (
        db.query(ERPLiveSession)
        .filter(
            ERPLiveSession.erp_item_id == item_id,
            ERPLiveSession.patient_id == patient_id,
            ERPLiveSession.status.in_(["running", "paused"]),
        )
        .order_by(ERPLiveSession.created_at.desc())
        .first()
    )


@router.get("/items/{item_id}/sessions/active", response_model=ERPLiveSessionResponse)
async def get_active_session(
    item_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    """Get the currently active (running or paused) session for an ERP item."""
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
    """Start a new live session for an ERP item (creates one; existing active sessions are ended first)."""
    _get_owned_item(item_id, current_patient.id, db)

    # End any lingering active session cleanly
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
    """Pause a running session and bank the elapsed seconds."""
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
    """Resume a paused session."""
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
    """End a session (running or paused)."""
    session = _get_session_owned(session_id, current_patient.id, db)
    _end_session_obj(session)
    db.commit()
    db.refresh(session)
    return session


# ─── SUDS Readings ─────────────────────────────────────────────────────────────

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
    """Record a SUDS data-point during a live session."""
    session = _get_session_owned(session_id, current_patient.id, db)
    reading = ERPSUDSReading(
        session_id=session.id,
        erp_item_id=session.erp_item_id,
        patient_id=current_patient.id,
        suds_value=payload.suds_value,
        elapsed_seconds=payload.elapsed_seconds,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


@router.get("/items/{item_id}/suds-history", response_model=list[ERPSUDSReadingResponse])
async def get_suds_history(
    item_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    """Get all SUDS readings across all sessions for an ERP item (for the graph)."""
    _get_owned_item(item_id, current_patient.id, db)
    readings = (
        db.query(ERPSUDSReading)
        .filter(
            ERPSUDSReading.erp_item_id == item_id,
            ERPSUDSReading.patient_id == current_patient.id,
        )
        .order_by(ERPSUDSReading.recorded_at.asc())
        .all()
    )
    return readings


# ─── Exercise Notes ────────────────────────────────────────────────────────────

@router.get("/items/{item_id}/exercise-notes/latest", response_model=Optional[ERPExerciseNoteResponse])
async def get_latest_exercise_note(
    item_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    """Return the most recent exercise note for this item, or null."""
    _get_owned_item(item_id, current_patient.id, db)
    note = (
        db.query(ERPExerciseNote)
        .filter(
            ERPExerciseNote.erp_item_id == item_id,
            ERPExerciseNote.patient_id == current_patient.id,
        )
        .order_by(ERPExerciseNote.created_at.desc())
        .first()
    )
    return note  # returns null serialised as None → 200 with null body


@router.get("/items/{item_id}/exercise-notes", response_model=list[ERPExerciseNoteResponse])
async def list_exercise_notes(
    item_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient),
):
    """Return all exercise notes for this item, newest first."""
    _get_owned_item(item_id, current_patient.id, db)
    notes = (
        db.query(ERPExerciseNote)
        .filter(
            ERPExerciseNote.erp_item_id == item_id,
            ERPExerciseNote.patient_id == current_patient.id,
        )
        .order_by(ERPExerciseNote.created_at.desc())
        .all()
    )
    return notes


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
    """Store a new exercise note (does NOT overwrite previous ones)."""
    _get_owned_item(item_id, current_patient.id, db)
    note = ERPExerciseNote(
        erp_item_id=item_id,
        patient_id=current_patient.id,
        content=payload.content,
    )
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
    """Update an existing exercise note in the same session visit (patient must own it)."""
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


# ─── session helpers ──────────────────────────────────────────────────────────

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
    """Mutate session in-place to mark it ended (does NOT commit)."""
    now = datetime.utcnow()
    if session.status == "running" and session.resumed_at:
        session.accumulated_seconds += (now - session.resumed_at).total_seconds()
    session.resumed_at = None
    session.status = "ended"
    session.ended_at = now


# ─── Therapist ERP endpoints ──────────────────────────────────────────────────

@router.get("/therapist/patients", response_model=list[ERPPatientSummary])
async def therapist_list_erp_patients(
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist),
):
    """
    Return a deduplicated list of the therapist's patients who have at least one ERP item.
    """
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


@router.get("/therapist/patients/{patient_id}/items", response_model=list[ERPItemResponse])
async def therapist_list_patient_erp_items(
    patient_id: int,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist),
):
    """Return all ERP items for a specific patient who belongs to this therapist."""
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
    """
    Return full detail for one ERP item (obsession, compulsions, SUDS history)
    for a patient who belongs to this therapist.
    """
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

    # Attach SUDS readings manually so the response schema can include them
    suds_readings = (
        db.query(ERPSUDSReading)
        .filter(
            ERPSUDSReading.erp_item_id == item_id,
            ERPSUDSReading.patient_id == patient_id,
        )
        .order_by(ERPSUDSReading.recorded_at.asc())
        .all()
    )

    # Dynamically set the attribute so Pydantic v2 model_validate picks it up
    item.suds_readings = suds_readings  # type: ignore[attr-defined]
    return ERPItemWithSUDSResponse.model_validate(item)

