from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class DisponibiliteBase(BaseModel):
    """Schéma de base pour une disponibilité"""
    date: datetime
    heure_debut: datetime
    heure_fin: datetime
    is_available: bool = Field(default=True, description="Disponible ou non")

class DisponibiliteCreate(DisponibiliteBase):
    """Schéma pour créer une disponibilité"""
    docteur_id: int

class DisponibiliteUpdate(BaseModel):
    """Schéma pour mettre à jour une disponibilité"""
    date: Optional[datetime] = None
    heure_debut: Optional[datetime] = None
    heure_fin: Optional[datetime] = None
    is_available: Optional[bool] = None

class DisponibiliteResponse(DisponibiliteBase):
    """Schéma pour la réponse d'une disponibilité"""
    id: int
    docteur_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class DisponibiliteWithDocteur(DisponibiliteResponse):
    """Schéma avec les informations du docteur"""
    docteur_nom: str
    docteur_prenom: str
    specialite: str