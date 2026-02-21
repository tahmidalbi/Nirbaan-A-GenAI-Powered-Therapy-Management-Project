from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class FearLadderItemBase(BaseModel):
    item: str = Field(..., description="Description of the fear or obsession")
    suds: int = Field(..., ge=0, le=100, description="SUDS rating (0-100)")


class FearLadderItemCreate(FearLadderItemBase):
    pass


class FearLadderItemResponse(FearLadderItemBase):
    id: int
    order_index: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class FearLadderCreate(BaseModel):
    items: List[FearLadderItemCreate] = Field(..., min_length=1, description="List of fear ladder items")


class FearLadderUpdate(BaseModel):
    items: List[FearLadderItemCreate] = Field(..., min_length=1, description="Updated list of fear ladder items")


class FearLadderResponse(BaseModel):
    id: int
    patient_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    items: List[FearLadderItemResponse]
    
    class Config:
        from_attributes = True


class FearLadderWithPatientInfo(FearLadderResponse):
    patient_name: str
    patient_email: str
    
    class Config:
        from_attributes = True


# AI Ladder Review Schemas

class AILadderEvidenceResponse(BaseModel):
    """Evidence quote supporting a suggestion"""
    id: int
    source_type: str  # 'intake' or 'daily_log'
    source_id: int
    source_date: Optional[datetime] = None
    field_name: Optional[str] = None
    quote_text: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class AILadderSuggestionResponse(BaseModel):
    """A missing obsession-compulsion pair detected by AI"""
    id: int
    obsession_label: str
    compulsion_summary: str
    rationale: str
    created_at: datetime
    evidence: List[AILadderEvidenceResponse] = []
    
    class Config:
        from_attributes = True


class AILadderReviewResponse(BaseModel):
    """AI review of fear ladder completeness"""
    id: int
    ladder_id: int
    patient_id: int
    therapist_id: int
    status: str  # queued, running, completed, failed
    model_name: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    suggestions: List[AILadderSuggestionResponse] = []
    
    class Config:
        from_attributes = True


class AILadderReviewSummary(BaseModel):
    """Simplified view for therapist dashboard"""
    status: str
    suggestions: List[AILadderSuggestionResponse] = []
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True
