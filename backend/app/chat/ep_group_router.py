from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.auth.utils import decode_access_token
from app.therapists.models import Therapist
from app.emergency_personnel.models import EmergencyPersonnel
from app.chat.models import EPGroup, EPGroupMessage
from app.chat.manager import ChatConnectionManager

ep_group_router = APIRouter(prefix="/chat/ep-group", tags=["EP Group Chat"])

# Separate manager so EP-group rooms don't collide with any other rooms
ep_group_manager = ChatConnectionManager()


# ─── Shared helpers ───────────────────────────────────────────────────────────

def _get_therapist(token: str, db: Session) -> Therapist:
    td = decode_access_token(token)
    if td.role != "therapist":
        raise HTTPException(status_code=403, detail="Therapists only")
    t = db.query(Therapist).filter(Therapist.id == td.id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Therapist not found")
    return t


def _get_ep(token: str, db: Session) -> EmergencyPersonnel:
    td = decode_access_token(token)
    if td.role != "emergency_personnel":
        raise HTTPException(status_code=403, detail="Emergency personnel only")
    ep = db.query(EmergencyPersonnel).filter(EmergencyPersonnel.id == td.id).first()
    if not ep:
        raise HTTPException(status_code=404, detail="Not found")
    return ep


def _get_or_create_group(therapist_id: int, db: Session) -> EPGroup:
    """Return the EP group for this therapist, creating it lazily if needed."""
    group = db.query(EPGroup).filter(EPGroup.therapist_id == therapist_id).first()
    if not group:
        group = EPGroup(therapist_id=therapist_id)
        db.add(group)
        db.commit()
        db.refresh(group)
    return group


def _verify_access(token_data, group: EPGroup, db: Session):
    """Raise 403 if the caller is not the group's therapist or one of their EPs."""
    if token_data.role == "therapist":
        if group.therapist_id != token_data.id:
            raise HTTPException(status_code=403, detail="Not your group")
    elif token_data.role == "emergency_personnel":
        ep = db.query(EmergencyPersonnel).filter(EmergencyPersonnel.id == token_data.id).first()
        if not ep or ep.therapist_id != group.therapist_id:
            raise HTTPException(status_code=403, detail="Not your group")
    else:
        raise HTTPException(status_code=403, detail="Unauthorized")


def _msg_to_dict(m: EPGroupMessage) -> dict:
    return {
        "type": "message",
        "id": m.id,
        "group_id": m.group_id,
        "sender_id": m.sender_id,
        "sender_role": m.sender_role,
        "sender_name": m.sender_name,
        "content": m.content,
        "patient_id": m.patient_id,
        "patient_name": m.patient_name,
        "is_claimed": m.is_claimed,
        "claimed_by_ep_id": m.claimed_by_ep_id,
        "claimed_by_name": m.claimed_by_name,
        "claimed_at": m.claimed_at.isoformat() if m.claimed_at else None,
        "created_at": m.created_at.isoformat(),
    }


# ─── REST: therapist gets (or creates) their EP group ────────────────────────

@ep_group_router.get("/my-group")
def get_my_ep_group(token: str = Query(...), db: Session = Depends(get_db)):
    therapist = _get_therapist(token, db)
    group = _get_or_create_group(therapist.id, db)
    return {"id": group.id, "therapist_id": group.therapist_id, "created_at": group.created_at}


# ─── REST: EP gets the group for their therapist ─────────────────────────────

@ep_group_router.get("/mine")
def get_my_group_as_ep(token: str = Query(...), db: Session = Depends(get_db)):
    ep = _get_ep(token, db)
    group = _get_or_create_group(ep.therapist_id, db)
    return {"id": group.id, "therapist_id": group.therapist_id, "created_at": group.created_at}


# ─── REST: message history ────────────────────────────────────────────────────

@ep_group_router.get("/{group_id}/messages")
def get_ep_group_messages(
    group_id: int,
    limit: int = 200,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    td = decode_access_token(token)
    group = db.query(EPGroup).filter(EPGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    _verify_access(td, group, db)

    messages = (
        db.query(EPGroupMessage)
        .filter(EPGroupMessage.group_id == group_id)
        .order_by(EPGroupMessage.created_at.asc())
        .limit(limit)
        .all()
    )
    return [_msg_to_dict(m) for m in messages]


# ─── REST: EP claims a message ("I'm visiting this patient") ─────────────────

@ep_group_router.post("/{group_id}/messages/{message_id}/claim")
async def claim_ep_group_message(
    group_id: int,
    message_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    ep = _get_ep(token, db)
    group = db.query(EPGroup).filter(EPGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if ep.therapist_id != group.therapist_id:
        raise HTTPException(status_code=403, detail="Not your group")

    msg = db.query(EPGroupMessage).filter(
        EPGroupMessage.id == message_id,
        EPGroupMessage.group_id == group_id,
    ).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    msg.is_claimed = True
    msg.claimed_by_ep_id = ep.id
    msg.claimed_by_name = ep.name
    msg.claimed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(msg)

    # Broadcast the updated message so all connected clients update their UI
    payload = _msg_to_dict(msg)
    payload["type"] = "claim_update"
    await ep_group_manager.broadcast(group_id, payload)

    return payload


# ─── WebSocket ────────────────────────────────────────────────────────────────

@ep_group_router.websocket("/ws/{group_id}")
async def websocket_ep_group(
    websocket: WebSocket,
    group_id: int,
    token: str = Query(...),
):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        token_data = decode_access_token(token)
        group = db.query(EPGroup).filter(EPGroup.id == group_id).first()
        if not group:
            await websocket.close(code=4004)
            return

        # Authorise
        if token_data.role == "therapist":
            if group.therapist_id != token_data.id:
                await websocket.close(code=4003)
                return
            user_obj = db.query(Therapist).filter(Therapist.id == token_data.id).first()
            sender_name = user_obj.name if user_obj else "Therapist"
            sender_role = "therapist"
        elif token_data.role == "emergency_personnel":
            ep = db.query(EmergencyPersonnel).filter(EmergencyPersonnel.id == token_data.id).first()
            if not ep or ep.therapist_id != group.therapist_id:
                await websocket.close(code=4003)
                return
            sender_name = ep.name
            sender_role = "emergency_personnel"
        else:
            await websocket.close(code=4003)
            return

        await ep_group_manager.connect(websocket, group_id)

        try:
            while True:
                data = await websocket.receive_text()
                payload = json.loads(data)
                content = payload.get("content", "").strip()
                if not content:
                    continue

                msg = EPGroupMessage(
                    group_id=group_id,
                    sender_id=token_data.id,
                    sender_role=sender_role,
                    sender_name=sender_name,
                    content=content,
                )
                db.add(msg)
                db.commit()
                db.refresh(msg)

                await ep_group_manager.broadcast(group_id, _msg_to_dict(msg))

        except WebSocketDisconnect:
            ep_group_manager.disconnect(websocket, group_id)

    except Exception:
        try:
            await websocket.close(code=4000)
        except Exception:
            pass
    finally:
        db.close()
