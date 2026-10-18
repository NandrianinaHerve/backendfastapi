# # from fastapi import APIRouter, Depends, HTTPException
# # from sqlalchemy.orm import Session
# # from typing import List
# # import random

# # from ...core.database import get_db
# # from ...core.dependencies import get_current_user
# # from ...models.user import User
# # from ...models.patient import Patient
# # from ...models.consultation_ia import ConsultationIA
# # from ...models.docteur import Docteur
# # from ...models.specialite import Specialite
# # from ...schemas.consultation_ia import SymptomeInput, IaConsultationResponse, IaRecommendationResponse, DocteurRecommande
# # from ...services.ia_service import IAAnalyzer

# # router = APIRouter(prefix="/ia", tags=["IA"])

# # # Mapping des symptômes vers les spécialités (simplifié)
# # SYMPTOME_SPECIALITE = {
# #     "douleur poitrine": "cardiologie",
# #     "essoufflement": "cardiologie",
# #     "palpitations": "cardiologie",
# #     "maux tête": "neurologie",
# #     "vertiges": "neurologie",
# #     "perte connaissance": "neurologie",
# #     "douleur estomac": "gastro-entérologie",
# #     "nausée": "gastro-entérologie",
# #     "vomissement": "gastro-entérologie",
# #     "douleur os": "orthopédie",
# #     "fracture": "orthopédie",
# #     "entorse": "orthopédie",
# #     "fièvre": "médecine générale",
# #     "toux": "pneumologie",
# #     "mal gorge": "ORL",
# #     "éruption cutanée": "dermatologie",
# #     "démangeaison": "dermatologie",
# #     "douleur oeil": "ophtalmologie",
# #     "vision trouble": "ophtalmologie",
# #     "dépression": "psychiatrie",
# #     "anxiété": "psychiatrie",
# #     "douleur dent": "dentisterie",
# #     "saignement": "dentisterie"
# # }

# # @router.post("/analyze", response_model=IaRecommendationResponse)
# # def analyze_symptoms(
# #     input_data: SymptomeInput,
# #     db: Session = Depends(get_db),
# #     current_user: User = Depends(get_current_user)
# # ):
# #     """
# #     Analyser les symptômes et recommander des médecins
# #     """
# #     # Vérifier que l'utilisateur est un patient
# #     patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
# #     if not patient:
# #         raise HTTPException(status_code=403, detail="Seuls les patients peuvent utiliser cette fonctionnalité")
    
# #     # Analyser les symptômes
# #     symptomes = input_data.symptomes.lower()
    
# #     # Trouver la spécialité la plus probable
# #     specialite_predite = "médecine générale"
# #     score_max = 0
    
# #     for key, specialite in SYMPTOME_SPECIALITE.items():
# #         if key in symptomes:
# #             # Simuler un score de confiance
# #             score = random.uniform(0.6, 0.95)
# #             if score > score_max:
# #                 score_max = score
# #                 specialite_predite = specialite
    
# #     # Niveau de confiance (simulé)
# #     niveau_confiance = score_max if score_max > 0 else 0.5
    
# #     # Sauvegarder la consultation
# #     consultation = ConsultationIA(
# #         patient_id=patient.id,
# #         symptomes=input_data.symptomes,
# #         specialite_predite=specialite_predite,
# #         niveau_confiance=niveau_confiance,
# #         resultat=f"Spécialité recommandée : {specialite_predite} (confiance: {niveau_confiance:.2f})"
# #     )
# #     db.add(consultation)
# #     db.commit()
# #     db.refresh(consultation)
    
# #     # Rechercher des docteurs dans la spécialité prédite
# #     specialite = db.query(Specialite).filter(Specialite.nom.ilike(f"%{specialite_predite}%")).first()
# #     docteurs_recommandes = []
    
# #     if specialite:
# #         # Trouver les docteurs disponibles dans cette spécialité
# #         docteurs = db.query(Docteur).filter(
# #             Docteur.specialite_id == specialite.id,
# #             Docteur.is_available == True
# #         ).limit(5).all()
        
