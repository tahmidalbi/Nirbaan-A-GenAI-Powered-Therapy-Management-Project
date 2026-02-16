from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class TranscriptEntry(BaseModel):
    speaker: str = Field(..., min_length=1, max_length=100, description="Speaker identifier (e.g., 'therapist', 'patient')")
    text: str = Field(..., min_length=1, description="Text content of the transcript entry")
    emotion: Optional[str] = Field(None, max_length=50, description="Detected emotion (e.g., 'happy', 'sad', 'anxious')")
    timestamp: datetime = Field(..., description="Timestamp of when this entry was spoken")

class AppendTranscriptRequest(BaseModel):
    transcript_entry: TranscriptEntry

class TherapySessionCreate(BaseModel):
    therapist_id: int
    patient_id: int

class TherapySessionResponse(BaseModel):
    id: int
    therapist_id: int
    patient_id: int
    transcript: List[dict]
    started_at: datetime
    ended_at: Optional[datetime]

    class Config:
        from_attributes = True
