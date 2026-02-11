from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

class InitialConditionCreate(BaseModel):
    initial_condition: str

class WeeklyProgressCreate(BaseModel):
    week_number: int
    progress_text: str

class PatientProgressResponse(BaseModel):
    id: int
    patient_id: int
    initial_condition: Optional[str]
    weekly_progress: Dict[str, str]
    current_week: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TherapistNoteCreate(BaseModel):
    patient_id: int
    week_key: str  # "initial" or "week_1", "week_2", etc.
    note_text: Optional[str] = None

class TherapistNoteUpdate(BaseModel):
    week_key: str
    note_text: Optional[str] = None

class AIProtocolUpdate(BaseModel):
    patient_id: int
    ai_protocol_instruction: str

class TherapistNoteResponse(BaseModel):
    id: int
    patient_id: int
    therapist_id: int
    week_notes: Dict[str, str]
    ai_protocol_instruction: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PatientProgressHistory(BaseModel):
    patient_id: int
    patient_name: str
    patient_email: str
    conditions: str
    initial_condition: Optional[str]
    weekly_progress: Dict[str, str]
    current_week: int
    therapist_note: Optional[TherapistNoteResponse]

    class Config:
        from_attributes = True
