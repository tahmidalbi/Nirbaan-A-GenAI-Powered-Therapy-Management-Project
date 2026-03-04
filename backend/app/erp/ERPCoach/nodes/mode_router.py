# app/erp/ERPCoach/nodes/mode_router.py
from __future__ import annotations

from typing import Any, Dict, Literal


Mode = Literal["LIVE", "DEBRIEF_PROMPT", "REPORT"]


def mode_router(state: Dict[str, Any]) -> Mode:
    """
    Router used by StateGraph.add_conditional_edges on the 'mode_router' step.

    Expects:
      - event_type in state

    Returns:
      - "DEBRIEF_PROMPT" for END_SESSION_DEBRIEF_PROMPT
      - "REPORT" for END_SESSION_REPORT
      - "LIVE" for USER_MESSAGE / CHECK_IN (and any unknown defaults)
    """
    event_type = (state.get("event_type") or "").strip().upper()

    if event_type == "END_SESSION_DEBRIEF_PROMPT":
        return "DEBRIEF_PROMPT"
    if event_type == "END_SESSION_REPORT":
        return "REPORT"
    return "LIVE"