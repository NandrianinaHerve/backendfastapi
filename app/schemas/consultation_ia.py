from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class SymptomeInput(BaseModel):
    symptomes: str
    patient_id: int

class IaConsultationResponse(BaseModel):
    id: int
    patient_id: int
    symptomes: str
    specialite_predite: Optional[str] = None
    niveau_confiance: float
    resultat: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class DocteurRecommande(BaseModel):
    id: int
    nom: str
    prenom: str
    specialite: str
    distance: float  # en km
    is_available: bool
    consultation_price: Optional[int] = None
    experience_years: int

class IaRecommendationResponse(BaseModel):
    consultation: IaConsultationResponse
    docteurs_recommandes: List[DocteurRecommande]