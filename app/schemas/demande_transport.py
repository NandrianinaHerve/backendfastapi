from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from ..models.demande_transport import TransportStatus, TransportType

class DemandeTransportBase(BaseModel):
    type: TransportType
    destination: Optional[str] = None
    notes: Optional[str] = None

class DemandeTransportCreate(DemandeTransportBase):
    patient_id: Optional[int] = None
    latitude_depart: float
    longitude_depart: float
    latitude_arrivee: Optional[float] = None
    longitude_arrivee: Optional[float] = None

class DemandeTransportUpdate(BaseModel):
    chauffeur_id: Optional[int] = None
    status: Optional[TransportStatus] = None
    destination: Optional[str] = None

# ✅ CORRECTION : Ajouter les champs latitude/longitude pour la réponse
class DemandeTransportResponse(BaseModel):
    id: int
    patient_id: int
    chauffeur_id: Optional[int] = None
    type: TransportType
    status: TransportStatus
    destination: Optional[str] = None
    notes: Optional[str] = None
    latitude_depart: float
    longitude_depart: float
    latitude_arrivee: Optional[float] = None
    longitude_arrivee: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True