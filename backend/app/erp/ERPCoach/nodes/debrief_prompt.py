# app/erp/ERPCoach/nodes/debrief_prompt.py
from __future__ import annotations

from typing import Any, Dict

from app.erp.ERPCoach.llm.client import LLMClient
from app.erp.schemas import CoachResponse
from app.erp.ERPCoach.prompts.debrief_prompt import build_debrief_prompt


def send_debrief_prompt(state: Dict[str, Any], *, llm: LLMClient) -> Dict[str, Any]:
    """
    Node used in DEBRIEF_PROMPT mode.

    When patient clicks "End Session" (Option A), your backend:
      1) marks session.status="ending" and stops timer (session_service.end_clicked)
      2) calls LangGraph with event_type="END_SESSION_DEBRIEF_PROMPT"
      3) this node generates a SYSTEM coach message + next_action SHOW_DEBRIEF_FORM

    Frontend:
      - appends coach_message to chat
      - sees next_action=SHOW_DEBRIEF_FORM
      - renders the debrief form UI (not a normal text bubble)
    """
    prompt = build_debrief_prompt(
        obsession=state.get("obsession", ""),
        compulsions=state.get("compulsions", []) or [],
        exercise_text=state.get("exercise_text"),
        elapsed_seconds=float(state.get("elapsed_seconds", 0.0)),
        suds_peak=state.get("suds_peak"),
        suds_latest=state.get("suds_latest"),
    )

    resp = llm.structured_call(schema=CoachResponse, prompt=prompt)
    state["coach_response"] = resp
    state["coach_response_json"] = resp.model_dump()
    return state