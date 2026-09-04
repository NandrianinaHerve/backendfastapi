from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import random

from ...core.database import get_db
from ...core.dependencies import get_current_user
from ...models.user import User
from ...models.patient import Patient
from ...models.consultation_ia import ConsultationIA
from ...models.docteur import Docteur
from ...models.specialite import Specialite
from ...schemas.consultation_ia import SymptomeInput, IaConsultationResponse, IaRecommendationResponse, DocteurRecommande
from ...services.ia_service import IAAnalyzer

router = APIRouter(prefix="/ia", tags=["IA"])

# Mapping des symptômes vers les spécialités (simplifié)
SYMPTOME_SPECIALITE = {
    "douleur poitrine": "cardiologie",
    "essoufflement": "cardiologie",
    "palpitations": "cardiologie",
    "maux tête": "neurologie",
    "vertiges": "neurologie",
    "perte connaissance": "neurologie",
    "douleur estomac": "gastro-entérologie",
    "nausée": "gastro-entérologie",
    "vomissement": "gastro-entérologie",
    "douleur os": "orthopédie",
    "fracture": "orthopédie",
    "entorse": "orthopédie",
    "fièvre": "médecine générale",
    "toux": "pneumologie",
    "mal gorge": "ORL",
    "éruption cutanée": "dermatologie",
    "démangeaison": "dermatologie",
    "douleur oeil": "ophtalmologie",
    "vision trouble": "ophtalmologie",
    "dépression": "psychiatrie",
    "anxiété": "psychiatrie",
    "douleur dent": "dentisterie",
    "saignement": "dentisterie"
}

@router.post("/analyze", response_model=IaRecommendationResponse)
def analyze_symptoms(
    input_data: SymptomeInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyser les symptômes et recommander des médecins
    """
    # Vérifier que l'utilisateur est un patient
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=403, detail="Seuls les patients peuvent utiliser cette fonctionnalité")
    
    # Analyser les symptômes
    symptomes = input_data.symptomes.lower()
    
    # Trouver la spécialité la plus probable
    specialite_predite = "médecine générale"
    score_max = 0
    
    for key, specialite in SYMPTOME_SPECIALITE.items():
        if key in symptomes:
            # Simuler un score de confiance
            score = random.uniform(0.6, 0.95)
            if score > score_max:
                score_max = score
                specialite_predite = specialite
    
    # Niveau de confiance (simulé)
    niveau_confiance = score_max if score_max > 0 else 0.5
    
    # Sauvegarder la consultation
    consultation = ConsultationIA(
        patient_id=patient.id,
        symptomes=input_data.symptomes,
        specialite_predite=specialite_predite,
        niveau_confiance=niveau_confiance,
        resultat=f"Spécialité recommandée : {specialite_predite} (confiance: {niveau_confiance:.2f})"
    )
    db.add(consultation)
    db.commit()
    db.refresh(consultation)
    
    # Rechercher des docteurs dans la spécialité prédite
    specialite = db.query(Specialite).filter(Specialite.nom.ilike(f"%{specialite_predite}%")).first()
    docteurs_recommandes = []
    
    if specialite:
        # Trouver les docteurs disponibles dans cette spécialité
        docteurs = db.query(Docteur).filter(
            Docteur.specialite_id == specialite.id,
            Docteur.is_available == True
        ).limit(5).all()
        
        # Simuler des distances et scores
        for docteur in docteurs:
            distance = random.uniform(0.5, 10.0)
            docteur_info = DocteurRecommande(
                id=docteur.id,
                nom=docteur.user.nom,
                prenom=docteur.user.prenom,
                specialite=specialite.nom,
                distance=round(distance, 2),
                is_available=docteur.is_available,
                consultation_price=docteur.consultation_price,
                experience_years=docteur.experience_years
            )
            docteurs_recommandes.append(docteur_info)
    
    return IaRecommendationResponse(
        consultation=consultation,
        docteurs_recommandes=docteurs_recommandes
    )

@router.get("/consultations", response_model=List[IaConsultationResponse])
def get_consultations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir l'historique des consultations IA du patient"""
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=403, detail="Seuls les patients peuvent voir leurs consultations")
    
    consultations = db.query(ConsultationIA).filter(
        ConsultationIA.patient_id == patient.id
    ).order_by(ConsultationIA.created_at.desc()).all()
    
    return consultations