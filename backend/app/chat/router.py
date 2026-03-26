from __future__ import annotations

import json
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status, Query
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.auth.utils import decode_access_token
from app.therapists.models import Therapist
from app.patients.models import Patient
from app.chat.models import ChatGroup, ChatGroupMember, ChatMessage
from app.chat.schemas import (
    ChatGroupCreate,
    ChatGroupMemberAdd,
    ChatGroupOut,
    ChatGroupMemberOut,
    ChatMessageOut,
)
from app.chat.manager import manager

router = APIRouter(prefix="/chat", tags=["Chat"])


# ─── helpers ────────────────────────────────────────────────────────────────


def _get_therapist(token: str, db: Session) -> Therapist:
    token_data = decode_access_token(token)
    if token_data.role != "therapist":
        raise HTTPException(status_code=403, detail="Therapists only")
    therapist = db.query(Therapist).filter(Therapist.id == token_data.id).first()
    if not therapist:
        raise HTTPException(status_code=404, detail="Therapist not found")
    return therapist


def _get_patient(token: str, db: Session) -> Patient:
    token_data = decode_access_token(token)
    if token_data.role != "patient":
        raise HTTPException(status_code=403, detail="Patients only")
    patient = db.query(Patient).filter(Patient.id == token_data.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


def _get_user_from_token(token: str, db: Session):
    """Return (user_obj, role) from a JWT. Works for both therapists and patients."""
    token_data = decode_access_token(token)
    if token_data.role == "therapist":
        user = db.query(Therapist).filter(Therapist.id == token_data.id).first()
        return user, "therapist"
    elif token_data.role == "patient":
        user = db.query(Patient).filter(Patient.id == token_data.id).first()
        return user, "patient"
    raise HTTPException(status_code=403, detail="Unsupported role")


# ─── REST: group management (therapist) ─────────────────────────────────────


@router.post("/groups", response_model=ChatGroupOut, status_code=201)
def create_group(
    payload: ChatGroupCreate,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    therapist = _get_therapist(token, db)
    group = ChatGroup(name=payload.name, therapist_id=therapist.id)
    db.add(group)
    db.commit()
    db.refresh(group)
    return ChatGroupOut(
        id=group.id,
        name=group.name,
        therapist_id=group.therapist_id,
        created_at=group.created_at,
        member_count=0,
    )


@router.get("/groups", response_model=List[ChatGroupOut])
def list_groups_therapist(
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    therapist = _get_therapist(token, db)
    groups = db.query(ChatGroup).filter(ChatGroup.therapist_id == therapist.id).all()
    result = []
    for g in groups:
        count = db.query(ChatGroupMember).filter(ChatGroupMember.group_id == g.id).count()
        result.append(
            ChatGroupOut(
                id=g.id,
                name=g.name,
                therapist_id=g.therapist_id,
                created_at=g.created_at,
                member_count=count,
            )
        )
    return result


@router.delete("/groups/{group_id}", status_code=204)
def delete_group(
    group_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    therapist = _get_therapist(token, db)
    group = db.query(ChatGroup).filter(
        ChatGroup.id == group_id, ChatGroup.therapist_id == therapist.id
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    db.delete(group)
    db.commit()


@router.post("/groups/{group_id}/members", response_model=ChatGroupMemberOut, status_code=201)
def add_member(
    group_id: int,
    payload: ChatGroupMemberAdd,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    therapist = _get_therapist(token, db)
    group = db.query(ChatGroup).filter(
        ChatGroup.id == group_id, ChatGroup.therapist_id == therapist.id
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    patient = db.query(Patient).filter(
        Patient.id == payload.patient_id,
        Patient.therapist_id == therapist.id,
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found or not yours")
    existing = db.query(ChatGroupMember).filter(
        ChatGroupMember.group_id == group_id,
        ChatGroupMember.patient_id == payload.patient_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Patient already in group")
    member = ChatGroupMember(group_id=group_id, patient_id=payload.patient_id)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.delete("/groups/{group_id}/members/{patient_id}", status_code=204)
def remove_member(
    group_id: int,
    patient_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    therapist = _get_therapist(token, db)
    group = db.query(ChatGroup).filter(
        ChatGroup.id == group_id, ChatGroup.therapist_id == therapist.id
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    member = db.query(ChatGroupMember).filter(
        ChatGroupMember.group_id == group_id,
        ChatGroupMember.patient_id == patient_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(member)
    db.commit()


@router.get("/groups/{group_id}/members")
def list_members(
    group_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    token_data = decode_access_token(token)
    group = db.query(ChatGroup).filter(ChatGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    members = db.query(ChatGroupMember).filter(ChatGroupMember.group_id == group_id).all()
    result = []
    for m in members:
        patient = db.query(Patient).filter(Patient.id == m.patient_id).first()
        result.append({
            "id": m.id,
            "patient_id": m.patient_id,
            "patient_name": patient.name if patient else "Unknown",
            "joined_at": m.joined_at.isoformat(),
        })
    return result


# ─── REST: groups for patients ───────────────────────────────────────────────


@router.get("/groups/patient/mine")
def list_groups_patient(
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    patient = _get_patient(token, db)
    memberships = db.query(ChatGroupMember).filter(ChatGroupMember.patient_id == patient.id).all()
    result = []
    for m in memberships:
        group = db.query(ChatGroup).filter(ChatGroup.id == m.group_id).first()
        if group:
            count = db.query(ChatGroupMember).filter(ChatGroupMember.group_id == group.id).count()
            result.append({
                "id": group.id,
                "name": group.name,
                "therapist_id": group.therapist_id,
                "created_at": group.created_at.isoformat(),
                "member_count": count,
            })
    return result


# ─── REST: message history ───────────────────────────────────────────────────


@router.get("/groups/{group_id}/messages", response_model=List[ChatMessageOut])
def get_messages(
    group_id: int,
    limit: int = 100,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    token_data = decode_access_token(token)
    group = db.query(ChatGroup).filter(ChatGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # verify access
    if token_data.role == "therapist":
        if group.therapist_id != token_data.id:
            raise HTTPException(status_code=403, detail="Not your group")
    elif token_data.role == "patient":
        membership = db.query(ChatGroupMember).filter(
            ChatGroupMember.group_id == group_id,
            ChatGroupMember.patient_id == token_data.id,
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="Not a member of this group")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.group_id == group_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
        .all()
    )
    return messages


# ─── WebSocket ───────────────────────────────────────────────────────────────


@router.websocket("/ws/{group_id}")
async def websocket_chat(
    websocket: WebSocket,
    group_id: int,
    token: str = Query(...),
):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        token_data = decode_access_token(token)
        group = db.query(ChatGroup).filter(ChatGroup.id == group_id).first()
        if not group:
            await websocket.close(code=4004)
            return

        # Authorise
        if token_data.role == "therapist":
            if group.therapist_id != token_data.id:
                await websocket.close(code=4003)
                return
            user = db.query(Therapist).filter(Therapist.id == token_data.id).first()
            sender_name = user.name if user else "Therapist"
        elif token_data.role == "patient":
            membership = db.query(ChatGroupMember).filter(
                ChatGroupMember.group_id == group_id,
                ChatGroupMember.patient_id == token_data.id,
            ).first()
            if not membership:
                await websocket.close(code=4003)
                return
            user = db.query(Patient).filter(Patient.id == token_data.id).first()
            sender_name = user.name if user else "Patient"
        else:
            await websocket.close(code=4003)
            return

        await manager.connect(websocket, group_id)

        # Notify others that user joined
        await manager.broadcast(group_id, {
            "type": "system",
            "content": f"{sender_name} joined the chat",
            "group_id": group_id,
        })

        try:
            while True:
                data = await websocket.receive_text()
                payload = json.loads(data)
                content = payload.get("content", "").strip()
                if not content:
                    continue

                # Persist message
                msg = ChatMessage(
                    group_id=group_id,
                    sender_id=token_data.id,
                    sender_role=token_data.role,
                    sender_name=sender_name,
                    content=content,
                )
                db.add(msg)
                db.commit()
                db.refresh(msg)

                # Broadcast to all members in group
                await manager.broadcast(group_id, {
                    "type": "message",
                    "id": msg.id,
                    "group_id": group_id,
                    "sender_id": token_data.id,
                    "sender_role": token_data.role,
                    "sender_name": sender_name,
                    "content": content,
                    "created_at": msg.created_at.isoformat(),
                })
        except WebSocketDisconnect:
            manager.disconnect(websocket, group_id)
            await manager.broadcast(group_id, {
                "type": "system",
                "content": f"{sender_name} left the chat",
                "group_id": group_id,
            })
    except Exception as e:
        try:
            await websocket.close(code=4000)
        except Exception:
            pass
    finally:
        db.close()
