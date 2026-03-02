from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ─── Imaginal Cards ───────────────────────────────────────────────────────────

class ERPImaginalCardCreate(BaseModel):
    content: str = Field(default="", max_length=10000)
    order_index: int = Field(default=0, ge=0)

    class Config:
        from_attributes = True


class ERPImaginalCardUpdate(BaseModel):
    content: Optional[str] = Field(None, max_length=10000)
    order_index: Optional[int] = Field(None, ge=0)

    class Config:
        from_attributes = True


class ERPImaginalCardResponse(BaseModel):
    id: int
    erp_item_id: int
    content: str
    order_index: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Session Note ─────────────────────────────────────────────────────────────

class ERPSessionNoteUpdate(BaseModel):
    session_exercise_note: Optional[str] = Field(None, max_length=10000)

    class Config:
        from_attributes = True


# ─── ERP Items ────────────────────────────────────────────────────────────────

class ERPItemCreate(BaseModel):
    obsession: str = Field(..., min_length=1, max_length=2000)
    compulsions: List[str] = Field(default_factory=list)
    suds: Optional[int] = Field(None, ge=0, le=100)

    class Config:
        from_attributes = True


class ERPItemUpdate(BaseModel):
    obsession: Optional[str] = Field(None, min_length=1, max_length=2000)
    compulsions: Optional[List[str]] = None
    suds: Optional[int] = Field(None, ge=0, le=100)

    class Config:
        from_attributes = True


class ERPItemResponse(BaseModel):
    id: int
    patient_id: int
    obsession: str
    compulsions: List[str]
    suds: Optional[int]
    session_exercise_note: Optional[str]
    imaginal_cards: List[ERPImaginalCardResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Live Sessions ─────────────────────────────────────────────────────────────

class ERPLiveSessionResponse(BaseModel):
    id: int
    erp_item_id: int
    patient_id: int
    status: str               # running | paused | ended
    accumulated_seconds: float
    resumed_at: Optional[datetime]   # null when paused / ended
    ended_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── SUDS Readings ─────────────────────────────────────────────────────────────

class ERPSUDSReadingCreate(BaseModel):
    suds_value: int = Field(..., ge=0, le=100)
    elapsed_seconds: float = Field(default=0.0, ge=0)

    class Config:
        from_attributes = True


class ERPSUDSReadingResponse(BaseModel):
    id: int
    session_id: int
    erp_item_id: int
    suds_value: int
    elapsed_seconds: float
    recorded_at: datetime

    class Config:
        from_attributes = True


# ─── Therapist-facing schemas ──────────────────────────────────────────────────

class ERPPatientSummary(BaseModel):
    """Minimal patient info returned in the therapist ERP patient list."""
    patient_id: int
    patient_name: str
    patient_email: str
    item_count: int

    class Config:
        from_attributes = True


class ERPItemWithSUDSResponse(ERPItemResponse):
    """ERP item with full SUDS history, used in the therapist obsession-detail view."""
    suds_readings: List[ERPSUDSReadingResponse] = []

    class Config:
        from_attributes = True


# ─── Exercise Notes ───────────────────────────────────────────────────────────

class ERPExerciseNoteCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)

    class Config:
        from_attributes = True


class ERPExerciseNoteResponse(BaseModel):
    id: int
    erp_item_id: int
    patient_id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
