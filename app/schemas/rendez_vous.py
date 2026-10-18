from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from ..models.rendez_vous import AppointmentStatus
from .patient import PatientResponse


# ============================================
# SCHÉMAS DE BASE
# ============================================
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


# ============================================
# ⭐ NOUVEAUX SCHÉMAS POUR LES RELATIONS
# ============================================
class UserInfo(BaseModel):
    """Informations de base de l'utilisateur"""
    id: int
    nom: str
    prenom: str
    email: Optional[str] = None
    telephone: Optional[str] = None

    class Config:
        from_attributes = True


class SpecialiteInfo(BaseModel):
    """Informations de la spécialité"""
    id: int
    nom: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class DocteurInfo(BaseModel):
    """Informations du docteur (pour la réponse rendez-vous)"""
    id: int
    user: Optional[UserInfo] = None
    specialite: Optional[SpecialiteInfo] = None
    adresse: Optional[str] = None
    cabinet: Optional[str] = None
    consultation_price: Optional[int] = None
    experience_years: Optional[int] = None
    is_available: Optional[bool] = None

    class Config:
        from_attributes = True


# ============================================
# RÉPONSE AVEC DOCTEUR INCLUS
# ============================================
class RendezVousResponse(RendezVousBase):
    id: int
    patient_id: int
    status: AppointmentStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # ⭐ AJOUTER le docteur complet
    docteur: Optional[DocteurInfo] = None
    patient: PatientResponse

    class Config:
        from_attributes = True