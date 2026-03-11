from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.auth.utils import decode_access_token
from app.emergency_personnel.models import EmergencyPersonnel
from app.patients.models import Patient
from app.chat.models import EPPatientSession, EPPatientMessage
from app.chat.manager import ChatConnectionManager

ep_patient_router = APIRouter(prefix="/chat/ep-patient", tags=["EP-Patient Direct Chat"])

ep_patient_manager = ChatConnectionManager()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_ep(token: str, db: Session) -> EmergencyPersonnel:
    td = decode_access_token(token)
    if td.role != "emergency_personnel":
        raise HTTPException(status_code=403, detail="Emergency personnel only")
    ep = db.query(EmergencyPersonnel).filter(EmergencyPersonnel.id == td.id).first()
    if not ep:
        raise HTTPException(status_code=404, detail="EP not found")
    return ep


def _get_patient(token: str, db: Session) -> Patient:
    td = decode_access_token(token)
    if td.role != "patient":
        raise HTTPException(status_code=403, detail="Patients only")
    patient = db.query(Patient).filter(Patient.id == td.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


def _msg_to_dict(m: EPPatientMessage) -> dict:
    return {
        "type": "message",
        "id": m.id,
        "session_id": m.session_id,
        "sender_role": m.sender_role,
        "sender_id": m.sender_id,
        "sender_name": m.sender_name,
        "content": m.content,
        "created_at": m.created_at.isoformat(),
    }


# ─── EP endpoints ──────────────────────────────────────────────────────────────

@ep_patient_router.get("/patients")
def get_therapist_patients(token: str = Query(...), db: Session = Depends(get_db)):
    """EP sees all patients belonging to their therapist."""
    ep = _get_ep(token, db)
    patients = db.query(Patient).filter(Patient.therapist_id == ep.therapist_id).all()

    # For each patient, check if there's an active session
    result = []
    for p in patients:
        session = db.query(EPPatientSession).filter(
            EPPatientSession.ep_id == ep.id,
            EPPatientSession.patient_id == p.id,
            EPPatientSession.status == "active",
        ).first()
        result.append({
            "id": p.id,
            "name": p.name,
            "conditions": p.conditions,
            "active_session_id": session.id if session else None,
        })
    return result


@ep_patient_router.post("/session/{patient_id}")
def get_or_create_session(
    patient_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """EP opens (or resumes) a direct session with a patient."""
    ep = _get_ep(token, db)

    # Verify patient belongs to same therapist
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.therapist_id == ep.therapist_id,
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found or not your therapist's patient")

    # Check for existing active session
    session = db.query(EPPatientSession).filter(
        EPPatientSession.ep_id == ep.id,
        EPPatientSession.patient_id == patient_id,
        EPPatientSession.status == "active",
    ).first()

    if not session:
        session = EPPatientSession(ep_id=ep.id, patient_id=patient_id, status="active")
        db.add(session)
        db.commit()
        db.refresh(session)

    return {
        "id": session.id,
        "ep_id": session.ep_id,
        "ep_name": ep.name,
        "patient_id": session.patient_id,
        "patient_name": patient.name,
        "status": session.status,
        "created_at": session.created_at.isoformat(),
    }


@ep_patient_router.get("/session/{session_id}/messages")
def get_session_messages(
    session_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """Get message history for a session. Callable by either the EP or the patient."""
    td = decode_access_token(token)
    session = db.query(EPPatientSession).filter(EPPatientSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Access control: only the EP of this session or the patient may read messages
    if td.role == "emergency_personnel" and td.id != session.ep_id:
        raise HTTPException(status_code=403, detail="Not your session")
    elif td.role == "patient" and td.id != session.patient_id:
        raise HTTPException(status_code=403, detail="Not your session")
    elif td.role not in ("emergency_personnel", "patient"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    messages = (
        db.query(EPPatientMessage)
        .filter(EPPatientMessage.session_id == session_id)
        .order_by(EPPatientMessage.created_at.asc())
        .all()
    )
    return [_msg_to_dict(m) for m in messages]


@ep_patient_router.post("/session/{session_id}/close")
async def close_session(
    session_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """EP closes the session. All messages are deleted; patient loses access."""
    ep = _get_ep(token, db)
    session = db.query(EPPatientSession).filter(
        EPPatientSession.id == session_id,
        EPPatientSession.ep_id == ep.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session already closed")

    # Delete all messages
    db.query(EPPatientMessage).filter(EPPatientMessage.session_id == session_id).delete()

    # Mark session closed
    session.status = "closed"
    session.closed_at = datetime.now(timezone.utc)
    db.commit()

    # Notify connected clients so the patient's UI can update immediately
    await ep_patient_manager.broadcast(session_id, {"type": "session_closed"})

    return {"detail": "Session closed and messages deleted"}


# ─── Patient endpoints ────────────────────────────────────────────────────────

@ep_patient_router.get("/my-sessions")
def get_patient_ep_sessions(token: str = Query(...), db: Session = Depends(get_db)):
    """Patient sees all EPs who have an active session with them."""
    patient = _get_patient(token, db)
    sessions = db.query(EPPatientSession).filter(
        EPPatientSession.patient_id == patient.id,
        EPPatientSession.status == "active",
    ).all()

    result = []
    for s in sessions:
        ep = db.query(EmergencyPersonnel).filter(EmergencyPersonnel.id == s.ep_id).first()
        result.append({
            "session_id": s.id,
            "ep_id": s.ep_id,
            "ep_name": ep.name if ep else "Helper",
            "created_at": s.created_at.isoformat(),
        })
    return result


# ─── WebSocket ────────────────────────────────────────────────────────────────

@ep_patient_router.websocket("/ws/{session_id}")
async def websocket_ep_patient(
    websocket: WebSocket,
    session_id: int,
    token: str = Query(...),
):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        td = decode_access_token(token)
        session = db.query(EPPatientSession).filter(EPPatientSession.id == session_id).first()
        if not session or session.status != "active":
            await websocket.close(code=4004)
            return

        # Authorise + resolve sender info
        if td.role == "emergency_personnel":
            if td.id != session.ep_id:
                await websocket.close(code=4003)
                return
            ep = db.query(EmergencyPersonnel).filter(EmergencyPersonnel.id == td.id).first()
            sender_name = ep.name if ep else "Helper"
            sender_role = "ep"
        elif td.role == "patient":
            if td.id != session.patient_id:
                await websocket.close(code=4003)
                return
            patient = db.query(Patient).filter(Patient.id == td.id).first()
            sender_name = patient.name if patient else "Patient"
            sender_role = "patient"
        else:
            await websocket.close(code=4003)
            return

        await ep_patient_manager.connect(websocket, session_id)

        try:
            while True:
                data = await websocket.receive_text()
                payload = json.loads(data)
                content = payload.get("content", "").strip()
                if not content:
                    continue

                msg = EPPatientMessage(
                    session_id=session_id,
                    sender_role=sender_role,
                    sender_id=td.id,
                    sender_name=sender_name,
                    content=content,
                )
                db.add(msg)
                db.commit()
                db.refresh(msg)

                await ep_patient_manager.broadcast(session_id, _msg_to_dict(msg))

        except WebSocketDisconnect:
            ep_patient_manager.disconnect(websocket, session_id)

    except Exception:
        try:
            await websocket.close(code=4000)
        except Exception:
            pass
    finally:
        db.close()
