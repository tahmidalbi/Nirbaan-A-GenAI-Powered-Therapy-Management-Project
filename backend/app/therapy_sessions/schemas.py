from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TherapySessionCreate(BaseModel):
    patient_id: int
    session_date: str           # ISO date e.g. "2026-03-09"
    title: str
    transcript: str
    therapist_notes: Optional[str] = None


class TherapySessionUpdate(BaseModel):
    session_date: Optional[str] = None
    title: Optional[str] = None
    transcript: Optional[str] = None
    therapist_notes: Optional[str] = None


class TherapySessionTherapistResponse(BaseModel):
    """Full response for therapist — includes private therapist_notes."""
    id: int
    patient_id: int
    therapist_id: int
    session_date: Optional[str] = None
    session_number: Optional[int] = None
    title: Optional[str] = None
    transcript: Optional[str] = None
    therapist_notes: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TherapySessionPatientResponse(BaseModel):
    """Patient-facing response — therapist_notes are excluded."""
    id: int
    patient_id: int
    session_date: Optional[str] = None
    session_number: Optional[int] = None
    title: Optional[str] = None
    transcript: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
