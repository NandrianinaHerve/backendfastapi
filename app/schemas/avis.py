from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from ..models.avis import TypeService


# ============================================
# AVIS
# ============================================

class AvisBase(BaseModel):
    note: int = Field(..., ge=1, le=5, description="Note de 1 à 5 étoiles")
    commentaire: Optional[str] = Field(None, max_length=1000)
    note_accueil: Optional[int] = Field(None, ge=1, le=5)
    note_attente: Optional[int] = Field(None, ge=1, le=5)
    note_proprete: Optional[int] = Field(None, ge=1, le=5)
    note_professionnalisme: Optional[int] = Field(None, ge=1, le=5)
    is_anonyme: bool = False


class AvisCreate(AvisBase):
    type_service: TypeService
    service_id: int
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None


class AvisUpdate(BaseModel):
    note: Optional[int] = Field(None, ge=1, le=5)
    commentaire: Optional[str] = Field(None, max_length=1000)
    note_accueil: Optional[int] = Field(None, ge=1, le=5)
    note_attente: Optional[int] = Field(None, ge=1, le=5)
    note_proprete: Optional[int] = Field(None, ge=1, le=5)
    note_professionnalisme: Optional[int] = Field(None, ge=1, le=5)


class ReponseAvis(BaseModel):
    """Réponse du service à un avis"""
    reponse: str = Field(..., min_length=1, max_length=1000)


class AvisResponse(AvisBase):
    id: int
    patient_id: int
    type_service: TypeService
    service_id: int
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    reponse_service: Optional[str] = None
    date_reponse: Optional[datetime] = None
    is_visible: bool
    nb_signalements: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AvisWithPatient(AvisResponse):
    """Avis avec info patient (anonymisé si demandé)"""
    patient_nom: Optional[str] = None
    patient_prenom: Optional[str] = None
    patient_photo: Optional[str] = None


# ============================================
# STATISTIQUES
# ============================================

class StatistiqueAvisResponse(BaseModel):
    id: int
    type_service: TypeService
    service_id: int
    nb_avis: int
    note_moyenne: float
    note_accueil_moyenne: Optional[float] = None
    note_attente_moyenne: Optional[float] = None
    note_proprete_moyenne: Optional[float] = None
    note_professionnalisme_moyenne: Optional[float] = None
    nb_1_etoile: int
    nb_2_etoiles: int
    nb_3_etoiles: int
    nb_4_etoiles: int
    nb_5_etoiles: int
    
    class Config:
        from_attributes = True


class AvisStatsDetail(BaseModel):
    """Statistiques détaillées d'un service"""
    service_id: int
    type_service: TypeService
    nom_service: Optional[str] = None
    nb_avis: int
    note_moyenne: float
    note_accueil_moyenne: Optional[float] = None
    note_attente_moyenne: Optional[float] = None
    note_proprete_moyenne: Optional[float] = None
    note_professionnalisme_moyenne: Optional[float] = None
    distribution: dict  # {1: 5, 2: 10, 3: 20, 4: 30, 5: 35}
    pourcentage_recommandation: float


# ============================================
# CLASSEMENT
# ============================================

class ClassementService(BaseModel):
    """Classement des services par note"""
    rang: int
    service_id: int
    nom: str
    type_service: TypeService
    note_moyenne: float
    nb_avis: int
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance: Optional[float] = None


class MeilleurServiceResponse(BaseModel):
    """Meilleurs services par catégorie"""
    meilleurs_docteurs: List[ClassementService] = []
    meilleures_pharmacies: List[ClassementService] = []
    meilleurs_hopitaux: List[ClassementService] = []
    meilleurs_chauffeurs: List[ClassementService] = []