# #         # Simuler des distances et scores
# #         for docteur in docteurs:
# #             distance = random.uniform(0.5, 10.0)
# #             docteur_info = DocteurRecommande(
# #                 id=docteur.id,
# #                 nom=docteur.user.nom,
# #                 prenom=docteur.user.prenom,
# #                 specialite=specialite.nom,
# #                 distance=round(distance, 2),
# #                 is_available=docteur.is_available,
# #                 consultation_price=docteur.consultation_price,
# #                 experience_years=docteur.experience_years
# #             )
# #             docteurs_recommandes.append(docteur_info)
    
# #     return IaRecommendationResponse(
# #         consultation=consultation,
# #         docteurs_recommandes=docteurs_recommandes
# #     )

# # @router.get("/consultations", response_model=List[IaConsultationResponse])
# # def get_consultations(
# #     db: Session = Depends(get_db),
# #     current_user: User = Depends(get_current_user)
# # ):
# #     """Obtenir l'historique des consultations IA du patient"""
# #     patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
# #     if not patient:
# #         raise HTTPException(status_code=403, detail="Seuls les patients peuvent voir leurs consultations")
    
# #     consultations = db.query(ConsultationIA).filter(
# #         ConsultationIA.patient_id == patient.id
# #     ).order_by(ConsultationIA.created_at.desc()).all()
    
# #     return consultations
# from fastapi import APIRouter, Depends, HTTPException, Query
# from sqlalchemy.orm import Session
# from typing import List, Optional
# from datetime import datetime

# from ...core.database import get_db
# from ...core.dependencies import get_current_user
# from ...models.user import User
# from ...models.patient import Patient
# from ...models.consultation_ia import ConsultationIA
# from ...models.docteur import Docteur
# from ...models.specialite import Specialite
# from ...schemas.consultation_ia import (
#     SymptomeInput, 
#     IaConsultationResponse, 
#     IaRecommendationResponse, 
#     DocteurRecommande,
#     MLTrainingData,
#     MLStatsResponse
# )
# from ...services.ia_service import IAAnalyzer
# from ...services.ml_service import ml_service

# router = APIRouter(prefix="/ia", tags=["IA"])

# @router.post("/analyze", response_model=IaRecommendationResponse)
# def analyze_symptoms(
#     input_data: SymptomeInput,
#     use_ml: bool = Query(True, description="Utiliser le ML si disponible"),
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Analyser les symptômes et recommander des médecins
    
#     - Utilise le ML si disponible et use_ml=True
#     - Fallback sur le système expert à base de règles
#     """
#     # Vérifier que l'utilisateur est un patient
#     patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
#     if not patient:
#         raise HTTPException(
#             status_code=403, 
#             detail="Seuls les patients peuvent utiliser cette fonctionnalité"
#         )
    
#     # 🔥 Analyse avec ML ou fallback
#     if use_ml:
#         try:
#             ml_result = ml_service.predict(input_data.symptomes)
#             specialite_predite = ml_result["specialite"]
#             niveau_confiance = ml_result["confiance"]
#             method_used = "machine_learning"
#             details = ml_result
#         except Exception as e:
#             print(f"⚠️ Erreur ML: {e}. Fallback sur le système expert.")
#             rule_result = IAAnalyzer.analyze(input_data.symptomes)
#             specialite_predite = rule_result["specialite"]
#             niveau_confiance = rule_result["confiance"]
#             method_used = "rule_based_fallback"
#             details = rule_result
#     else:
#         rule_result = IAAnalyzer.analyze(input_data.symptomes)
#         specialite_predite = rule_result["specialite"]
#         niveau_confiance = rule_result["confiance"]
#         method_used = "rule_based"
#         details = rule_result
    
