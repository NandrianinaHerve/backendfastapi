from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import List, Optional
from datetime import datetime, timedelta
import json

from ...core.database import get_db
from ...core.dependencies import get_current_user, require_patient
from ...models.user import User, UserStatus, UserRole
from ...models.patient import Patient
from ...models.docteur import Docteur
from ...models.pharmacie import Pharmacie
from ...models.hopital import Hopital
from ...models.chauffeur import Chauffeur
from ...models.avis import Avis, StatistiqueAvis, TypeService
from ...models.notification import Notification
from ...schemas.avis import (
    AvisCreate,
    AvisUpdate,
    AvisResponse,
    AvisWithPatient,
    ReponseAvis,
    StatistiqueAvisResponse,
    AvisStatsDetail,
    ClassementService,
    MeilleurServiceResponse
)

router = APIRouter(prefix="/avis", tags=["Avis & Notes"])


# ============================================
# HELPER : Créer notification
# ============================================
def create_notification(db, user_id, title, message, type, data=None):
    try:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type,
            data=json.dumps(data) if data else None,
            is_read=False
        )
        db.add(notif)
        return notif
    except Exception as e:
        print(f"⚠️ Erreur notification: {e}")
        return None


# ============================================
# HELPER : Récupérer le service
# ============================================
def get_service_info(db: Session, type_service: TypeService, service_id: int):
    """Récupérer les infos du service selon son type"""
    if type_service == TypeService.DOCTEUR:
        service = db.query(Docteur).filter(Docteur.id == service_id).first()
        if service:
            return {
                "id": service.id,
                "nom": f"Dr. {service.user.prenom} {service.user.nom}",
                "user_id": service.user_id,
                "adresse": service.adresse,
                "telephone": service.user.telephone
            }
    elif type_service == TypeService.PHARMACIE:
        service = db.query(Pharmacie).filter(Pharmacie.id == service_id).first()
        if service:
            return {
                "id": service.id,
                "nom": service.nom,
                "user_id": service.user_id,
                "adresse": service.adresse,
                "telephone": service.telephone
            }
    elif type_service == TypeService.HOPITAL:
        service = db.query(Hopital).filter(Hopital.id == service_id).first()
        if service:
            return {
                "id": service.id,
                "nom": service.nom,
                "user_id": service.user_id,
                "adresse": service.adresse,
                "telephone": service.telephone
            }
    elif type_service == TypeService.CHAUFFEUR:
        service = db.query(Chauffeur).filter(Chauffeur.id == service_id).first()
        if service:
            return {
                "id": service.id,
                "nom": f"{service.user.prenom} {service.user.nom}",
                "user_id": service.user_id,
                "adresse": None,
                "telephone": service.user.telephone
            }
    return None


# ============================================
# HELPER : Mettre à jour les statistiques
# ============================================
def update_statistiques(db: Session, type_service: TypeService, service_id: int):
    """Recalculer les statistiques d'un service"""
    
    avis_list = db.query(Avis).filter(
        Avis.type_service == type_service,
        Avis.service_id == service_id,
        Avis.is_visible == True
    ).all()
    
    if not avis_list:
        # Supprimer les stats si plus d'avis
        db.query(StatistiqueAvis).filter(
            StatistiqueAvis.type_service == type_service,
            StatistiqueAvis.service_id == service_id
        ).delete()
        return
    
    nb_avis = len(avis_list)
    note_moyenne = sum(a.note for a in avis_list) / nb_avis
    note_accueil = [a.note_accueil for a in avis_list if a.note_accueil]
    note_attente = [a.note_attente for a in avis_list if a.note_attente]
    note_proprete = [a.note_proprete for a in avis_list if a.note_proprete]
    note_pro = [a.note_professionnalisme for a in avis_list if a.note_professionnalisme]
    
    # Compter les étoiles
    nb_1 = sum(1 for a in avis_list if a.note == 1)
    nb_2 = sum(1 for a in avis_list if a.note == 2)
    nb_3 = sum(1 for a in avis_list if a.note == 3)
    nb_4 = sum(1 for a in avis_list if a.note == 4)
    nb_5 = sum(1 for a in avis_list if a.note == 5)
    
    # Chercher ou créer les stats
    stats = db.query(StatistiqueAvis).filter(
        StatistiqueAvis.type_service == type_service,
        StatistiqueAvis.service_id == service_id
    ).first()
    
    if not stats:
        stats = StatistiqueAvis(
            type_service=type_service,
            service_id=service_id
        )
        db.add(stats)
    
    stats.nb_avis = nb_avis
    stats.note_moyenne = int(note_moyenne * 10)  # x10 pour éviter les décimales
    stats.note_accueil_moyenne = int(sum(note_accueil) / len(note_accueil) * 10) if note_accueil else 0
    stats.note_attente_moyenne = int(sum(note_attente) / len(note_attente) * 10) if note_attente else 0
    stats.note_proprete_moyenne = int(sum(note_proprete) / len(note_proprete) * 10) if note_proprete else 0
    stats.note_professionnalisme_moyenne = int(sum(note_pro) / len(note_pro) * 10) if note_pro else 0
    stats.nb_1_etoile = nb_1
    stats.nb_2_etoiles = nb_2
    stats.nb_3_etoiles = nb_3
    stats.nb_4_etoiles = nb_4
    stats.nb_5_etoiles = nb_5
    
    db.commit()


