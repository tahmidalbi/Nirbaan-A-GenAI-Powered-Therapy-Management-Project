from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class SUDSSnapshotItem(BaseModel):
    item_id: Optional[int] = None
    item_text: str
    suds: int  # 0-100


class WeeklyProgressCreate(BaseModel):
    week_start_date: str  # ISO date string e.g. "2025-03-01"
    detailed_progress: str
    homework_reflection: str
    suds_snapshot: Optional[List[SUDSSnapshotItem]] = None


class WeeklyProgressResponse(BaseModel):
    id: int
    patient_id: int
    week_number: int
    week_start_date: str
    detailed_progress: str
    homework_reflection: str
    suds_snapshot: Optional[list] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