#     # Sauvegarder la consultation
#     consultation = ConsultationIA(
#         patient_id=patient.id,
#         symptomes=input_data.symptomes,
#         specialite_predite=specialite_predite,
#         niveau_confiance=niveau_confiance,
#         resultat=f"Spécialité recommandée : {specialite_predite} (confiance: {niveau_confiance:.2f}) - Méthode: {method_used}"
#     )
#     db.add(consultation)
#     db.commit()
#     db.refresh(consultation)
    
#     # Rechercher des docteurs dans la spécialité prédite
#     specialite = db.query(Specialite).filter(
#         Specialite.nom.ilike(f"%{specialite_predite}%")
#     ).first()
    
#     docteurs_recommandes = []
    
#     if specialite:
#         docteurs = db.query(Docteur).filter(
#             Docteur.specialite_id == specialite.id,
#             Docteur.is_available == True
#         ).limit(5).all()
        
#         # Calculer des distances simulées (à remplacer par de vraies distances)
#         for i, docteur in enumerate(docteurs):
#             distance = round(0.5 + (i * 0.7), 2)
#             docteur_info = DocteurRecommande(
#                 id=docteur.id,
#                 nom=docteur.user.nom,
#                 prenom=docteur.user.prenom,
#                 specialite=specialite.nom,
#                 distance=distance,
#                 is_available=docteur.is_available,
#                 consultation_price=docteur.consultation_price,
#                 experience_years=docteur.experience_years
#             )
#             docteurs_recommandes.append(docteur_info)
    
#     return IaRecommendationResponse(
#         consultation=consultation,
#         docteurs_recommandes=docteurs_recommandes,
#         ml_details=details if method_used == "machine_learning" else None
#     )

# @router.get("/consultations", response_model=List[IaConsultationResponse])
# def get_consultations(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """Obtenir l'historique des consultations IA du patient"""
#     patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
#     if not patient:
#         raise HTTPException(
#             status_code=403, 
#             detail="Seuls les patients peuvent voir leurs consultations"
#         )
    
#     consultations = db.query(ConsultationIA).filter(
#         ConsultationIA.patient_id == patient.id
#     ).order_by(ConsultationIA.created_at.desc()).all()
    
#     return consultations

# # ============================================
# # ENDPOINTS POUR L'ENTRAÎNEMENT ML
# # ============================================

# @router.post("/train")
# def train_ml_model(
#     data: List[MLTrainingData],
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Entraîner le modèle ML avec de nouvelles données
#     (Admin uniquement)
#     """
#     if current_user.role.value != "admin":
#         raise HTTPException(
#             status_code=403,
#             detail="Seuls les administrateurs peuvent entraîner le modèle"
#         )
    
#     training_data = [(d.symptomes, d.specialite) for d in data]
#     result = ml_service.train(training_data)
    
#     return {
#         "message": "Modèle entraîné avec succès",
#         "result": result
#     }

# @router.get("/ml/stats", response_model=dict)
# def get_ml_stats(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """Obtenir les statistiques du modèle ML"""
#     if current_user.role.value != "admin":
#         raise HTTPException(
#             status_code=403,
#             detail="Seuls les administrateurs peuvent voir les statistiques"
#         )
    
#     return ml_service.get_statistics()

# @router.post("/ml/add-data")
# def add_training_data(
#     symptoms: str,
#     specialite: str,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Ajouter une donnée d'entraînement pour enrichir le modèle
#     (Admin uniquement)
#     """
#     if current_user.role.value != "admin":
#         raise HTTPException(
#             status_code=403,
#             detail="Seuls les administrateurs peuvent ajouter des données"
#         )
    
#     result = ml_service.add_training_data(symptoms, specialite)
    
#     return {
#         "message": "Donnée ajoutée et modèle réentraîné",
#         "result": result
#     }
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json

