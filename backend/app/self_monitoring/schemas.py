from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


class SelfMonitoringEntryBase(BaseModel):
    """Base schema for self-monitoring entry."""
    date: str = Field(..., description="ISO date string (YYYY-MM-DD)")
    time: str = Field(..., description="Time in HH:MM format")
    event: str = Field(..., description="Description of the event")
    ritual: str = Field(..., description="Description of the ritual")
    time_spent: float = Field(..., ge=0, description="Time spent in minutes")
    anxiety_level: int = Field(..., ge=0, le=10, description="Anxiety level from 0 to 10")


class SelfMonitoringEntryCreate(SelfMonitoringEntryBase):
    """Schema for creating a new entry."""
    pass


class SelfMonitoringEntryResponse(SelfMonitoringEntryBase):
    """Schema for entry response."""
    id: int
    day_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SelfMonitoringDayBase(BaseModel):
    """Base schema for self-monitoring day."""
    day_number: int = Field(..., ge=1, description="Day number")


class SelfMonitoringDayCreate(SelfMonitoringDayBase):
    """Schema for creating a new monitoring day."""
    pass


class SelfMonitoringDayResponse(SelfMonitoringDayBase):
    """Schema for day response with entries."""
    id: int
    patient_id: int
    entries: List[SelfMonitoringEntryResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SelfMonitoringDayListItem(BaseModel):
    """Simplified day list item (without full entries)."""
    id: int
    patient_id: int
    day_number: int
    entry_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PatientSelfMonitoringSummary(BaseModel):
    """Summary of patient's self-monitoring data."""
    patient_id: int
    patient_name: str
    total_days: int
    total_entries: int
    days: List[SelfMonitoringDayListItem]

    class Config:
        from_attributes = True
