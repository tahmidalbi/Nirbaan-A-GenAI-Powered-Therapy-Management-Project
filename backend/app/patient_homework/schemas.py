from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class HomeworkItemBase(BaseModel):
    task: str
    rationale: str
    frequency: str


class HomeworkItemCreate(HomeworkItemBase):
    pass


class HomeworkItemUpdate(HomeworkItemBase):
    pass


class PatientHomeworkResponse(BaseModel):
    id: int
    patient_id: int
    session_id: int
    task: str
    rationale: str
    frequency: str
    week_number: int
    status: str
    created_at: datetime
    approved_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    completed_at: Optional[datetime] = None
    patient_notes: Optional[str] = None

    class Config:
        from_attributes = True


class HomeworksByWeekResponse(BaseModel):
    week_number: int
    homeworks: List[PatientHomeworkResponse]


class TranscriptItemResponse(BaseModel):
    id: int
    speaker: str
    text: str
    timestamp: datetime

    class Config:
        from_attributes = True


class SessionWithHomeworksResponse(BaseModel):
    session_id: int
    patient_id: int
    patient_name: str
    started_at: datetime
    ended_at: Optional[datetime]
    transcript_count: int
    transcripts: List[TranscriptItemResponse]
    analysis_summary: Optional[str]
    homeworks: List[HomeworkItemBase]
    approved_count: int


class EditHomeworksRequest(BaseModel):
    homeworks: List[HomeworkItemCreate]


class ApproveHomeworksRequest(BaseModel):
    homeworks: List[HomeworkItemCreate]


class MarkCompleteRequest(BaseModel):
    notes: Optional[str] = None
