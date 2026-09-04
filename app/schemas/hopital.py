from pydantic import BaseModel, Field
from typing import Optional
from .user import UserCreate, UserResponse

class HopitalBase(BaseModel):
    nom: str
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    services: Optional[str] = None  # JSON ou liste de services
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

class HopitalCreate(HopitalBase):
    user: UserCreate

# ✅ AJOUTER CETTE CLASSE
class HopitalUpdate(BaseModel):
    nom: Optional[str] = None
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    services: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

class HopitalResponse(HopitalBase):
    id: int
    user_id: int
    is_open: bool
    user: UserResponse
    
    class Config:
        from_attributes = True