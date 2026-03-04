# app/erp/ERPCoach/nodes/persist.py
from __future__ import annotations

from typing import Any, Dict, Optional

from app.erp.services.coach_storage import CoachStorage


def log_user_message(state: Dict[str, Any], *, storage: CoachStorage) -> Dict[str, Any]:
    """
    Persists the patient's message into erp_chat_messages.
    Called on USER_MESSAGE events before generating the coach reply.

    Expects:
      - session (ERPLiveSession)
      - user_message (str)
    """
    session = state["session"]
    msg = (state.get("user_message") or "").strip()
    if msg:
        storage.save_chat_message(
            session_id=session.id,
            erp_item_id=session.erp_item_id,
            patient_id=session.patient_id,
            role="patient",
            content=msg,
            intent="USER_MESSAGE",
            tags=[],
            commit=True,
        )
    return state


def log_coach_message(state: Dict[str, Any], *, storage: CoachStorage) -> Dict[str, Any]:
    """
    Persists the coach message into erp_chat_messages (unless NO_MESSAGE).

    Expects:
      - coach_response_json OR coach_response (from handlers)
      - session (ERPLiveSession)
    """
    session = state["session"]

    resp = state.get("coach_response_json") or {}
    if not resp:
        return state

    if resp.get("type") == "NO_MESSAGE":
        return state

    text = (resp.get("coach_message") or "").strip()
    if not text:
        return state

    storage.save_chat_message(
        session_id=session.id,
        erp_item_id=session.erp_item_id,
        patient_id=session.patient_id,
        role="coach",
        content=text,
        intent=resp.get("source"),
        tags=resp.get("tags") or [],
        commit=True,
    )
    return state


def log_debrief_prompt(state: Dict[str, Any], *, storage: CoachStorage) -> Dict[str, Any]:
    """
    When END_SESSION_DEBRIEF_PROMPT is generated, store that coach message
    as a system/coach message so transcript is complete.

    Uses coach_response_json.
    """
    session = state["session"]
    resp = state.get("coach_response_json") or {}
    if not resp or resp.get("type") == "NO_MESSAGE":
        return state

    text = (resp.get("coach_message") or "").strip()
    if not text:
        return state

    storage.save_chat_message(
        session_id=session.id,
        erp_item_id=session.erp_item_id,
        patient_id=session.patient_id,
        role="system",
        content=text,
        intent="DEBRIEF_PROMPT",
        tags=resp.get("tags") or ["debrief_prompt"],
        commit=True,
    )
    return state


def save_reports_update_latest(state: Dict[str, Any], *, storage: CoachStorage) -> Dict[str, Any]:
    """
    Final persistence step for END_SESSION_REPORT.

    Writes:
      - patient_debrief_text
      - therapist_report_json
      - patient_feedback_json
    to ERPLiveSession and sets ERPItem.latest_session_id = this session.

    Expects:
      - session (ERPLiveSession)
      - patient_debrief_text (str)
      - therapist_report_json (dict)
      - patient_feedback_json (dict)
    """
    session = state["session"]
    debrief = (state.get("patient_debrief_text") or "").strip()
    therapist_report_json = state.get("therapist_report_json") or {}
    patient_feedback_json = state.get("patient_feedback_json") or {}

    storage.save_end_session_reports(
        session_id=session.id,
        patient_debrief_text=debrief,
        therapist_report_json=therapist_report_json,
        patient_feedback_json=patient_feedback_json,
        commit=True,
    )

    storage.set_item_latest_session(session.erp_item_id, session.id, commit=True)
    return state