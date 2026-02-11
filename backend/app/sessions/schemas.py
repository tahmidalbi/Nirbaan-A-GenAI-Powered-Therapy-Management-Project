"""
Session Schemas - Request and Response models
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


class SessionCreate(BaseModel):
    """Schema for creating a new session"""
    patient_id: int
    week_number: int
    transcript: str = Field(..., min_length=1)
    session_date: Optional[datetime] = None


class SessionUpdate(BaseModel):
    """Schema for updating an existing session"""
    transcript: str = Field(..., min_length=1)


class SessionResponse(BaseModel):
    """Schema for session response"""
    id: int
    patient_id: int
    therapist_id: int
    week_number: int
    session_date: datetime
    transcript: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SessionListItem(BaseModel):
    """Schema for session list item (for sidebar)"""
    id: int
    week_number: int
    session_date: datetime
    
    class Config:
        from_attributes = True


class PatientSessionData(BaseModel):
    """Schema for patient session data (therapist view)"""
    patient_id: int
    patient_name: str
    patient_email: str
    sessions: List[SessionListItem]
