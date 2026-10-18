from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict
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



class MLTrainingData(BaseModel):
    """Données pour l'entraînement du modèle ML"""
    symptomes: str
    specialite: str

class MLStatsResponse(BaseModel):
    """Statistiques du modèle ML"""
    model_type: str
    n_classes: int
    classes: List[str]
    n_features: int
    is_trained: bool

class IaRecommendationResponse(BaseModel):
    """Réponse avec recommandation IA"""
    consultation: IaConsultationResponse
    docteurs_recommandes: List[DocteurRecommande]
    ml_details: Optional[Dict] = None