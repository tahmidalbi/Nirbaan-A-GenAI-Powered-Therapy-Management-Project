from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict


class ChatTurn(TypedDict):
    role: str
    content: str


class ObsessionCompulsionPair(TypedDict):
    erp_item_id: int
    obsession: str
    compulsions: List[str]


class WeeklyProgressData(TypedDict, total=False):
    id: int
    week_number: int
    week_start_date: str
    detailed_progress: str
    homework_reflection: str
    suds_snapshot: Optional[List[dict]]


class RetrievedChunk(TypedDict, total=False):
    content: str
    source: str
    score: float
    metadata: Dict[str, Any]


class WebResult(TypedDict, total=False):
    title: str
    content: str
    url: str
    source: str


class PsychoeducationState(TypedDict, total=False):
    # ------------------------------------------------------------------
    # Core request/session info
    # ------------------------------------------------------------------
    patient_id: int
    therapist_id: int
    thread_id: int
    user_message: str

    # ------------------------------------------------------------------
    # Short-term memory loaded from DB
    # ------------------------------------------------------------------
    recent_chat_history: List[ChatTurn]

    # ------------------------------------------------------------------
    # Raw DB context loaded by db_picker.py
    # ------------------------------------------------------------------
    db_obsession_compulsion_pairs: List[ObsessionCompulsionPair]
    db_latest_weekly_progress: Optional[WeeklyProgressData]
    db_last_therapy_session: Optional[Dict[str, Any]]

    # ------------------------------------------------------------------
    # Selected DB context chosen by context_selector.py
    # ------------------------------------------------------------------
    needs_personalization: bool
    selected_obsession_compulsion_pairs: List[ObsessionCompulsionPair]
    selected_progress_snippets: List[str]
    selected_db_context_summary: str
    selected_last_therapy_session: Optional[Dict[str, Any]]

    # ------------------------------------------------------------------
    # Retrieval query state
    # ------------------------------------------------------------------
    retrieval_query: str
    original_retrieval_query: str
    refined_query_history: List[str]

    # ------------------------------------------------------------------
    # KB retrieval output
    # ------------------------------------------------------------------
    kb_chunks: List[RetrievedChunk]
    kb_context_summary: str

    # ------------------------------------------------------------------
    # Sufficiency checking
    # ------------------------------------------------------------------
    retrieval_sufficient: bool
    insufficiency_reason: str
    missing_concept: str

    # ------------------------------------------------------------------
    # Retry / loop control
    # ------------------------------------------------------------------
    retry_count: int
    max_retries: int
    next_step: Literal["generate", "refine_query", "web_search"]

    # ------------------------------------------------------------------
    # Web fallback
    # ------------------------------------------------------------------
    web_used: bool
    web_results: List[WebResult]
    web_context_summary: str

    # ------------------------------------------------------------------
    # Final generation
    # ------------------------------------------------------------------
    final_grounding_summary: str
    final_response: str

    # ------------------------------------------------------------------
    # Metadata for API / logging / frontend
    # ------------------------------------------------------------------
    used_sources: List[str]
    error_message: str