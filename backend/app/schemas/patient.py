from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

class PatientRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    conditions: str = Field(..., min_length=2, max_length=200)
    conditions_description: Optional[str] = Field(None, max_length=2000)
    address: str = Field(..., min_length=5, max_length=500)

class PatientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    conditions: Optional[str] = Field(None, min_length=2, max_length=200)
    conditions_description: Optional[str] = Field(None, max_length=2000)
    address: Optional[str] = Field(None, min_length=5, max_length=500)

class PatientLogin(BaseModel):
    email: EmailStr
    password: str

class PatientResponse(BaseModel):
    id: int
    name: str
    email: str
    conditions: str
    conditions_description: Optional[str]
    address: str
    therapist_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
