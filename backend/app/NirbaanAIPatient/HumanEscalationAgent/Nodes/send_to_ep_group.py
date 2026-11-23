from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.chat.models import EPGroup, EPGroupMessage
from app.chat.ep_group_router import ep_group_manager, _msg_to_dict

log = logging.getLogger(__name__)

# During an API outage every message may fall back to escalation. Send at most one
# "safety check unavailable" alert per patient in this window (confirmed alerts are never held back).
FALLBACK_ALERT_COOLDOWN_SECONDS = float(os.getenv("ESCALATION_FALLBACK_ALERT_COOLDOWN_SECONDS", "1800"))
_last_fallback_alert: Dict[Any, float] = {}  # patient_id -> time.monotonic() of last saved fallback alert
_cooldown_lock = threading.Lock()

# Patient-facing replies. They say only what is known: the alert was (or was not) saved in the
# care team's support chat. They never promise that someone has seen it or will respond soon.
ALERT_SENT_RESPONSE = (
    "I understand you need help right now. I've sent an alert to your care team's support chat, "
    "but I can't confirm when someone will see it. "
    "If you are in immediate danger, please contact your local emergency services now. I'm still here with you."
)
FALLBACK_ALERT_SENT_RESPONSE = (
    "I'm having trouble checking your message right now, so I've sent an alert to your care team's "
    "support chat just in case. I can't confirm when someone will see it. "
    "If you are in immediate danger, please contact your local emergency services now."
)
FALLBACK_ALERT_RECENT_RESPONSE = (
    "I'm having trouble checking your message right now. An alert was already sent to your care team's "
    "support chat a short time ago. "
    "If you are in immediate danger, please contact your local emergency services now."
)
ALERT_FAILED_RESPONSE = (
    "I'm sorry — I couldn't send an alert to your care team just now. "
    "If you are in immediate danger, please contact your local emergency services now, "
    "or reach out to someone you trust."
)


def send_to_ep_group_node(state: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """
    Persist the AI-generated helper message into the therapist's EP group chat
    and broadcast it to any connected WebSocket clients.

    This node:
    1. Gets or creates the therapist's EP group
    2. Creates an EPGroupMessage with sender_role='ai_agent'
    3. Tries to broadcast via WebSocket manager (best-effort)
    4. Returns a patient-facing message that says the care team was alerted
       only if the alert was actually saved
    """

    therapist_id = state.get("therapist_id")
    patient_id = state.get("patient_id")
    patient_name = state.get("patient_name", "Unknown")
    helper_message = state.get("helper_message", "")
    is_fallback = bool(state.get("verification_unavailable"))

    if not therapist_id or not helper_message:
        return {
            "delivery_error": "Missing therapist_id or helper_message",
            "final_response": ALERT_FAILED_RESPONSE,
        }

    if is_fallback:
        with _cooldown_lock:
            last = _last_fallback_alert.get(patient_id)
        if last is not None and time.monotonic() - last < FALLBACK_ALERT_COOLDOWN_SECONDS:
            return {
                "delivery_error": "Fallback alert already sent recently; not repeated",
                "final_response": FALLBACK_ALERT_RECENT_RESPONSE,
            }

    try:
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
    except Exception as exc:
        db.rollback()
        log.error("Could not save EP alert for patient %s: %s", patient_id, exc)
        return {
            "delivery_error": f"Alert not saved: {type(exc).__name__}",
            "final_response": ALERT_FAILED_RESPONSE,
        }

    if is_fallback:
        with _cooldown_lock:
            _last_fallback_alert[patient_id] = time.monotonic()

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
        "final_response": FALLBACK_ALERT_SENT_RESPONSE if is_fallback else ALERT_SENT_RESPONSE,
    }
