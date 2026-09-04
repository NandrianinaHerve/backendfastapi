from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from ..models.demande_transport import TransportStatus, TransportType

class DemandeTransportBase(BaseModel):
    type: TransportType
    destination: Optional[str] = None
    notes: Optional[str] = None
    latitude_depart: float
    longitude_depart: float
    latitude_arrivee: Optional[float] = None
    longitude_arrivee: Optional[float] = None

class DemandeTransportCreate(DemandeTransportBase):
    patient_id: int

class DemandeTransportUpdate(BaseModel):
    chauffeur_id: Optional[int] = None
    status: Optional[TransportStatus] = None
    destination: Optional[str] = None

class DemandeTransportResponse(DemandeTransportBase):
    id: int
    patient_id: int
    chauffeur_id: Optional[int] = None
    status: TransportStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True