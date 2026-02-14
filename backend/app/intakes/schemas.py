from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class IssueItem(BaseModel):
    """Individual issue with severity rating"""
    issue: str = Field(..., min_length=1, max_length=500)
    severity: int = Field(..., ge=1, le=10, description="Severity rating from 1-10")


class PatientIntakeCreate(BaseModel):
    """Schema for creating a patient intake"""
    # NOTE: patient_id / therapist_id usually come from auth context or route params.
    # If your POST endpoint expects them in body, add them here.
    your_story: str = Field(..., min_length=10)
    when_started: str = Field(..., min_length=1, max_length=500)

    tried_previous_therapy: bool = False
    previous_therapy_details: Optional[str] = None

    taken_medication: bool = False
    medication_details: Optional[str] = None

    affected_life_areas: Optional[str] = None
    other_conditions: Optional[str] = None

    issues: List[IssueItem] = Field(default_factory=list, min_length=1)


class PatientIntakeUpdate(BaseModel):
    """Schema for updating a patient intake"""
    your_story: Optional[str] = None
    when_started: Optional[str] = None

    tried_previous_therapy: Optional[bool] = None
    previous_therapy_details: Optional[str] = None

    taken_medication: Optional[bool] = None
    medication_details: Optional[str] = None

    affected_life_areas: Optional[str] = None
    other_conditions: Optional[str] = None

    issues: Optional[List[IssueItem]] = None


class PatientIntakeResponse(BaseModel):
    """Schema for patient intake response (includes AI summary fields)"""
    id: int
    patient_id: int
    therapist_id: int

    your_story: str
    when_started: str

    tried_previous_therapy: bool
    previous_therapy_details: Optional[str]

    taken_medication: bool
    medication_details: Optional[str]

    affected_life_areas: Optional[str]
    other_conditions: Optional[str]

    issues: List[Dict[str, Any]]

    # -----------------------
    # AI summary fields
    # -----------------------
    # pending | running | done | failed
    ai_summary_status: str
    ai_summary_text: Optional[str] = None
    ai_summary_structured: Optional[Dict[str, Any]] = None
    ai_summary_error: Optional[str] = None
    ai_summary_version: int
    ai_summary_updated_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PatientIntakeListItem(BaseModel):
    """Brief intake info for listing (includes summary status for UI badges)"""
    id: int
    patient_id: int
    therapist_id: int

    ai_summary_status: str
    ai_summary_updated_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IntakeSubmitResponse(BaseModel):
    """Return after submit/retry so frontend can start polling."""
    intake_id: int
    ai_summary_status: str
