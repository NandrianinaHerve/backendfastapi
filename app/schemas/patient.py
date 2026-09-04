from pydantic import BaseModel, Field
from datetime import date
from typing import Optional
from .user import UserCreate, UserResponse

class PatientBase(BaseModel):
    date_naissance: Optional[date] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

class PatientCreate(BaseModel):
    user: UserCreate
    date_naissance: Optional[date] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

# ✅ AJOUTER CETTE CLASSE
class PatientUpdate(BaseModel):
    date_naissance: Optional[date] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

class PatientResponse(PatientBase):
    id: int
    user_id: int
    user: UserResponse
    
    class Config:
        from_attributes = True