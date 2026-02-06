from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

# Request Schemas
class TherapistRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    license_number: str = Field(..., min_length=3, max_length=50)
    specialty: str = Field(..., min_length=2, max_length=100)
    address: str = Field(..., min_length=5, max_length=500)

class TherapistLogin(BaseModel):
    email: EmailStr
    password: str

# Response Schemas
class TherapistResponse(BaseModel):
    id: int
    name: str
    email: str
    license_number: str
    specialty: str
    address: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    id: Optional[int] = None
