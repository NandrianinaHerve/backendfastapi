from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


# ============================================
# CHAMBRE
# ============================================

class ChambreBase(BaseModel):
    numero: str = Field(..., min_length=1, max_length=20)
    etage: Optional[str] = None
    aile: Optional[str] = None
    capacite_lits: int = Field(1, ge=1, le=10)
    notes: Optional[str] = None


class ChambreCreate(ChambreBase):
    pass


class ChambreUpdate(BaseModel):
    numero: Optional[str] = None
    etage: Optional[str] = None
    aile: Optional[str] = None
    capacite_lits: Optional[int] = None
    is_disponible: Optional[bool] = None
    notes: Optional[str] = None


class ChambreResponse(ChambreBase):
    id: int
    hopital_id: int
    nb_lits_occupes: int
    is_disponible: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ChambreStats(BaseModel):
    total: int
    disponibles: int
    occupees: int
    lits_total: int
    lits_occupes: int
    taux_occupation: float


# ============================================
# HOSPITALISATION
# ============================================

class HospitalisationBase(BaseModel):
    patient_nom: str = Field(..., min_length=2, max_length=100)
    patient_prenom: str = Field(..., min_length=2, max_length=100)
    patient_telephone: Optional[str] = None
    contact_nom: Optional[str] = None
    contact_telephone: Optional[str] = None
    contact_relation: Optional[str] = None
    visites_autorisees: bool = True
    heures_visite: Optional[str] = None


class HospitalisationCreate(HospitalisationBase):
    chambre_id: int
    patient_id: Optional[int] = None  # Si patient dans le système


class HospitalisationUpdate(BaseModel):
    visites_autorisees: Optional[bool] = None
    heures_visite: Optional[str] = None
    contact_nom: Optional[str] = None
    contact_telephone: Optional[str] = None
    contact_relation: Optional[str] = None


class HospitalisationResponse(HospitalisationBase):
    id: int
    hopital_id: int
    chambre_id: int
    patient_id: Optional[int] = None
    date_entree: datetime
    date_sortie_effective: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class HospitalisationWithChambre(HospitalisationResponse):
    """Hospitalisation avec infos chambre"""
    chambre_numero: Optional[str] = None
    chambre_etage: Optional[str] = None
    chambre_aile: Optional[str] = None
    hopital_nom: Optional[str] = None


# ============================================
# RECHERCHE FAMILLE
# ============================================

class RechercheFamille(BaseModel):
    """Recherche d'un membre de famille"""
    nom: str = Field(..., min_length=2)
    prenom: Optional[str] = None


class ResultatRechercheFamille(BaseModel):
    """Résultat de recherche - Informations limitées"""
    trouve: bool
    patient_nom: Optional[str] = None
    patient_prenom: Optional[str] = None
    hopital_nom: Optional[str] = None
    hopital_adresse: Optional[str] = None
    hopital_telephone: Optional[str] = None
    chambre_numero: Optional[str] = None
    chambre_etage: Optional[str] = None
    chambre_aile: Optional[str] = None
    visites_autorisees: Optional[bool] = None
    heures_visite: Optional[str] = None
    message: Optional[str] = None