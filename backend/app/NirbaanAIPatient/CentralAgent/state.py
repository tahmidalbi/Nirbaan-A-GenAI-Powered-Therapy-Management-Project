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

    final_response: str