from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class SessionStart(BaseModel):
    therapist_id: int
    patient_id: int

class TranscriptAppend(BaseModel):
    speaker: str = Field(..., pattern="^(therapist|patient)$")
    text: str = Field(..., min_length=1, max_length=10000)

class TranscriptResponse(BaseModel):
    id: int
    session_id: int
    speaker: str
    text: str
    timestamp: datetime
    confidence: Optional[float] = None

    class Config:
        from_attributes = True

class SessionAnalysisResponse(BaseModel):
    id: int
    session_id: int
    summary: str
    detected_topics: list
    therapist_interventions: list
    patient_emotions: list
    homeworks: list
    created_at: datetime

    class Config:
        from_attributes = True

class SessionResponse(BaseModel):
    id: int
    therapist_id: int
    patient_id: int
    started_at: datetime
    ended_at: Optional[datetime]
    transcripts: List[TranscriptResponse] = []
    analysis: Optional[SessionAnalysisResponse] = None

    class Config:
        from_attributes = True
