from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from ..models.rendez_vous import AppointmentStatus

class RendezVousBase(BaseModel):
    docteur_id: int
    date: datetime
    motif: Optional[str] = None
    notes: Optional[str] = None

class RendezVousCreate(RendezVousBase):
    patient_id: int

class RendezVousUpdate(BaseModel):
    date: Optional[datetime] = None
    status: Optional[AppointmentStatus] = None
    motif: Optional[str] = None
    notes: Optional[str] = None

class RendezVousResponse(RendezVousBase):
    id: int
    patient_id: int
    status: AppointmentStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True