# ============================================
# CRÉER UN AVIS (Patient)
# ============================================
@router.post("/", response_model=AvisResponse)
def create_avis(
    avis_data: AvisCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient)
):
    """Donner un avis sur un service (Patient)"""
    
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient non trouvé")
    
    # Vérifier que le service existe
    service_info = get_service_info(db, avis_data.type_service, avis_data.service_id)
    if not service_info:
        raise HTTPException(status_code=404, detail="Service non trouvé")
    
    # Vérifier si le patient a déjà donné un avis
    existing = db.query(Avis).filter(
        Avis.patient_id == patient.id,
        Avis.type_service == avis_data.type_service,
        Avis.service_id == avis_data.service_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Vous avez déjà donné un avis sur ce service. Vous pouvez le modifier."
        )
    
    # Créer l'avis
    avis = Avis(
        patient_id=patient.id,
        **avis_data.dict()
    )
    
    db.add(avis)
    db.commit()
    db.refresh(avis)
    
    # Mettre à jour les statistiques
    update_statistiques(db, avis_data.type_service, avis_data.service_id)
    
    # Notification au service
    create_notification(
        db=db,
        user_id=service_info["user_id"],
        title=f"⭐ Nouvel avis reçu",
        message=(
            f"Vous avez reçu un avis de {avis.note}/5 étoiles. "
            f"{'Commentaire: ' + avis.commentaire[:50] + '...' if avis.commentaire else ''}"
        ),
        type="nouvel_avis",
        data={
            "avis_id": avis.id,
            "note": avis.note,
            "patient_nom": f"{patient.user.prenom} {patient.user.nom}" if not avis.is_anonyme else "Anonyme",
            "commentaire": avis.commentaire
        }
    )
    
    db.commit()
    
    return avis


