# app/erp/ERPCoach/state.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from app.erp.ERPCoach.events import EventType


class CoachState(TypedDict, total=False):
    """
    This is the shared state that flows through LangGraph nodes.
    Keep it JSON-serializable where possible, but it's okay to carry ORM objects
    in-memory during a single request (we do not checkpoint to disk).

    Required inputs when invoking graph:
      - session_id: int
      - event_type: EventType
      - user_message: str (optional for CHECK_IN)
      - patient_debrief_text: str (only for END_SESSION_REPORT)

    Outputs:
      - coach_response_json: dict (for LIVE + DEBRIEF_PROMPT)
      - therapist_report_json: dict (for REPORT)
      - patient_feedback_json: dict (for REPORT)
    """

    # --- Inputs ---
    session_id: int
    event_type: EventType
    user_message: str
    patient_debrief_text: str

    # --- DB-loaded context (load_context) ---
    session: Any
    item: Any
    erp_item_id: int
    patient_id: int

    obsession: str
    compulsions: List[str]
    exercise_text: Optional[str]

    messages_tail: List[Any]         # ERPChatMessage ORM objects
    transcript_block: str

    suds_recent: List[Any]           # ERPSUDSReading ORM objects
    suds_stats: Any                  # SudsStats dataclass from utils.summarization
    suds_stats_dict: Dict[str, Any]

    suds_peak: Optional[int]
    suds_latest: Optional[int]
    suds_previous: Optional[int]
    suds_delta: Optional[int]
    suds_slope_per_min: Optional[float]
    suds_trend_hint: Optional[str]

    last_suds_at: Any
    latest_report_session: Any
    prior_sessions: List[Any]
    prior_summaries: List[str]

    elapsed_seconds: float

    # --- Deterministic routing signals (compute_metrics) ---
    rate_reminder_flag: bool
    spike_flag: bool
    cooldown_ok: bool
    since_last_suds_seconds: Optional[float]
    since_last_agent_seconds: Optional[float]

    # --- Report bundle ---
    suds_points_block: str
    clipped_debrief_text: str
    report_inputs: Dict[str, Any]
    session_facts_text: str

    # --- LLM outputs ---
    coach_response: Any
    coach_response_json: Dict[str, Any]
    therapist_report: Any
    therapist_report_json: Dict[str, Any]
    patient_feedback: Any
    patient_feedback_json: Dict[str, Any]

    # --- Optional knobs ---
    message_limit: int
    suds_limit: int
    prior_sessions_limit: int
    max_chars_per_message: int
    rate_reminder_seconds: int
    checkin_cooldown_seconds: int
    spike_delta_threshold: int
    spike_slope_per_min_threshold: float

    # --- Optional injected objects (router uses this) ---
    db: Any
    storage: Any
    llm_client: Any