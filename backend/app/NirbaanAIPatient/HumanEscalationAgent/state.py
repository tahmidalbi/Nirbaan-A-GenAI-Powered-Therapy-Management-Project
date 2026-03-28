from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class ChatTurn(TypedDict):
    role: str
    content: str


class HumanEscalationState(TypedDict, total=False):
    # ── Core request / session info ──
    patient_id: int
    therapist_id: int
    thread_id: int
    user_message: str
    recent_chat_history: List[ChatTurn]

    # ── Context loaded from DB (no LLM) ──
    patient_name: str
    patient_conditions: str
    patient_conditions_description: str
    patient_address: str
    db_obsession_compulsion_pairs: List[Dict[str, Any]]
    db_latest_weekly_progress: Optional[Dict[str, Any]]

    # ── Router pass-through ──
    route: str

    # ── Verifier decision ──
    needs_human_help: bool
    verifier_reasoning: str

    # ── Generated helper message ──
    helper_message: str

    # ── Delivery status ──
    ep_group_message_id: Optional[int]
    delivery_error: str

    # ── Final response back to the patient ──
    final_response: str