# ============================================
# LISTE DES AVIS (Public)
# ============================================
@router.get("/service/{type_service}/{service_id}", response_model=List[AvisWithPatient])
def get_service_avis(
    type_service: TypeService,
    service_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    note_min: Optional[int] = Query(None, ge=1, le=5),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Voir les avis d'un service (Public)"""
    
    # Vérifier que le service existe
    service_info = get_service_info(db, type_service, service_id)
    if not service_info:
        raise HTTPException(status_code=404, detail="Service non trouvé")
    
    query = db.query(Avis).filter(
        Avis.type_service == type_service,
        Avis.service_id == service_id,
        Avis.is_visible == True
    )
    
    if note_min:
        query = query.filter(Avis.note >= note_min)
    
    avis_list = query.order_by(Avis.created_at.desc()).offset(offset).limit(limit).all()
    
    # Enrichir avec info patient
    result = []
    for avis in avis_list:
        patient = db.query(Patient).filter(Patient.id == avis.patient_id).first()
        
        avis_dict = {
            "id": avis.id,
            "patient_id": avis.patient_id,
            "type_service": avis.type_service,
            "service_id": avis.service_id,
            "note": avis.note,
            "commentaire": avis.commentaire,
            "note_accueil": avis.note_accueil,
            "note_attente": avis.note_attente,
            "note_proprete": avis.note_proprete,
            "note_professionnalisme": avis.note_professionnalisme,
            "is_anonyme": avis.is_anonyme,
            "reference_type": avis.reference_type,
            "reference_id": avis.reference_id,
            "reponse_service": avis.reponse_service,
            "date_reponse": avis.date_reponse,
            "is_visible": avis.is_visible,
            "nb_signalements": avis.nb_signalements,
            "created_at": avis.created_at,
            "updated_at": avis.updated_at,
            "patient_nom": patient.user.nom if patient and not avis.is_anonyme else None,
            "patient_prenom": patient.user.prenom if patient and not avis.is_anonyme else None,
            "patient_photo": None
        }
        result.append(avis_dict)
    
    return result


# ============================================
# MES AVIS (Patient)
# ============================================
@router.get("/me", response_model=List[AvisResponse])
def get_my_avis(
    type_service: Optional[TypeService] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient)
):
    """Voir mes avis donnés (Patient)"""
    
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient non trouvé")
    
    query = db.query(Avis).filter(Avis.patient_id == patient.id)
    
    if type_service:
        query = query.filter(Avis.type_service == type_service)
    
    return query.order_by(Avis.created_at.desc()).all()


# ============================================
# MODIFIER UN AVIS (Patient)
# ============================================
@router.put("/{avis_id}", response_model=AvisResponse)
def update_avis(
    avis_id: int,
    update_data: AvisUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient)
):
    """Modifier son avis (Patient)"""
    
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient non trouvé")
    
    avis = db.query(Avis).filter(
        Avis.id == avis_id,
        Avis.patient_id == patient.id
    ).first()
    if not avis:
        raise HTTPException(status_code=404, detail="Avis non trouvé")
    
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(avis, field, value)
    
    db.commit()
    db.refresh(avis)
    
    # Mettre à jour les stats
    update_statistiques(db, avis.type_service, avis.service_id)
    
    return avis


# ============================================
# SUPPRIMER UN AVIS (Patient)
# ============================================
@router.delete("/{avis_id}")
def delete_avis(
    avis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient)
):
    """Supprimer son avis (Patient)"""
    
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient non trouvé")
    
    avis = db.query(Avis).filter(
        Avis.id == avis_id,
        Avis.patient_id == patient.id
    ).first()
    if not avis:
        raise HTTPException(status_code=404, detail="Avis non trouvé")
    
    type_service = avis.type_service
    service_id = avis.service_id
    
    db.delete(avis)
    db.commit()
    
    # Mettre à jour les stats
    update_statistiques(db, type_service, service_id)
    
    return {"message": "Avis supprimé avec succès"}


