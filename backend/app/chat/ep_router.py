from __future__ import annotations

import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.auth.utils import decode_access_token
from app.therapists.models import Therapist
from app.emergency_personnel.models import EmergencyPersonnel
from app.chat.models import EPDirectMessage
from app.chat.manager import ChatConnectionManager

ep_router = APIRouter(prefix="/chat/ep", tags=["EP Chat"])

# Separate manager instance so EP rooms don't collide with patient group rooms
ep_manager = ChatConnectionManager()


# ─── helpers ────────────────────────────────────────────────────────────────

def _get_therapist(token: str, db: Session) -> Therapist:
    token_data = decode_access_token(token)
    if token_data.role != "therapist":
        raise HTTPException(status_code=403, detail="Therapists only")
    therapist = db.query(Therapist).filter(Therapist.id == token_data.id).first()
    if not therapist:
        raise HTTPException(status_code=404, detail="Therapist not found")
    return therapist


def _get_ep(token: str, db: Session) -> EmergencyPersonnel:
    token_data = decode_access_token(token)
    if token_data.role != "emergency_personnel":
        raise HTTPException(status_code=403, detail="Emergency personnel only")
    ep = db.query(EmergencyPersonnel).filter(EmergencyPersonnel.id == token_data.id).first()
    if not ep:
        raise HTTPException(status_code=404, detail="Not found")
    return ep


# ─── Therapist: list all assigned EPs ────────────────────────────────────────

@ep_router.get("/contacts")
def list_ep_contacts(
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    therapist = _get_therapist(token, db)
    eps = (
        db.query(EmergencyPersonnel)
        .filter(EmergencyPersonnel.therapist_id == therapist.id)
        .all()
    )
    return [{"id": e.id, "name": e.name, "email": e.email} for e in eps]


# ─── EP: get my therapist info ────────────────────────────────────────────────

@ep_router.get("/my-therapist")
def get_my_therapist(
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    ep = _get_ep(token, db)
    therapist = db.query(Therapist).filter(Therapist.id == ep.therapist_id).first()
    if not therapist:
        raise HTTPException(status_code=404, detail="Therapist not found")
    return {"id": therapist.id, "name": therapist.name, "ep_id": ep.id}


# ─── Message history (accessible by both therapist and EP) ───────────────────

@ep_router.get("/messages/{ep_id}")
def get_ep_messages(
    ep_id: int,
    limit: int = 200,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    token_data = decode_access_token(token)
    ep = db.query(EmergencyPersonnel).filter(EmergencyPersonnel.id == ep_id).first()
    if not ep:
        raise HTTPException(status_code=404, detail="EP not found")

    if token_data.role == "therapist":
        if ep.therapist_id != token_data.id:
            raise HTTPException(status_code=403, detail="Not your contact")
    elif token_data.role == "emergency_personnel":
        if ep.id != token_data.id:
            raise HTTPException(status_code=403, detail="Forbidden")
    else:
        raise HTTPException(status_code=403, detail="Forbidden")

    messages = (
        db.query(EPDirectMessage)
        .filter(EPDirectMessage.ep_id == ep_id)
        .order_by(EPDirectMessage.created_at.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": m.id,
            "ep_id": m.ep_id,
            "therapist_id": m.therapist_id,
            "sender_role": m.sender_role,
            "sender_id": m.sender_id,
            "sender_name": m.sender_name,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


# ─── WebSocket ────────────────────────────────────────────────────────────────

@ep_router.websocket("/ws/{ep_id}")
async def ep_websocket(
    websocket: WebSocket,
    ep_id: int,
    token: str = Query(...),
):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        token_data = decode_access_token(token)
        ep = db.query(EmergencyPersonnel).filter(EmergencyPersonnel.id == ep_id).first()
        if not ep:
            await websocket.close(code=4004)
            return

        if token_data.role == "therapist":
            if ep.therapist_id != token_data.id:
                await websocket.close(code=4003)
                return
            user = db.query(Therapist).filter(Therapist.id == token_data.id).first()
            sender_name = user.name if user else "Therapist"
            sender_role = "therapist"
            sender_id = token_data.id
        elif token_data.role == "emergency_personnel":
            if ep.id != token_data.id:
                await websocket.close(code=4003)
                return
            sender_name = ep.name
            sender_role = "emergency_personnel"
            sender_id = ep.id
        else:
            await websocket.close(code=4003)
            return

        therapist_id = ep.therapist_id
        db.close()

        await ep_manager.connect(websocket, ep_id)
        try:
            while True:
                data = await websocket.receive_text()
                payload = json.loads(data)
                content = payload.get("content", "").strip()
                if not content:
                    continue

                db2 = SessionLocal()
                try:
                    msg = EPDirectMessage(
                        ep_id=ep_id,
                        therapist_id=therapist_id,
                        sender_role=sender_role,
                        sender_id=sender_id,
                        sender_name=sender_name,
                        content=content,
                    )
                    db2.add(msg)
                    db2.commit()
                    db2.refresh(msg)
                    await ep_manager.broadcast(ep_id, {
                        "type": "message",
                        "id": msg.id,
                        "sender_id": sender_id,
                        "sender_role": sender_role,
                        "sender_name": sender_name,
                        "content": content,
                        "created_at": msg.created_at.isoformat(),
                    })
                finally:
                    db2.close()
        except WebSocketDisconnect:
            ep_manager.disconnect(websocket, ep_id)
    finally:
        try:
            db.close()
        except Exception:
            pass
