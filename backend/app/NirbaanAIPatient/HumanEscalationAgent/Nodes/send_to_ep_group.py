from __future__ import annotations

import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.chat.models import EPGroup, EPGroupMessage
from app.chat.ep_group_router import ep_group_manager, _msg_to_dict

log = logging.getLogger(__name__)


def send_to_ep_group_node(state: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """
    Persist the AI-generated helper message into the therapist's EP group chat
    and broadcast it to any connected WebSocket clients.

    This node:
    1. Gets or creates the therapist's EP group
    2. Creates an EPGroupMessage with sender_role='ai_agent'
    3. Tries to broadcast via WebSocket manager (best-effort)
    4. Returns a patient-facing confirmation message
    """

    therapist_id = state.get("therapist_id")
    patient_id = state.get("patient_id")
    patient_name = state.get("patient_name", "Unknown")
    helper_message = state.get("helper_message", "")

    if not therapist_id or not helper_message:
        return {
            "delivery_error": "Missing therapist_id or helper_message",
            "final_response": (
                "I've noted your request for human help. "
                "Your care team has been notified and someone will reach out to you soon. "
                "In the meantime, I'm still here if you need to talk."
            ),
        }

    # Get or create the EP group for this therapist
    group = db.query(EPGroup).filter(EPGroup.therapist_id == therapist_id).first()
    if not group:
        group = EPGroup(therapist_id=therapist_id)
        db.add(group)
        db.commit()
        db.refresh(group)

    # Create the message
    msg = EPGroupMessage(
        group_id=group.id,
        sender_id=None,
        sender_role="ai_agent",
        sender_name="Nirbaan AI",
        content=helper_message,
        patient_id=patient_id,
        patient_name=patient_name,
        is_claimed=False,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    # Best-effort WebSocket broadcast
    try:
        import asyncio

        payload = _msg_to_dict(msg)
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

        if loop and loop.is_running():
            loop.create_task(ep_group_manager.broadcast(group.id, payload))
        else:
            asyncio.run(ep_group_manager.broadcast(group.id, payload))
    except Exception as exc:
        log.warning("EP group broadcast failed (non-fatal): %s", exc)

    return {
        "ep_group_message_id": msg.id,
        "final_response": (
            "I understand you need help right now. "
            "I've alerted your care team's human helpers — one of them will be reaching out to you soon. "
            "Please stay where you are if you can. I'm still here with you while you wait."
        ),
    }