from ...core.database import get_db
from ...core.dependencies import get_current_user
from ...models.user import User
from ...models.patient import Patient
from ...models.consultation_ia import ConsultationIA
from ...models.docteur import Docteur
from ...models.specialite import Specialite
from ...models.notification import Notification  # ✅ AJOUTER
from ...schemas.consultation_ia import (
    SymptomeInput, 
    IaConsultationResponse, 
    IaRecommendationResponse, 
    DocteurRecommande,
    MLTrainingData,
    MLStatsResponse
)
from ...services.ia_service import IAAnalyzer
from ...services.ml_service import ml_service

router = APIRouter(prefix="/ia", tags=["IA"])


@router.post("/analyze", response_model=IaRecommendationResponse)
def analyze_symptoms(
    input_data: SymptomeInput,
    use_ml: bool = Query(True, description="Utiliser le ML si disponible"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyser les symptômes et recommander des médecins
    
    - Utilise le ML si disponible et use_ml=True
    - Fallback sur le système expert à base de règles
    """
    # Vérifier que l'utilisateur est un patient
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(
            status_code=403, 
            detail="Seuls les patients peuvent utiliser cette fonctionnalité"
        )
    
    # 🔥 Analyse avec ML ou fallback
    if use_ml:
        try:
            ml_result = ml_service.predict(input_data.symptomes)
            specialite_predite = ml_result["specialite"]
            niveau_confiance = ml_result["confiance"]
            method_used = "machine_learning"
            details = ml_result
        except Exception as e:
            print(f"⚠️ Erreur ML: {e}. Fallback sur le système expert.")
            rule_result = IAAnalyzer.analyze(input_data.symptomes)
            specialite_predite = rule_result["specialite"]
            niveau_confiance = rule_result["confiance"]
            method_used = "rule_based_fallback"
            details = rule_result
    else:
        rule_result = IAAnalyzer.analyze(input_data.symptomes)
        specialite_predite = rule_result["specialite"]
        niveau_confiance = rule_result["confiance"]
        method_used = "rule_based"
        details = rule_result
    
    # Sauvegarder la consultation
    consultation = ConsultationIA(
        patient_id=patient.id,
        symptomes=input_data.symptomes,
        specialite_predite=specialite_predite,
        niveau_confiance=niveau_confiance,
        resultat=f"Spécialité recommandée : {specialite_predite} (confiance: {niveau_confiance:.2f}) - Méthode: {method_used}"
    )
    db.add(consultation)
    db.commit()
    db.refresh(consultation)
    
    # Rechercher des docteurs dans la spécialité prédite
    specialite = db.query(Specialite).filter(
        Specialite.nom.ilike(f"%{specialite_predite}%")
    ).first()
    
    docteurs_recommandes = []
    
    if specialite:
        docteurs = db.query(Docteur).filter(
            Docteur.specialite_id == specialite.id,
            Docteur.is_available == True
        ).limit(5).all()
        
        # Calculer des distances simulées (à remplacer par de vraies distances)
        for i, docteur in enumerate(docteurs):
            distance = round(0.5 + (i * 0.7), 2)
            docteur_info = DocteurRecommande(
                id=docteur.id,
                nom=docteur.user.nom,
                prenom=docteur.user.prenom,
                specialite=specialite.nom,
                distance=distance,
                is_available=docteur.is_available,
                consultation_price=docteur.consultation_price,
                experience_years=docteur.experience_years
            )
            docteurs_recommandes.append(docteur_info)
    
    # ============================================
    # ✅ NOTIFICATION AU PATIENT
    # ============================================
    try:
        notification = Notification(
            user_id=patient.user_id,
            title="🤖 Analyse IA terminée",
            message=(
                f"Spécialité recommandée : {specialite_predite} "
                f"(confiance: {niveau_confiance:.0%}). "
                f"{len(docteurs_recommandes)} médecin(s) disponible(s) trouvé(s)."
            ),
            type="ia_recommendation",
            data=json.dumps({
                "consultation_id": consultation.id,
                "specialite": specialite_predite,
                "confiance": niveau_confiance,
                "method": method_used,
                "docteurs_count": len(docteurs_recommandes)
            }),
            is_read=False
        )
        db.add(notification)
        db.commit()
        print(f"✅ Notification IA créée pour le patient {patient.id}")
    except Exception as e:
        print(f"❌ Erreur notification IA: {e}")
        db.rollback()
    
    return IaRecommendationResponse(
        consultation=consultation,
        docteurs_recommandes=docteurs_recommandes,
        ml_details=details if method_used == "machine_learning" else None
    )


@router.get("/consultations", response_model=List[IaConsultationResponse])
def get_consultations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir l'historique des consultations IA du patient"""
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(
            status_code=403, 
            detail="Seuls les patients peuvent voir leurs consultations"
        )
    
    consultations = db.query(ConsultationIA).filter(
        ConsultationIA.patient_id == patient.id
    ).order_by(ConsultationIA.created_at.desc()).all()
    
    return consultations


# ============================================
# ENDPOINTS POUR L'ENTRAÎNEMENT ML
# ============================================

@router.post("/train")
def train_ml_model(
    data: List[MLTrainingData],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Entraîner le modèle ML avec de nouvelles données
    (Admin uniquement)
    """
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=403,
            detail="Seuls les administrateurs peuvent entraîner le modèle"
        )
    
    training_data = [(d.symptomes, d.specialite) for d in data]
    result = ml_service.train(training_data)
    
    # ============================================
    # ✅ NOTIFICATION À L'ADMIN (confirmation)
    # ============================================
    try:
        if "error" not in result:
            notification = Notification(
                user_id=current_user.id,
                title="🤖 Modèle ML entraîné",
                message=(
                    f"Le modèle a été entraîné avec succès. "
                    f"Accuracy: {result.get('accuracy', 0):.1%}, "
                    f"Exemples: {result.get('n_samples', 0)}, "
                    f"Classes: {result.get('n_classes', 0)}"
                ),
                type="ml_training",
                data=json.dumps({
                    "accuracy": result.get('accuracy', 0),
                    "n_samples": result.get('n_samples', 0),
                    "n_features": result.get('n_features', 0),
                    "n_classes": result.get('n_classes', 0)
                }),
                is_read=False
            )
            db.add(notification)
            db.commit()
            print(f"✅ Notification d'entraînement créée")
    except Exception as e:
        print(f"❌ Erreur notification entraînement: {e}")
        db.rollback()
    
    return {
        "message": "Modèle entraîné avec succès",
        "result": result
    }


@router.get("/ml/stats", response_model=dict)
def get_ml_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir les statistiques du modèle ML"""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=403,
            detail="Seuls les administrateurs peuvent voir les statistiques"
        )
    
    return ml_service.get_statistics()


@router.post("/ml/add-data")
def add_training_data(
    symptoms: str,
    specialite: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ajouter une donnée d'entraînement pour enrichir le modèle
    (Admin uniquement)
    """
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=403,
            detail="Seuls les administrateurs peuvent ajouter des données"
        )
    
    result = ml_service.add_training_data(symptoms, specialite)
    
    # ============================================
    # ✅ NOTIFICATION À L'ADMIN
    # ============================================
    try:
        notification = Notification(
            user_id=current_user.id,
            title="📚 Donnée d'entraînement ajoutée",
            message=(
                f"Nouvelle donnée ajoutée : '{symptoms[:50]}...' → {specialite}. "
                f"Le modèle a été réentraîné."
            ),
            type="ml_data_added",
            data=json.dumps({
                "symptoms": symptoms,
                "specialite": specialite,
                "total_examples": result.get('n_samples', 0) if 'n_samples' in result else 0
            }),
            is_read=False
        )
        db.add(notification)
        db.commit()
        print(f"✅ Notification ajout de donnée créée")
    except Exception as e:
        print(f"❌ Erreur notification: {e}")
        db.rollback()
    
    return {
        "message": "Donnée ajoutée et modèle réentraîné",
        "result": result
    }