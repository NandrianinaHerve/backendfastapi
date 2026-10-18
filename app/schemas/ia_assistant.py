from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ============================================
# ÉTAPE 1 : PRÉDIRE + GÉNÉRER QUESTIONS
# ============================================
# class SymptomesPredefinis(BaseModel):
#     """Le patient choisit UNIQUEMENT ses symptômes"""
#     symptomes: List[str] = Field(..., description="Liste des symptômes")
#     age: Optional[int] = None
#     sexe: Optional[str] = None
#     antecedents: Optional[List[str]] = None
#     duree_symptomes: Optional[str] = None
class SymptomesPredefinis(BaseModel):
    """Le patient sélectionne des symptômes ET peut ajouter des précisions"""
    symptomes: List[str] = Field(
        default_factory=list,
        description="Symptômes cochés dans la liste prédéfinie"
    )
    # ⚠️ NOUVEAU : texte libre optionnel pour compléter
    description_libre: Optional[str] = Field(
        None,
        max_length=1000,
        description=(
            "Description libre pour ajouter des symptômes ou précisions "
            "qui ne sont pas dans la liste. Ex: 'j'ai aussi mal aux oreilles'"
        )
    )
    age: Optional[int] = None
    sexe: Optional[str] = None
    antecedents: Optional[List[str]] = None
    duree_symptomes: Optional[str] = None

class MaladieProbable(BaseModel):
    nom: str
    probabilite: float
    symptomes_correspondants: List[str]
    description_courte: str
    urgence: str


class QuestionDifferentielle(BaseModel):
    """Question générée par le LLM pour distinguer les maladies"""
    id: str
    question: str
    type_reponse: str = "oui_non"  # oui_non | choix_multiple | texte_libre
    options: Optional[List[str]] = None
    aide: Optional[str] = None
    maladies_ciblees: List[str] = Field(default_factory=list)
class SymptomesExtraits(BaseModel):
    """Symptômes finaux après fusion (liste + description)"""
    symptomes_finaux: List[str] = Field(
        default_factory=list,
        description="Symptômes finaux utilisés pour l'analyse"
    )
    symptomes_ajoutes: List[str] = Field(
        default_factory=list,
        description="Symptômes extraits de la description libre uniquement"
    )
    description_utilisee: Optional[str] = None
    notes_extraction: Optional[str] = None

class PredictionResponse(BaseModel):
    """Réponse étape 1 : maladies probables + questions"""
    session_id: str
    maladies_probables: List[MaladieProbable]
    questions_differentielles: List[QuestionDifferentielle]
    message_introduction: str = Field(
        ...,
        description="Message du LLM expliquant qu'il doit poser des questions"
    )
    recommandation_generale: str
    avertissement: str
    symptomes_extraits: Optional[SymptomesExtraits] = None


# ============================================
# ÉTAPE 2 : CONFIRMER (patient répond aux questions)
# ============================================
class ReponsesDifferentiellesInput(BaseModel):
    """Le patient a répondu aux questions du LLM"""
    session_id: str
    reponses: Dict[str, str] = Field(
        ...,
        description="Question ID → réponse. Ex: {'q1': 'oui', 'q2': 'non'}"
    )


class ConfirmationResponse(BaseModel):
    """Confirmation finale sans médicaments"""
    maladie_confirmee: str
    niveau_confiance: float
    justification: str
    symptomes_cles: List[str]
    niveau_urgence: str
    recommandations: List[str]
    quand_consulter_urgence: List[str]
    avertissement: str
    diagnostic_certain: bool = True
    maladie_alternative: Optional[str] = None
    conseil_consultation: str = "Consultez un médecin pour confirmer."





    
# ============================================
# DOCTEURS / HÔPITAUX
# ============================================
class DocteurRecommandeSchema(BaseModel):
    id: int
    nom: str
    prenom: str
    specialite: str
    specialite_id: Optional[int] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    adresse: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_km: Optional[float] = None
    is_available: bool
    consultation_price: Optional[float] = None
    experience_years: Optional[int] = None
    note_moyenne: Optional[float] = None
    nb_avis: int = 0
    note_bayesienne: Optional[float] = None
    photo_url: Optional[str] = None


class HopitalRecommandeSchema(BaseModel):
    id: int
    nom: str
    type_etablissement: Optional[str] = None
    adresse: Optional[str] = None
    ville: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_km: Optional[float] = None
    urgence_24h: bool = False
    nb_lits_disponibles: Optional[int] = None
    services: Optional[List[str]] = None
    note_moyenne: Optional[float] = None
    nb_avis: int = 0
    note_bayesienne: Optional[float] = None


class ConfirmationAvecRecommandationsResponse(ConfirmationResponse):
    specialites_suggerees: List[str] = []
    docteurs_recommandes: List[DocteurRecommandeSchema] = []
    hopitaux_recommandes: List[HopitalRecommandeSchema] = []


# class SessionIASchema(BaseModel):
#     id: int
#     patient_id: int
#     symptomes: List[str]
#     maladie_confirmee: Optional[str]
#     statut: str
#     created_at: datetime
#     updated_at: Optional[datetime]
class SessionIASchema(BaseModel):
    """Session IA complète pour l'historique"""
    id: int
    patient_id: int
    symptomes: List[str] = []
    age: Optional[int] = None
    sexe: Optional[str] = None
    antecedents: Optional[List[str]] = None

    # Étape 1
    maladies_probables: Optional[List[Dict]] = None
    questions_differentielles: Optional[List[Dict]] = None
    message_introduction: Optional[str] = None

    # Étape 2
    reponses_differentielles: Optional[Dict] = None

    # Résultat
    maladie_confirmee: Optional[str] = None
    niveau_confiance: Optional[str] = None
    recommandations: Optional[List[str]] = None
    diagnostic_certain: Optional[bool] = True
    maladie_alternative: Optional[str] = None
    conseil_consultation: Optional[str] = None

    statut: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    

    class Config:
        from_attributes = True