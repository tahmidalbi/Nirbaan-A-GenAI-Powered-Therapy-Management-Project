from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

class EmergencyPersonnelRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    education: str = Field(..., min_length=2, max_length=200)
    experience: str = Field(..., min_length=2, max_length=200)
    details: Optional[str] = Field(None, max_length=2000)
    address: str = Field(..., min_length=5, max_length=500)

class EmergencyPersonnelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    education: Optional[str] = Field(None, min_length=2, max_length=200)
    experience: Optional[str] = Field(None, min_length=2, max_length=200)
    details: Optional[str] = Field(None, max_length=2000)
    address: Optional[str] = Field(None, min_length=5, max_length=500)

class EmergencyPersonnelLogin(BaseModel):
    email: EmailStr
    password: str

class EmergencyPersonnelResponse(BaseModel):
    id: int
    name: str
    email: str
    education: str
    experience: str
    details: Optional[str]
    address: str
    therapist_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
