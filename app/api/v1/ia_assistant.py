from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import logging

from ...core.database import get_db
from ...core.dependencies import get_current_user
from ...models.user import User
from ...models.patient import Patient
from ...models.session_ia import SessionIA
from ...models.notification import Notification
from ...models.localisation import Localisation
from ...schemas.ia_assistant import (
    SymptomesPredefinis,
    PredictionResponse,
    ReponsesDifferentiellesInput,
    ConfirmationAvecRecommandationsResponse,
    SessionIASchema,
    MaladieProbable,
    QuestionDifferentielle,
    DocteurRecommandeSchema,
    HopitalRecommandeSchema,
    SymptomesExtraits,
    
)
from ...services.deepseek_service import deepseek_service
from ...services.specialite_mapper import SpecialiteMapper
from ...services.docteur_recommender import DocteurRecommender
from ...services.hopital_recommender import HopitalRecommender

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ia-assistant", tags=["IA Assistant"])


SYMPTOMES_PREDEFINIS = [
    "Fièvre", "Frissons", "Maux de tête", "Fatigue intense",
    "Toux persistante", "Toux avec sang", "Sueurs nocturnes",
    "Perte de poids", "Douleurs musculaires", "Nausées",
    "Vomissements", "Diarrhée", "Douleur thoracique",
    "Essoufflement", "Ganglions enflés", "Éruption cutanée",
    "Douleur abdominale", "Perte d'appétit", "Vertiges",
    "Palpitations"
]


@router.get("/symptomes", response_model=List[str])
def get_symptomes_predefinis():
    return SYMPTOMES_PREDEFINIS


# ============================================
# ÉTAPE 1 : PRÉDIRE + QUESTIONS
# ============================================



