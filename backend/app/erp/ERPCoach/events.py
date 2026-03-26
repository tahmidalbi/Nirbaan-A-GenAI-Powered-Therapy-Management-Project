# app/erp/ERPCoach/events.py
from __future__ import annotations

from typing import Final, Literal

# Event types your backend can call the graph with.
EVENT_USER_MESSAGE: Final[str] = "USER_MESSAGE"
EVENT_CHECK_IN: Final[str] = "CHECK_IN"
EVENT_SUDS_SUBMITTED: Final[str] = "SUDS_SUBMITTED"
EVENT_END_SESSION_DEBRIEF_PROMPT: Final[str] = "END_SESSION_DEBRIEF_PROMPT"
EVENT_END_SESSION_REPORT: Final[str] = "END_SESSION_REPORT"

EventType = Literal[
    "USER_MESSAGE",
    "CHECK_IN",
    "SUDS_SUBMITTED",
    "END_SESSION_DEBRIEF_PROMPT",
    "END_SESSION_REPORT",
]


def normalize_event_type(value: str | None) -> EventType:
    v = (value or "").strip().upper()
    if v == EVENT_CHECK_IN:
        return "CHECK_IN"
    if v == EVENT_SUDS_SUBMITTED:
        return "SUDS_SUBMITTED"
    if v == EVENT_END_SESSION_DEBRIEF_PROMPT:
        return "END_SESSION_DEBRIEF_PROMPT"
    if v == EVENT_END_SESSION_REPORT:
        return "END_SESSION_REPORT"
    return "USER_MESSAGE"