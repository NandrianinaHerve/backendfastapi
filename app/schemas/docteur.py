from pydantic import BaseModel, Field
from typing import Optional
from .user import UserCreate, UserResponse
from .specialite import SpecialiteResponse

class DocteurBase(BaseModel):
    specialite_id: int
    adresse: Optional[str] = None
    cabinet: Optional[str] = None
    consultation_price: Optional[int] = Field(None, ge=0)
    experience_years: Optional[int] = Field(0, ge=0)
    bio: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

class DocteurCreate(DocteurBase):
    user: UserCreate

# ✅ AJOUTER CETTE CLASSE
class DocteurUpdate(BaseModel):
    specialite_id: Optional[int] = None
    adresse: Optional[str] = None
    cabinet: Optional[str] = None
    consultation_price: Optional[int] = Field(None, ge=0)
    experience_years: Optional[int] = Field(None, ge=0)
    bio: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

class DocteurResponse(DocteurBase):
    id: int
    user_id: int
    is_available: bool
    user: UserResponse
    specialite: SpecialiteResponse
    
    class Config:
        from_attributes = True