@router.post("/predire", response_model=PredictionResponse)
async def predire_maladies(
    data: SymptomesPredefinis,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ÉTAPE 1 :
    - Le patient sélectionne des symptômes dans la liste
    - Il PEUT AUSSI ajouter une description libre
    - Le LLM COMBINE les deux sources
    - Le LLM identifie les maladies candidates + questions différentielles
    """
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=403, detail="Réservé aux patients")

    # Validation : au moins une source doit être fournie
    a_des_symptomes = len(data.symptomes) > 0
    a_une_description = bool(data.description_libre and data.description_libre.strip())

    if not a_des_symptomes and not a_une_description:
        raise HTTPException(
            status_code=400,
            detail=(
                "Vous devez cocher au moins un symptôme OU fournir "
                "une description libre."
            )
        )

    if a_une_description and len(data.description_libre.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="La description libre doit contenir au moins 10 caractères."
        )

    # Appel LLM (fusion + prédiction + questions)
    try:
        result = await deepseek_service.predire_et_questionner(
            symptomes=data.symptomes,
            description_libre=data.description_libre,
            age=data.age,
            sexe=data.sexe,
            antecedents=data.antecedents,
            duree_symptomes=data.duree_symptomes,
        )
    except Exception as e:
        logger.error(f"Erreur IA: {e}")
        raise HTTPException(status_code=503, detail=f"Service IA indisponible: {e}")

    # Récupérer les symptômes finaux (fusion)
    symptomes_extraits_raw = result.get("symptomes_extraits", {})
    symptomes_finaux = symptomes_extraits_raw.get("symptomes_finaux", [])

    # Fallback : si le LLM n'a rien renvoyé, utiliser les cochés
    if not symptomes_finaux:
        symptomes_finaux = data.symptomes

    # Créer la session avec les symptômes FUSIONNÉS
    session = SessionIA(
        patient_id=patient.id,
        symptomes=symptomes_finaux,
        age=data.age,
        sexe=data.sexe,
        antecedents=data.antecedents or [],
        maladies_probables=result.get("maladies_probables", []),
        questions_differentielles=result.get("questions_differentielles", []),
        message_introduction=result.get("message_introduction", ""),
        statut="questions_posees"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Notification
    try:
        db.add(Notification(
            user_id=patient.user_id,
            title="🤖 Analyse IA terminée",
            message=(
                f"{len(result.get('maladies_probables', []))} maladie(s) possible(s). "
                f"Répondez aux questions pour affiner."
            ),
            type="ia_prediction",
            data=json.dumps({
                "session_id": session.id,
                "symptomes_finaux": symptomes_finaux,
            }),
            is_read=False
        ))
        db.commit()
    except Exception as e:
        logger.warning(f"Erreur notification: {e}")
        db.rollback()

    return PredictionResponse(
        session_id=str(session.id),
        maladies_probables=[
            MaladieProbable(**m) for m in result.get("maladies_probables", [])
        ],
        questions_differentielles=[
            QuestionDifferentielle(**q)
            for q in result.get("questions_differentielles", [])
        ],
        message_introduction=result.get(
            "message_introduction",
            "Répondez aux questions suivantes pour affiner le diagnostic."
        ),
        recommandation_generale=result.get("recommandation_generale", ""),
        avertissement=result.get("avertissement", ""),
        symptomes_extraits=SymptomesExtraits(
            symptomes_finaux=symptomes_finaux,
            symptomes_ajoutes=symptomes_extraits_raw.get("symptomes_ajoutes", []),
            description_utilisee=symptomes_extraits_raw.get(
                "description_utilisee", data.description_libre
            ),
            notes_extraction=symptomes_extraits_raw.get("notes_extraction"),
        ) if symptomes_extraits_raw else None,
    )


# ============================================
# ÉTAPE 2 : CONFIRMER
# ============================================
@router.post(
    "/confirmer",
    response_model=ConfirmationAvecRecommandationsResponse
)
async def confirmer_maladie(
    data: ReponsesDifferentiellesInput,
    patient_lat: Optional[float] = Query(None),
    patient_lon: Optional[float] = Query(None),
    ponderation: str = Query("equilibre"),
    prix_max: Optional[float] = Query(None),
    experience_min: Optional[int] = Query(None),
    note_min: Optional[float] = Query(None),
    rayon_km: float = Query(50.0, ge=1.0, le=500.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ÉTAPE 2 :
    - Le patient a répondu aux questions du LLM
    - Le LLM DÉTERMINE LUI-MÊME la maladie finale
    - Recommande docteurs + hôpitaux
    - Aucun médicament
    """
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=403, detail="Réservé aux patients")

    session = db.query(SessionIA).filter(
        SessionIA.id == int(data.session_id),
        SessionIA.patient_id == patient.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable")

    if not session.questions_differentielles:
        raise HTTPException(
            status_code=400,
            detail="Aucune question générée. Appelez d'abord /predire."
        )

    # Analyse par le LLM
    try:
        confirmation = await deepseek_service.analyser_reponses(
            symptomes=session.symptomes,
            maladies_candidates=session.maladies_probables or [],
            questions=session.questions_differentielles or [],
            reponses=data.reponses,
            age=session.age,
            sexe=session.sexe,
        )
    except Exception as e:
        logger.error(f"Erreur analyse: {e}")
        raise HTTPException(status_code=503, detail=f"Service IA indisponible: {e}")

    # Sauvegarder
    session.reponses_differentielles = data.reponses
    session.maladie_confirmee = confirmation.get("maladie_confirmee")
    session.niveau_confiance = str(confirmation.get("niveau_confiance", 0))
    session.recommandations = confirmation.get("recommandations", [])
    session.diagnostic_certain = confirmation.get("diagnostic_certain", True)
    session.maladie_alternative = confirmation.get("maladie_alternative")
    session.conseil_consultation = confirmation.get("conseil_consultation", "")
    session.statut = "termine"
    db.commit()

    maladie_confirmee = confirmation.get("maladie_confirmee", "")

    # Localisation auto
    if patient_lat is None or patient_lon is None:
        loc = db.query(Localisation).filter(
            Localisation.user_id == patient.user_id
        ).first()
        if loc:
            patient_lat = patient_lat or getattr(loc, "latitude", None)
            patient_lon = patient_lon or getattr(loc, "longitude", None)

    # Recommandations docteurs
    specialites_suggerees = SpecialiteMapper.get_specialites_for_maladie(
        maladie_confirmee
    )
    docteurs_recommandes = DocteurRecommender.recommander(
        db=db,
        specialites_noms=specialites_suggerees,
        patient_lat=patient_lat,
        patient_lon=patient_lon,
        limit=5,
        rayon_km=rayon_km,
        ponderation=ponderation,
        prix_max=prix_max,
        experience_min=experience_min,
        note_min=note_min,
    )

    # Recommandations hôpitaux
    urgence = confirmation.get("niveau_urgence", "").lower() in ["élevée", "elevee"]
    hopitaux_recommandes = HopitalRecommender.recommander(
        db=db,
        maladie=maladie_confirmee,
        patient_lat=patient_lat,
        patient_lon=patient_lon,
        limit=5,
        rayon_km=max(rayon_km, 100.0),
        ponderation=ponderation,
        urgence_seulement=urgence,
    )

    # Notification
    try:
        db.add(Notification(
            user_id=patient.user_id,
            title="✅ Diagnostic IA complété",
            message=(
                f"Maladie détectée : {maladie_confirmee}. "
                f"{len(docteurs_recommandes)} médecin(s) et "
                f"{len(hopitaux_recommandes)} hôpital(aux) recommandé(s)."
            ),
            type="ia_confirmation",
            data=json.dumps({
                "session_id": session.id,
                "maladie": maladie_confirmee,
                "certain": confirmation.get("diagnostic_certain", True),
            }),
            is_read=False
        ))
        db.commit()
    except Exception as e:
        logger.warning(f"Erreur notification: {e}")
        db.rollback()

    return ConfirmationAvecRecommandationsResponse(
        maladie_confirmee=maladie_confirmee,
        niveau_confiance=confirmation.get("niveau_confiance", 0),
        justification=confirmation.get("justification", ""),
        symptomes_cles=confirmation.get("symptomes_cles", []),
        niveau_urgence=confirmation.get("niveau_urgence", ""),
        recommandations=confirmation.get("recommandations", []),
        quand_consulter_urgence=confirmation.get("quand_consulter_urgence", []),
        avertissement=confirmation.get("avertissement", ""),
        diagnostic_certain=confirmation.get("diagnostic_certain", True),
        maladie_alternative=confirmation.get("maladie_alternative"),
        conseil_consultation=confirmation.get(
            "conseil_consultation",
            "Consultez un médecin pour confirmer."
        ),
        specialites_suggerees=specialites_suggerees,
        docteurs_recommandes=[
            DocteurRecommandeSchema(**d) for d in docteurs_recommandes
        ],
        hopitaux_recommandes=[
            HopitalRecommandeSchema(**h) for h in hopitaux_recommandes
        ],
    )


# ============================================
# HISTORIQUE
# ============================================
@router.get("/sessions", response_model=List[SessionIASchema])
def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=403, detail="Réservé aux patients")
    return db.query(SessionIA).filter(
        SessionIA.patient_id == patient.id
    ).order_by(SessionIA.created_at.desc()).all()


