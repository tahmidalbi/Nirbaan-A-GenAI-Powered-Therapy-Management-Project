from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────────────
# Imaginal Cards
# ──────────────────────────────────────────────────────────────────────────────

class ERPImaginalCardCreate(BaseModel):
    content: str = Field(default="", max_length=10000)
    order_index: int = Field(default=0, ge=0)

    class Config:
        from_attributes = True


class ERPImaginalCardUpdate(BaseModel):
    content: Optional[str] = Field(None, max_length=10000)
    order_index: Optional[int] = Field(None, ge=0)

    class Config:
        from_attributes = True


class ERPImaginalCardResponse(BaseModel):
    id: int
    erp_item_id: int
    content: str
    order_index: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────────────────────────
# Session Note (legacy field on ERPItem)
# ──────────────────────────────────────────────────────────────────────────────

class ERPSessionNoteUpdate(BaseModel):
    session_exercise_note: Optional[str] = Field(None, max_length=10000)

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────────────────────────
# ERP Items
# ──────────────────────────────────────────────────────────────────────────────

class ERPItemCreate(BaseModel):
    obsession: str = Field(..., min_length=1, max_length=2000)
    compulsions: List[str] = Field(default_factory=list)
    suds: Optional[int] = Field(None, ge=0, le=100)

    class Config:
        from_attributes = True


class ERPItemUpdate(BaseModel):
    obsession: Optional[str] = Field(None, min_length=1, max_length=2000)
    compulsions: Optional[List[str]] = None
    suds: Optional[int] = Field(None, ge=0, le=100)

    class Config:
        from_attributes = True


class ERPItemResponse(BaseModel):
    id: int
    patient_id: int
    obsession: str
    compulsions: List[str]
    suds: Optional[int]
    session_exercise_note: Optional[str]

    # ✅ NEW: pointer used to show "latest report" under this obsession
    latest_session_id: Optional[int] = None

    imaginal_cards: List[ERPImaginalCardResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────────────────────────
# Live Sessions
# ──────────────────────────────────────────────────────────────────────────────

SessionStatus = Literal["running", "paused", "ending", "ended"]


class ERPLiveSessionResponse(BaseModel):
    id: int
    erp_item_id: int
    patient_id: int

    status: SessionStatus
    accumulated_seconds: float
    resumed_at: Optional[datetime]  # null when paused/ending/ended
    ended_at: Optional[datetime]
    created_at: datetime

    # ✅ NEW: check-in/agent timestamps
    last_checkin_at: Optional[datetime] = None
    last_agent_run_at: Optional[datetime] = None
    last_suds_at: Optional[datetime] = None

    # ✅ NEW: end-session debrief + reports
    patient_debrief_text: Optional[str] = None
    therapist_report_json: Optional[Dict[str, Any]] = None
    patient_feedback_json: Optional[Dict[str, Any]] = None
    report_version: int = 0

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────────────────────────
# SUDS Readings
# ──────────────────────────────────────────────────────────────────────────────

class ERPSUDSReadingCreate(BaseModel):
    suds_value: int = Field(..., ge=0, le=100)
    elapsed_seconds: float = Field(default=0.0, ge=0)

    class Config:
        from_attributes = True


class ERPSUDSReadingResponse(BaseModel):
    id: int
    session_id: int
    erp_item_id: int
    patient_id: int
    suds_value: int
    elapsed_seconds: float
    recorded_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────────────────────────
# Therapist-facing schemas
# ──────────────────────────────────────────────────────────────────────────────

class ERPPatientSummary(BaseModel):
    """Minimal patient info returned in the therapist ERP patient list."""
    patient_id: int
    patient_name: str
    patient_email: str
    item_count: int

    class Config:
        from_attributes = True


class ERPItemWithSUDSResponse(ERPItemResponse):
    """ERP item with full SUDS history, used in the therapist obsession-detail view."""
    suds_readings: List[ERPSUDSReadingResponse] = []

    # Optional: expose latest report quickly (if you want in therapist UI)
    latest_therapist_report_json: Optional[Dict[str, Any]] = None
    latest_patient_feedback_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────────────────────────
# Exercise Notes
# ──────────────────────────────────────────────────────────────────────────────

class ERPExerciseNoteCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)

    class Config:
        from_attributes = True


class ERPExerciseNoteResponse(BaseModel):
    id: int
    erp_item_id: int
    patient_id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────────────────────────
# Coach + Chat (LangGraph integration)
# ──────────────────────────────────────────────────────────────────────────────

# ---- Chat transcript (stored in DB) ----
ChatRole = Literal["patient", "coach", "system"]


class ERPChatMessageCreate(BaseModel):
    role: ChatRole
    content: str = Field(..., min_length=1, max_length=20000)
    intent: Optional[str] = Field(None, max_length=50)
    tags: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ERPChatMessageResponse(BaseModel):
    id: int
    session_id: int
    erp_item_id: int
    patient_id: int
    role: ChatRole
    content: str
    intent: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


