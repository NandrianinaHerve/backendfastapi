from pydantic import BaseModel, Field
from typing import Optional
from .user import UserCreate, UserResponse

class PharmacieBase(BaseModel):
    nom: str
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

class PharmacieCreate(PharmacieBase):
    user: UserCreate

# ✅ AJOUTER CETTE CLASSE
class PharmacieUpdate(BaseModel):
    nom: Optional[str] = None
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

class PharmacieResponse(PharmacieBase):
    id: int
    user_id: int
    is_open: bool
    user: UserResponse
    
    class Config:
        from_attributes = True