# ============================================
# RÉPONDRE À UN AVIS (Service)
# ============================================
@router.post("/{avis_id}/repondre", response_model=AvisResponse)
def repondre_avis(
    avis_id: int,
    reponse_data: ReponseAvis,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Répondre à un avis (Service)"""
    
    avis = db.query(Avis).filter(Avis.id == avis_id).first()
    if not avis:
        raise HTTPException(status_code=404, detail="Avis non trouvé")
    
    # Vérifier que l'utilisateur est bien le service concerné
    service_info = get_service_info(db, avis.type_service, avis.service_id)
    if not service_info or service_info["user_id"] != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez répondre qu'à vos propres avis"
        )
    
    avis.reponse_service = reponse_data.reponse
    avis.date_reponse = datetime.utcnow()
    
    db.commit()
    db.refresh(avis)
    
    # Notification au patient
    patient = db.query(Patient).filter(Patient.id == avis.patient_id).first()
    if patient:
        create_notification(
            db=db,
            user_id=patient.user_id,
            title="💬 Réponse à votre avis",
            message=f"{service_info['nom']} a répondu à votre avis.",
            type="reponse_avis",
            data={
                "avis_id": avis.id,
                "service_nom": service_info["nom"],
                "reponse": reponse_data.reponse
            }
        )
        db.commit()
    
    return avis


# ============================================
# MES AVIS REÇUS (Service)
# ============================================
@router.get("/me/recus", response_model=List[AvisWithPatient])
def get_my_recus_avis(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Voir les avis reçus (Service)"""
    
    # Déterminer le type de service et l'ID
    type_service = None
    service_id = None
    
    if current_user.role == UserRole.DOCTEUR:
        service = db.query(Docteur).filter(Docteur.user_id == current_user.id).first()
        if service:
            type_service = TypeService.DOCTEUR
            service_id = service.id
    elif current_user.role == UserRole.PHARMACIE:
        service = db.query(Pharmacie).filter(Pharmacie.user_id == current_user.id).first()
        if service:
            type_service = TypeService.PHARMACIE
            service_id = service.id
    elif current_user.role == UserRole.HOPITAL:
        service = db.query(Hopital).filter(Hopital.user_id == current_user.id).first()
        if service:
            type_service = TypeService.HOPITAL
            service_id = service.id
    elif current_user.role == UserRole.CHAUFFEUR:
        service = db.query(Chauffeur).filter(Chauffeur.user_id == current_user.id).first()
        if service:
            type_service = TypeService.CHAUFFEUR
            service_id = service.id
    else:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    if not type_service:
        raise HTTPException(status_code=404, detail="Profil service non trouvé")
    
    avis_list = db.query(Avis).filter(
        Avis.type_service == type_service,
        Avis.service_id == service_id,
        Avis.is_visible == True
    ).order_by(Avis.created_at.desc()).offset(offset).limit(limit).all()
    
    # Enrichir
    result = []
    for avis in avis_list:
        patient = db.query(Patient).filter(Patient.id == avis.patient_id).first()
        result.append({
            "id": avis.id,
            "patient_id": avis.patient_id,
            "type_service": avis.type_service,
            "service_id": avis.service_id,
            "note": avis.note,
            "commentaire": avis.commentaire,
            "note_accueil": avis.note_accueil,
            "note_attente": avis.note_attente,
            "note_proprete": avis.note_proprete,
            "note_professionnalisme": avis.note_professionnalisme,
            "is_anonyme": avis.is_anonyme,
            "reference_type": avis.reference_type,
            "reference_id": avis.reference_id,
            "reponse_service": avis.reponse_service,
            "date_reponse": avis.date_reponse,
            "is_visible": avis.is_visible,
            "nb_signalements": avis.nb_signalements,
            "created_at": avis.created_at,
            "updated_at": avis.updated_at,
            "patient_nom": patient.user.nom if patient and not avis.is_anonyme else None,
            "patient_prenom": patient.user.prenom if patient and not avis.is_anonyme else None,
            "patient_photo": None
        })
    
    return result


# ============================================
# STATISTIQUES D'UN SERVICE
# ============================================
@router.get("/stats/{type_service}/{service_id}", response_model=AvisStatsDetail)
def get_service_stats(
    type_service: TypeService,
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Voir les statistiques d'avis d'un service"""
    
    service_info = get_service_info(db, type_service, service_id)
    if not service_info:
        raise HTTPException(status_code=404, detail="Service non trouvé")
    
    stats = db.query(StatistiqueAvis).filter(
        StatistiqueAvis.type_service == type_service,
        StatistiqueAvis.service_id == service_id
    ).first()
    
    if not stats:
        return {
            "service_id": service_id,
            "type_service": type_service,
            "nom_service": service_info["nom"],
            "nb_avis": 0,
            "note_moyenne": 0.0,
            "note_accueil_moyenne": None,
            "note_attente_moyenne": None,
            "note_proprete_moyenne": None,
            "note_professionnalisme_moyenne": None,
            "distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            "pourcentage_recommandation": 0.0
        }
    
    # Calculer le % de recommandation (4-5 étoiles)
    nb_recommandation = stats.nb_4_etoiles + stats.nb_5_etoiles
    pourcentage = (nb_recommandation / stats.nb_avis * 100) if stats.nb_avis > 0 else 0
    
    return {
        "service_id": service_id,
        "type_service": type_service,
        "nom_service": service_info["nom"],
        "nb_avis": stats.nb_avis,
        "note_moyenne": stats.note_moyenne / 10,
        "note_accueil_moyenne": stats.note_accueil_moyenne / 10 if stats.note_accueil_moyenne else None,
        "note_attente_moyenne": stats.note_attente_moyenne / 10 if stats.note_attente_moyenne else None,
        "note_proprete_moyenne": stats.note_proprete_moyenne / 10 if stats.note_proprete_moyenne else None,
        "note_professionnalisme_moyenne": stats.note_professionnalisme_moyenne / 10 if stats.note_professionnalisme_moyenne else None,
        "distribution": {
            1: stats.nb_1_etoile,
            2: stats.nb_2_etoiles,
            3: stats.nb_3_etoiles,
            4: stats.nb_4_etoiles,
            5: stats.nb_5_etoiles
        },
        "pourcentage_recommandation": round(pourcentage, 1)
    }


# ============================================
# MEILLEURS SERVICES (Classement)
# ============================================
@router.get("/meilleurs", response_model=MeilleurServiceResponse)
def get_meilleurs_services(
    limit: int = Query(10, ge=1, le=50),
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Voir les meilleurs services par catégorie"""
    
    result = MeilleurServiceResponse()
    
    # Fonction pour construire le classement
    def build_classement(type_service: TypeService, limit: int) -> List[ClassementService]:
        stats = db.query(StatistiqueAvis).filter(
            StatistiqueAvis.type_service == type_service,
            StatistiqueAvis.nb_avis >= 1  # Au moins 1 avis
        ).order_by(
            desc(StatistiqueAvis.note_moyenne),
            desc(StatistiqueAvis.nb_avis)
        ).limit(limit).all()
        
        classement = []
        for i, stat in enumerate(stats, 1):
            service_info = get_service_info(db, type_service, stat.service_id)
            if not service_info:
                continue
            
            classement.append({
                "rang": i,
                "service_id": stat.service_id,
                "nom": service_info["nom"],
                "type_service": type_service,
                "note_moyenne": stat.note_moyenne / 10,
                "nb_avis": stat.nb_avis,
                "adresse": service_info.get("adresse"),
                "telephone": service_info.get("telephone"),
                "latitude": None,
                "longitude": None,
                "distance": None
            })
        
        return classement
    
    result.meilleurs_docteurs = build_classement(TypeService.DOCTEUR, limit)
    result.meilleures_pharmacies = build_classement(TypeService.PHARMACIE, limit)
    result.meilleurs_hopitaux = build_classement(TypeService.HOPITAL, limit)
    result.meilleurs_chauffeurs = build_classement(TypeService.CHAUFFEUR, limit)
    
    return result


# ============================================
# TOP MEILLEURS PAR TYPE (Simple)
# ============================================
@router.get("/meilleurs/{type_service}", response_model=List[ClassementService])
def get_meilleurs_by_type(
    type_service: TypeService,
    limit: int = Query(10, ge=1, le=50),
    min_avis: int = Query(1, ge=1),
    db: Session = Depends(get_db)
):
    """Voir les meilleurs services d'un type"""
    
    stats = db.query(StatistiqueAvis).filter(
        StatistiqueAvis.type_service == type_service,
        StatistiqueAvis.nb_avis >= min_avis
    ).order_by(
        desc(StatistiqueAvis.note_moyenne),
        desc(StatistiqueAvis.nb_avis)
    ).limit(limit).all()
    
    classement = []
    for i, stat in enumerate(stats, 1):
        service_info = get_service_info(db, type_service, stat.service_id)
        if not service_info:
            continue
        
        classement.append({
            "rang": i,
            "service_id": stat.service_id,
            "nom": service_info["nom"],
            "type_service": type_service,
            "note_moyenne": stat.note_moyenne / 10,
            "nb_avis": stat.nb_avis,
            "adresse": service_info.get("adresse"),
            "telephone": service_info.get("telephone"),
            "latitude": None,
            "longitude": None,
            "distance": None
        })
    
    return classement