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
