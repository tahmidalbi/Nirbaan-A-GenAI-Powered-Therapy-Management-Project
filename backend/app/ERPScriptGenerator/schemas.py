from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class StartImaginalRunRequest(BaseModel):
    patient_id: int
    therapist_id: int
    erp_item_id: int
    feared_consequence: str = Field(min_length=3)
    script_intensity: str = Field(description="Examples: 4/10, 7/10, 10/10")
    subtype: str | None = None


class ReviewImaginalRunRequest(BaseModel):
    thread_id: str
    approved: bool
    feedback: str | None = None


class ImaginalRunResponse(BaseModel):
    thread_id: str
    run_id: int
    status: str
    version_no: int
    script_text: str
    interrupt_required: bool = True


class ResumeResult(BaseModel):
    thread_id: str
    run_id: int
    status: str
    version_no: int
    script_text: str | None = None
    interrupt_required: bool
    audio_path: str | None = None
    approved_script_id: int | None = None


class ApprovedImaginalScriptItem(BaseModel):
    id: int
    run_id: int
    patient_id: int
    erp_item_id: int
    approved_script: str
    audio_path: str | None
    subtype: str | None
    created_at: datetime