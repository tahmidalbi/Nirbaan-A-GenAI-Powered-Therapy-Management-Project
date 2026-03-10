from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict


class ChatTurn(TypedDict):
    role: str
    content: str


class ObsessionCompulsionPair(TypedDict):
    erp_item_id: int
    obsession: str
    compulsions: List[str]
    latest_session_id: Optional[int]
    suds: Optional[int]


class WeeklyProgressData(TypedDict, total=False):
    id: int
    week_number: int
    week_start_date: str
    detailed_progress: str
    homework_reflection: str
    suds_snapshot: Optional[List[dict]]


class FearLadderItemData(TypedDict):
    id: int
    item: str
    suds: int
    order_index: int


class FearLadderData(TypedDict, total=False):
    id: int
    status: str
    created_at: Optional[str]
    items: List[FearLadderItemData]


class RetrievedChunk(TypedDict, total=False):
    content: str
    source: str
    score: float
    metadata: Dict[str, Any]


class NirbaanAITherapistState(TypedDict, total=False):
    # ------------------------------------------------------------------
    # Core request / chat / run info
    # ------------------------------------------------------------------
    therapist_id: int
    patient_id: int
    thread_id: int
    analysis_run_id: int

    user_message: str
    recent_chat_history: List[ChatTurn]

    analysis_goal: str

    # ------------------------------------------------------------------
    # Loaded patient context
    # ------------------------------------------------------------------
    latest_weekly_progress: Optional[WeeklyProgressData]
    initial_fear_ladder: Optional[FearLadderData]
    obsession_compulsion_pairs: List[ObsessionCompulsionPair]
    patient_context_summary: str

    # ------------------------------------------------------------------
    # KB retrieval
    # ------------------------------------------------------------------
    retrieval_query: str
    kb_chunks: List[RetrievedChunk]
    kb_context_summary: str

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------
    draft_analysis: str
    analysis_summary: str

    # ------------------------------------------------------------------
    # Human-in-the-loop clarification
    # ------------------------------------------------------------------
    needs_clarification: bool
    clarification_question: str
    clarification_answer: str

    # ------------------------------------------------------------------
    # Final output returned to therapist chat
    # ------------------------------------------------------------------
    final_analysis: str
    final_response: str

    # ------------------------------------------------------------------
    # Metadata / logging
    # ------------------------------------------------------------------
    used_sources: List[str]
    error_message: str
    status: Literal[
        "running",
        "needs_clarification",
        "completed",
        "failed",
    ]