class ERPSessionTranscriptResponse(BaseModel):
    session_id: int
    messages: List[ERPChatMessageResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


# ---- Coach strict JSON response (what frontend consumes) ----
NextActionType = Literal[
    "NONE",
    "SHOW_DEBRIEF_FORM",
    "RATE_SUDS_NOW",
    "CONTINUE",
    "DELAY_COMPULSION",
    "END_SESSION_CONFIRM",
]

CoachResponseType = Literal[
    "COACH_MESSAGE",
    "NO_MESSAGE",
]

CoachSource = Literal[
    "USER_MESSAGE",
    "CHECK_IN",
    "SYSTEM",
]


class NextAction(BaseModel):
    type: NextActionType = "NONE"
    payload: Dict[str, Any] = Field(default_factory=dict)


class CoachResponse(BaseModel):
    """
    Unified coach response used for:
    - live coaching (USER_MESSAGE)
    - timed check-ins (CHECK_IN)
    - end-session debrief prompt (SYSTEM)
    """
    type: CoachResponseType
    source: CoachSource
    coach_message: Optional[str] = None
    next_action: NextAction = Field(default_factory=NextAction)
    tags: List[str] = Field(default_factory=list)


# ---- Coach endpoints payloads ----

class ERPUserMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=20000)


class ERPEndClickedResponse(BaseModel):
    """
    Returned by: POST /erp/sessions/{session_id}/end-clicked
    Frontend:
      - appends response.coach_message to chat
      - if response.next_action.type == SHOW_DEBRIEF_FORM -> show debrief form UI
    """
    response: CoachResponse


class ERPDebriefSubmitRequest(BaseModel):
    patient_debrief_text: str = Field(..., min_length=1, max_length=20000)


# ---- Report JSON (stored in ERPLiveSession.*_json) ----

class TherapistReportJSON(BaseModel):
    session_overview: Dict[str, Any] = Field(default_factory=dict)
    suds_curve_summary: Optional[str] = None

    what_happened: List[str] = Field(default_factory=list)
    compulsions_urges: List[str] = Field(default_factory=list)
    response_prevention_successes: List[str] = Field(default_factory=list)
    avoidance_or_safety_behaviors: List[str] = Field(default_factory=list)

    key_learning: List[str] = Field(default_factory=list)
    recommend_next_step: Dict[str, Any] = Field(default_factory=dict)

    risk_flags: List[str] = Field(default_factory=list)

    # Cross-session analysis (null when no prior sessions exist)
    cross_session_overview: Optional[Dict[str, Any]] = None


class CrossSessionOverviewResult(BaseModel):
    """Pydantic model for the structured LLM call that generates cross-session analysis."""
    summary: Optional[str] = None
    common_patterns: List[str] = Field(default_factory=list)
    blockers_to_progress: List[str] = Field(default_factory=list)
    progress_signs: List[str] = Field(default_factory=list)


class PatientFeedbackJSON(BaseModel):
    reflection: List[str] = Field(default_factory=list)
    wins: List[str] = Field(default_factory=list)

    skill_to_practice: Optional[str] = None
    one_micro_goal_next_time: Optional[str] = None
    reminder: Optional[str] = None


class ERPEndReportResponse(BaseModel):
    """
    Returned by: POST /erp/sessions/{session_id}/end-report
    Backend saves:
      - patient_debrief_text
      - therapist_report_json
      - patient_feedback_json
      - erp_item.latest_session_id
    """
    patient_feedback: PatientFeedbackJSON
    therapist_report_saved: bool = True
    latest_session_id_updated: bool = True


# ──────────────────────────────────────────────────────────────────────────────
# Convenience schemas (optional)
# ──────────────────────────────────────────────────────────────────────────────

class ERPSUDSPoint(BaseModel):
    elapsed_seconds: float
    suds_value: int = Field(ge=0, le=100)
    recorded_at: datetime

    class Config:
        from_attributes = True


class ERPSessionWithTranscriptResponse(BaseModel):
    session: ERPLiveSessionResponse
    transcript: ERPSessionTranscriptResponse
    suds_readings: List[ERPSUDSReadingResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────────────────────────
# Patient session detail (for ended sessions — shows patient feedback)
# ──────────────────────────────────────────────────────────────────────────────

class ERPSessionDetailResponse(BaseModel):
    """Returned to the patient for session detail / history view."""
    session: ERPLiveSessionResponse
    suds_readings: List[ERPSUDSReadingResponse] = Field(default_factory=list)
    patient_feedback: Optional[PatientFeedbackJSON] = None

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────────────────────────
# Therapist session detail (includes report + transcript)
# ──────────────────────────────────────────────────────────────────────────────

class TherapistSessionDetailResponse(BaseModel):
    """Full session detail for therapist view: transcript, SUDS, both reports."""
    session: ERPLiveSessionResponse
    transcript: ERPSessionTranscriptResponse
    suds_readings: List[ERPSUDSReadingResponse] = Field(default_factory=list)
    therapist_report: Optional[TherapistReportJSON] = None
    patient_feedback: Optional[PatientFeedbackJSON] = None

    class Config:
        from_attributes = True