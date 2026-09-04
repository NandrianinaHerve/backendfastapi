from pydantic import BaseModel, Field
from typing import Optional
from .user import UserCreate, UserResponse

class ChauffeurBase(BaseModel):
    vehicle_type: str  # ambulance, taxi
    license_number: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

class ChauffeurCreate(ChauffeurBase):
    user: UserCreate
    immatriculation: str
    modele: Optional[str] = None
    couleur: Optional[str] = None

# ✅ AJOUTER CETTE CLASSE
class ChauffeurUpdate(BaseModel):
    license_number: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

class ChauffeurResponse(ChauffeurBase):
    id: int
    user_id: int
    is_available: bool
    user: UserResponse
    vehicule: Optional[dict] = None
    
    class Config:
        from_attributes = True