@router.get("/sessions/{session_id}", response_model=SessionIASchema)
def get_session_detail(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=403, detail="Réservé aux patients")
    session = db.query(SessionIA).filter(
        SessionIA.id == session_id,
        SessionIA.patient_id == patient.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable")
    return session


# ============================================
# ENDPOINTS DOCTEURS / HÔPITAUX
# ============================================
@router.get("/docteurs-recommandes", response_model=List[DocteurRecommandeSchema])
def get_docteurs_recommandes(
    maladie: str = Query(...),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    limit: int = Query(5, ge=1, le=20),
    rayon_km: float = Query(50.0, ge=1.0, le=500.0),
    ponderation: str = Query("equilibre"),
    prix_max: Optional[float] = Query(None),
    experience_min: Optional[int] = Query(None),
    note_min: Optional[float] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    specialites = SpecialiteMapper.get_specialites_for_maladie(maladie)
    docteurs = DocteurRecommender.recommander(
        db=db, specialites_noms=specialites,
        patient_lat=lat, patient_lon=lon,
        limit=limit, rayon_km=rayon_km,
        ponderation=ponderation, prix_max=prix_max,
        experience_min=experience_min, note_min=note_min,
    )
    return [DocteurRecommandeSchema(**d) for d in docteurs]


@router.get("/hopitaux-recommandes", response_model=List[HopitalRecommandeSchema])
def get_hopitaux_recommandes(
    maladie: str = Query(...),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    limit: int = Query(5, ge=1, le=20),
    rayon_km: float = Query(100.0, ge=1.0, le=500.0),
    ponderation: str = Query("equilibre"),
    urgence_seulement: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hopitaux = HopitalRecommender.recommander(
        db=db, maladie=maladie,
        patient_lat=lat, patient_lon=lon,
        limit=limit, rayon_km=rayon_km,
        ponderation=ponderation, urgence_seulement=urgence_seulement,
    )
    return [HopitalRecommandeSchema(**h) for h in hopitaux]
@router.get(
    "/sessions/{session_id}/recommandations",
    response_model=ConfirmationAvecRecommandationsResponse
)
def get_session_recommandations(
    session_id: int,
    patient_lat: Optional[float] = Query(None),
    patient_lon: Optional[float] = Query(None),
    ponderation: str = Query("equilibre"),
    rayon_km: float = Query(50.0, ge=1.0, le=500.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reconstruire les recommandations (docteurs + hôpitaux) pour une session passée.
    Utile quand le patient revient sur une analyse depuis l'historique.
    """
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=403, detail="Réservé aux patients")

    session = db.query(SessionIA).filter(
        SessionIA.id == session_id,
        SessionIA.patient_id == patient.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable")

    if not session.maladie_confirmee:
        raise HTTPException(
            status_code=400,
            detail="Cette analyse n'a pas encore de diagnostic final."
        )

    maladie = session.maladie_confirmee

    # Localisation patient
    if patient_lat is None or patient_lon is None:
        loc = db.query(Localisation).filter(
            Localisation.user_id == patient.user_id
        ).first()
        if loc:
            patient_lat = patient_lat or getattr(loc, "latitude", None)
            patient_lon = patient_lon or getattr(loc, "longitude", None)

    # Recommandations
    specialites_suggerees = SpecialiteMapper.get_specialites_for_maladie(maladie)
    docteurs_recommandes = DocteurRecommender.recommander(
        db=db,
        specialites_noms=specialites_suggerees,
        patient_lat=patient_lat,
        patient_lon=patient_lon,
        limit=5,
        rayon_km=rayon_km,
        ponderation=ponderation,
    )

    urgence = False
    if session.recommandations:
        urgence = any("urgence" in str(r).lower() for r in session.recommandations)

    hopitaux_recommandes = HopitalRecommender.recommander(
        db=db,
        maladie=maladie,
        patient_lat=patient_lat,
        patient_lon=patient_lon,
        limit=5,
        rayon_km=max(rayon_km, 100.0),
        ponderation=ponderation,
        urgence_seulement=urgence,
    )

    return ConfirmationAvecRecommandationsResponse(
        maladie_confirmee=maladie,
        niveau_confiance=float(session.niveau_confiance or 0),
        justification="Analyse historique",
        symptomes_cles=session.symptomes or [],
        niveau_urgence="modérée",
        recommandations=session.recommandations or [],
        quand_consulter_urgence=[],
        avertissement="Ceci n'est pas un diagnostic médical.",
        diagnostic_certain=session.diagnostic_certain if session.diagnostic_certain is not None else True,
        maladie_alternative=session.maladie_alternative,
        conseil_consultation=session.conseil_consultation or "",
        specialites_suggerees=specialites_suggerees,
        docteurs_recommandes=[DocteurRecommandeSchema(**d) for d in docteurs_recommandes],
        hopitaux_recommandes=[HopitalRecommandeSchema(**h) for h in hopitaux_recommandes],
    )
@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Supprimer une session IA (RGPD / droit à l'oubli)"""
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=403, detail="Réservé aux patients")

    session = db.query(SessionIA).filter(
        SessionIA.id == session_id,
        SessionIA.patient_id == patient.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable")

    db.delete(session)
    db.commit()
    return {"message": "Session supprimée", "id": session_id}