from __future__ import annotations

from typing import List, TypedDict


class ChatTurn(TypedDict):
    role: str
    content: str


class CentralState(TypedDict, total=False):
    patient_id: int
    therapist_id: int
    thread_id: int

    user_message: str
    recent_chat_history: List[ChatTurn]

    route: str
    router_unavailable: bool  # LLM router failed; message sent to the escalation check

    final_response: str