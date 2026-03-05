# app/erp/ERPCoach/nodes/finalize_json.py
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, ValidationError

from app.erp.schemas import CoachResponse, TherapistReportJSON, PatientFeedbackJSON


def finalize_coach_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures coach response is valid and always present as a dict.

    Expects:
      - coach_response_json OR coach_response

    Produces:
      - coach_response_json: dict (always)
    """
    if "coach_response_json" in state and isinstance(state["coach_response_json"], dict):
        # validate it
        try:
            CoachResponse.model_validate(state["coach_response_json"])
            return state
        except ValidationError:
            pass

    resp_obj = state.get("coach_response")
    if resp_obj is not None:
        try:
            if isinstance(resp_obj, CoachResponse):
                state["coach_response_json"] = resp_obj.model_dump()
                return state
        except Exception:
            pass

    # last fallback: safe NO_MESSAGE
    state["coach_response_json"] = {
        "type": "NO_MESSAGE",
        "source": state.get("event_type", "SYSTEM"),
        "coach_message": None,
        "next_action": {"type": "NONE", "payload": {}},
        "tags": ["finalize_fallback"],
    }
    return state


def finalize_reports(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates therapist_report_json and patient_feedback_json before persistence.

    If invalid, it raises ValidationError — you want to notice during dev.
    (In production you could catch and re-run repair.)
    """
    if "therapist_report_json" in state:
        TherapistReportJSON.model_validate(state["therapist_report_json"])
    if "patient_feedback_json" in state:
        PatientFeedbackJSON.model_validate(state["patient_feedback_json"])
    return state