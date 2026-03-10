from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import (
    AnalysisRunStatus,
    ClarificationStatus,
    TherapistChatRole,
)


# ------------------------------------------------------------------
# Therapist chat schemas
# ------------------------------------------------------------------

class TherapistChatSendRequest(BaseModel):
    thread_id: Optional[int] = Field(
        default=None,
        description="Existing chat thread ID. If null, backend may create a new thread.",
    )
    patient_id: Optional[int] = Field(
        default=None,
        description="Optional patient being discussed in this chat thread.",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="Therapist message sent to the AI assistant.",
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty.")
        return value


class TherapistAIChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    thread_id: int
    role: TherapistChatRole
    content: str
    created_at: datetime


class TherapistAIChatThreadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    therapist_id: int
    patient_id: Optional[int] = None
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TherapistAIChatHistoryResponse(BaseModel):
    thread: TherapistAIChatThreadOut
    messages: List[TherapistAIChatMessageOut]


# ------------------------------------------------------------------
# Internal analysis workflow schemas
# ------------------------------------------------------------------

class StartPatientAnalysisRequest(BaseModel):
    patient_id: int = Field(..., gt=0)
    thread_id: Optional[int] = Field(default=None)
    analysis_goal: Optional[str] = Field(
        default=None,
        max_length=4000,
        description="Optional therapist goal/focus for analysis.",
    )

    @field_validator("analysis_goal")
    @classmethod
    def validate_analysis_goal(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        return value or None


class SubmitClarificationAnswerRequest(BaseModel):
    answer: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="Therapist answer to the AI clarification question.",
    )

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Answer cannot be empty.")
        return value


class PatientAnalysisClarificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    analysis_run_id: int
    question: str
    answer: Optional[str] = None
    status: ClarificationStatus
    created_at: datetime
    answered_at: Optional[datetime] = None


class PatientAnalysisRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    therapist_id: int
    patient_id: int
    thread_id: Optional[int] = None
    status: AnalysisRunStatus
    analysis_goal: Optional[str] = None
    draft_analysis: Optional[str] = None
    analysis_summary: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ------------------------------------------------------------------
# Therapist chat send response
# ------------------------------------------------------------------

class TherapistChatSendResponse(BaseModel):
    thread_id: int
    user_message: TherapistAIChatMessageOut
    assistant_message: Optional[TherapistAIChatMessageOut] = None

    needs_clarification: bool = False
    clarification: Optional[PatientAnalysisClarificationOut] = None
    analysis_run: Optional[PatientAnalysisRunOut] = None


# ------------------------------------------------------------------
# Analysis workflow responses
# ------------------------------------------------------------------

class StartPatientAnalysisResponse(BaseModel):
    run: PatientAnalysisRunOut
    needs_clarification: bool = False
    clarification: Optional[PatientAnalysisClarificationOut] = None
    analysis_summary: Optional[str] = None


class ResumePatientAnalysisResponse(BaseModel):
    run: PatientAnalysisRunOut
    needs_clarification: bool = False
    clarification: Optional[PatientAnalysisClarificationOut] = None
    analysis_summary: Optional[str] = None