from pydantic import BaseModel, Field
from typing import Optional
from .user import UserCreate, UserResponse

# ✅ AJOUTER cette classe AVANT ChauffeurResponse
class VehiculeResponse(BaseModel):
    id: int
    chauffeur_id: int
    immatriculation: str
    modele: Optional[str] = None
    couleur: Optional[str] = None
    type: str
    is_active: bool
    
    class Config:
        from_attributes = True

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

class ChauffeurUpdate(BaseModel):
    license_number: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

class ChauffeurResponse(ChauffeurBase):
    id: int
    user_id: int
    is_available: bool
    user: UserResponse
    vehicule: Optional[VehiculeResponse] = None  # ✅ Utiliser VehiculeResponse au lieu de dict
    
    class Config:
        from_attributes = True