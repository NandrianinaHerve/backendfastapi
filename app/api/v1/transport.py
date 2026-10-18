from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint, ST_AsText, ST_Distance, ST_Transform
from datetime import datetime
import json

from ...core.database import get_db
from ...core.dependencies import get_current_user, require_patient, require_chauffeur
from ...models.user import User, UserStatus
from ...models.patient import Patient
from ...models.chauffeur import Chauffeur
from ...models.demande_transport import DemandeTransport, TransportStatus, TransportType
from ...models.notification import Notification
from ...schemas.demande_transport import (
    DemandeTransportCreate, 
    DemandeTransportResponse, 
    DemandeTransportUpdate
)

router = APIRouter(prefix="/transport", tags=["Transport"])


# ============================================
# CRÉER UNE DEMANDE
# ============================================
@router.post("/demande", response_model=DemandeTransportResponse)
def create_transport_request(
    demande_data: DemandeTransportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient)
):
    """Créer une demande de transport (ambulance ou taxi)"""
    
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=403, detail="Patient non trouvé")
    
    point_depart = ST_SetSRID(
        ST_MakePoint(demande_data.longitude_depart, demande_data.latitude_depart),
        4326
    )
    point_arrivee = None
    if demande_data.latitude_arrivee and demande_data.longitude_arrivee:
        point_arrivee = ST_SetSRID(
            ST_MakePoint(demande_data.longitude_arrivee, demande_data.latitude_arrivee),
            4326
        )
    
    demande = DemandeTransport(
        patient_id=patient.id,
        type=demande_data.type,
        point_depart=point_depart,
        point_arrivee=point_arrivee,
        destination=demande_data.destination,
        notes=demande_data.notes,
        status=TransportStatus.PENDING
    )
    
    db.add(demande)
    db.commit()
    db.refresh(demande)
    
    # Extraire les coordonnées
    latitude_depart, longitude_depart = None, None
    if demande.point_depart:
        point_text = db.execute(func.ST_AsText(demande.point_depart)).scalar()
        if point_text:
            coords = point_text.replace("POINT(", "").replace(")", "").split()
            longitude_depart = float(coords[0])
            latitude_depart = float(coords[1])
    
    latitude_arrivee, longitude_arrivee = None, None
    if demande.point_arrivee:
        point_text = db.execute(func.ST_AsText(demande.point_arrivee)).scalar()
        if point_text:
            coords = point_text.replace("POINT(", "").replace(")", "").split()
            longitude_arrivee = float(coords[0])
            latitude_arrivee = float(coords[1])
    
    # Notification patient
    notification_patient = Notification(
        user_id=patient.user_id,
        title=f"🚗 Demande de {demande.type.value} envoyée",
        message=(
            f"Votre demande de {demande.type.value} vers "
            f"{demande.destination or 'votre destination'} a été envoyée. "
            f"Recherche d'un chauffeur en cours..."
        ),
        type="transport_request",
        data=json.dumps({
            "demande_id": demande.id,
            "type": demande.type.value,
            "destination": demande.destination,
            "status": "pending"
        }),
        is_read=False
    )
    db.add(notification_patient)
    
    # Notifications aux chauffeurs
    chauffeurs = db.query(Chauffeur).join(User).filter(
        User.status == UserStatus.APPROVED,
        Chauffeur.is_available == True,
        Chauffeur.vehicle_type == demande.type.value.upper()
    ).all()
    
    for chauffeur in chauffeurs:
        notification_chauffeur = Notification(
            user_id=chauffeur.user_id,
            title=f"🚗 Nouvelle demande de {demande.type.value}",
            message=(
                f"{patient.user.prenom} {patient.user.nom} demande un {demande.type.value} "
                f"vers {demande.destination or 'destination inconnue'}."
            ),
            type="transport_request",
            data=json.dumps({
                "demande_id": demande.id,
                "patient_name": f"{patient.user.prenom} {patient.user.nom}",
                "type": demande.type.value,
                "destination": demande.destination,
                "latitude_depart": latitude_depart,
                "longitude_depart": longitude_depart,
                "status": "pending"
            }),
            is_read=False
        )
        db.add(notification_chauffeur)
    
    db.commit()
    
    return {
        "id": demande.id,
        "patient_id": demande.patient_id,
        "chauffeur_id": demande.chauffeur_id,
        "type": demande.type,
        "status": demande.status,
        "destination": demande.destination,
        "notes": demande.notes,
        "latitude_depart": latitude_depart,
        "longitude_depart": longitude_depart,
        "latitude_arrivee": latitude_arrivee,
        "longitude_arrivee": longitude_arrivee,
        "created_at": demande.created_at,
        "updated_at": demande.updated_at
    }


# ============================================
# LISTE DES DEMANDES
# ============================================
@router.get("/demandes", response_model=List[DemandeTransportResponse])
def get_transport_requests(
    status: Optional[TransportStatus] = None,
    type: Optional[TransportType] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir les demandes de transport avec filtres"""
    query = db.query(DemandeTransport)
    
    if current_user.role.value == "patient":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if patient:
            query = query.filter(DemandeTransport.patient_id == patient.id)
    elif current_user.role.value == "chauffeur":
        chauffeur = db.query(Chauffeur).filter(Chauffeur.user_id == current_user.id).first()
        if chauffeur:
            query = query.filter(DemandeTransport.chauffeur_id == chauffeur.id)
    elif current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    if status:
        query = query.filter(DemandeTransport.status == status)
    if type:
        query = query.filter(DemandeTransport.type == type)
    
    demandes = query.order_by(DemandeTransport.created_at.desc()).all()
    
    result = []
    for demande in demandes:
        lat_dep, lon_dep = None, None
        if demande.point_depart:
            point_text = db.execute(func.ST_AsText(demande.point_depart)).scalar()
            if point_text:
                coords = point_text.replace("POINT(", "").replace(")", "").split()
                lon_dep = float(coords[0])
                lat_dep = float(coords[1])
        
        lat_arr, lon_arr = None, None
        if demande.point_arrivee:
            point_text = db.execute(func.ST_AsText(demande.point_arrivee)).scalar()
            if point_text:
                coords = point_text.replace("POINT(", "").replace(")", "").split()
                lon_arr = float(coords[0])
                lat_arr = float(coords[1])
        
        result.append({
            "id": demande.id,
            "patient_id": demande.patient_id,
            "chauffeur_id": demande.chauffeur_id,
            "type": demande.type,
            "status": demande.status,
            "destination": demande.destination,
            "notes": demande.notes,
            "latitude_depart": lat_dep,
            "longitude_depart": lon_dep,
            "latitude_arrivee": lat_arr,
            "longitude_arrivee": lon_arr,
            "created_at": demande.created_at,
            "updated_at": demande.updated_at
        })
    
    return result


# ============================================
# DEMANDES EN ATTENTE (pour les chauffeurs)
# ============================================
@router.get("/demandes/pending", response_model=List[DemandeTransportResponse])
def get_pending_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_chauffeur)
):
    """Obtenir les demandes en attente (pour les chauffeurs)"""
    chauffeur = db.query(Chauffeur).filter(Chauffeur.user_id == current_user.id).first()
    if not chauffeur:
        raise HTTPException(status_code=404, detail="Chauffeur non trouvé")
    
    type_enum = TransportType.AMBULANCE if chauffeur.vehicle_type == "AMBULANCE" else TransportType.TAXI
    
    demandes = db.query(DemandeTransport).filter(
        DemandeTransport.type == type_enum,
        DemandeTransport.status == TransportStatus.PENDING
    ).order_by(DemandeTransport.created_at).all()
    
    result = []
    for demande in demandes:
        lat_dep, lon_dep = None, None
        if demande.point_depart:
            point_text = db.execute(func.ST_AsText(demande.point_depart)).scalar()
            if point_text:
                coords = point_text.replace("POINT(", "").replace(")", "").split()
                lon_dep = float(coords[0])
                lat_dep = float(coords[1])
        
        lat_arr, lon_arr = None, None
        if demande.point_arrivee:
            point_text = db.execute(func.ST_AsText(demande.point_arrivee)).scalar()
            if point_text:
                coords = point_text.replace("POINT(", "").replace(")", "").split()
                lon_arr = float(coords[0])
                lat_arr = float(coords[1])
        
        result.append({
            "id": demande.id,
            "patient_id": demande.patient_id,
            "chauffeur_id": demande.chauffeur_id,
            "type": demande.type,
            "status": demande.status,
            "destination": demande.destination,
            "notes": demande.notes,
            "latitude_depart": lat_dep,
            "longitude_depart": lon_dep,
            "latitude_arrivee": lat_arr,
            "longitude_arrivee": lon_arr,
            "created_at": demande.created_at,
            "updated_at": demande.updated_at
        })
    
    return result


# ============================================
# ✅ ACCEPTER UNE DEMANDE
# ============================================
@router.post("/demandes/{demande_id}/accept")
def accept_transport_request(
    demande_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_chauffeur)
):
    """Accepter une demande de transport (Chauffeur uniquement)"""
    
    # Vérifier le chauffeur
    chauffeur = db.query(Chauffeur).filter(
        Chauffeur.user_id == current_user.id
    ).first()
    if not chauffeur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil chauffeur non trouvé"
        )
    
    # Vérifier la disponibilité
    if not chauffeur.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous devez être disponible pour accepter une demande"
        )
    
    # Trouver la demande
    demande = db.query(DemandeTransport).filter(
        DemandeTransport.id == demande_id,
        DemandeTransport.status == TransportStatus.PENDING
    ).first()
    
    if not demande:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demande non trouvée ou déjà traitée"
        )
    
    # Vérifier le type de véhicule
    # if demande.type.value.upper() != chauffeur.vehicle_type:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail=f"Type de véhicule ne correspond pas"
    #     )
    demande_type = str(demande.type.value).upper() if demande.type else ""
    chauffeur_type = str(chauffeur.vehicle_type.value).upper() if chauffeur.vehicle_type else ""
    
    print(f"🔍 Debug comparaison:")
    print(f"   demande.type = {demande.type}")
    print(f"   demande.type.value = {demande.type.value if demande.type else 'None'}")
    print(f"   demande_type (normalisé) = '{demande_type}'")
    print(f"   chauffeur.vehicle_type = {chauffeur.vehicle_type}")
    print(f"   chauffeur_type (normalisé) = '{chauffeur_type}'")
    
    if demande_type != chauffeur_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Type de véhicule ne correspond pas. "
                f"Demande: '{demande_type}', "
                f"Votre véhicule: '{chauffeur_type}'"
            )
        )
    
    # Accepter
    demande.chauffeur_id = chauffeur.id
    demande.status = TransportStatus.ACCEPTED
    db.commit()
    db.refresh(demande)
    
    # Notification au patient
    patient = db.query(Patient).filter(Patient.id == demande.patient_id).first()
    
    if patient:
        notification = Notification(
            user_id=patient.user_id,
            title="✅ Chauffeur accepté",
            message=(
                f"{chauffeur.user.prenom} {chauffeur.user.nom} "
                f"({chauffeur.vehicle_type}) a accepté votre demande. "
                f"Il est en route vers vous."
            ),
            type="transport_accepted",
            data=json.dumps({
                "demande_id": demande.id,
                "chauffeur_id": chauffeur.id,
                "chauffeur_name": f"{chauffeur.user.prenom} {chauffeur.user.nom}",
                "chauffeur_phone": chauffeur.user.telephone,
                "vehicle_type": chauffeur.vehicle_type,
                "status": "accepted"
            }),
            is_read=False
        )
        db.add(notification)
        db.commit()
    
    return {
        "message": "Demande acceptée avec succès",
        "demande_id": demande.id,
        "chauffeur_id": chauffeur.id,
        "chauffeur_name": f"{chauffeur.user.prenom} {chauffeur.user.nom}",
        "status": demande.status.value
    }


# ============================================
# METTRE À JOUR UNE DEMANDE
# ============================================
@router.put("/demandes/{demande_id}", response_model=DemandeTransportResponse)
def update_transport_request(
    demande_id: int,
    update_data: DemandeTransportUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mettre à jour une demande de transport"""
    demande = db.query(DemandeTransport).filter(DemandeTransport.id == demande_id).first()
    if not demande:
        raise HTTPException(status_code=404, detail="Demande non trouvée")
    
    # Vérifier les droits
    if current_user.role.value == "patient":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient or demande.patient_id != patient.id:
            raise HTTPException(status_code=403, detail="Accès non autorisé")
    elif current_user.role.value == "chauffeur":
        chauffeur = db.query(Chauffeur).filter(Chauffeur.user_id == current_user.id).first()
        if not chauffeur:
            raise HTTPException(status_code=404, detail="Chauffeur non trouvé")
        
        if not demande.chauffeur_id:
            demande.chauffeur_id = chauffeur.id
            demande.status = TransportStatus.ACCEPTED
        elif demande.chauffeur_id != chauffeur.id:
            raise HTTPException(status_code=403, detail="Accès non autorisé")
    elif current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    old_status = demande.status
    
    if update_data.status:
        demande.status = update_data.status
    if update_data.destination:
        demande.destination = update_data.destination
    if update_data.chauffeur_id:
        chauffeur = db.query(Chauffeur).filter(Chauffeur.id == update_data.chauffeur_id).first()
        if chauffeur:
            demande.chauffeur_id = update_data.chauffeur_id
    
    db.commit()
    db.refresh(demande)
    
    # Notifications selon le statut
    patient = db.query(Patient).filter(Patient.id == demande.patient_id).first()
    chauffeur = db.query(Chauffeur).filter(Chauffeur.id == demande.chauffeur_id).first() if demande.chauffeur_id else None
    
    if update_data.status and update_data.status != old_status:
        if update_data.status == TransportStatus.IN_PROGRESS and chauffeur:
            notification = Notification(
                user_id=patient.user_id,
                title="🚗 Chauffeur en route",
                message=f"{chauffeur.user.prenom} {chauffeur.user.nom} est en route.",
                type="transport_in_progress",
                data=json.dumps({"demande_id": demande.id, "status": "in_progress"}),
                is_read=False
            )
            db.add(notification)
        
        elif update_data.status == TransportStatus.ARRIVED and chauffeur:
            notification = Notification(
                user_id=patient.user_id,
                title="📍 Chauffeur arrivé",
                message=f"{chauffeur.user.prenom} {chauffeur.user.nom} est arrivé.",
                type="transport_arrived",
                data=json.dumps({"demande_id": demande.id, "status": "arrived"}),
                is_read=False
            )
            db.add(notification)
        
        elif update_data.status == TransportStatus.COMPLETED and chauffeur:
            for user_id in [patient.user_id, chauffeur.user_id]:
                notification = Notification(
                    user_id=user_id,
                    title="✅ Course terminée",
                    message="La course est terminée. Merci d'avoir utilisé Santé-Fianarantsoa !",
                    type="transport_completed",
                    data=json.dumps({"demande_id": demande.id, "status": "completed"}),
                    is_read=False
                )
                db.add(notification)
        
        db.commit()
    
    # Extraire les coordonnées
    lat_dep, lon_dep = None, None
    if demande.point_depart:
        point_text = db.execute(func.ST_AsText(demande.point_depart)).scalar()
        if point_text:
            coords = point_text.replace("POINT(", "").replace(")", "").split()
            lon_dep = float(coords[0])
            lat_dep = float(coords[1])
    
    lat_arr, lon_arr = None, None
    if demande.point_arrivee:
        point_text = db.execute(func.ST_AsText(demande.point_arrivee)).scalar()
        if point_text:
            coords = point_text.replace("POINT(", "").replace(")", "").split()
            lon_arr = float(coords[0])
            lat_arr = float(coords[1])
    
    return {
        "id": demande.id,
        "patient_id": demande.patient_id,
        "chauffeur_id": demande.chauffeur_id,
        "type": demande.type,
        "status": demande.status,
        "destination": demande.destination,
        "notes": demande.notes,
        "latitude_depart": lat_dep,
        "longitude_depart": lon_dep,
        "latitude_arrivee": lat_arr,
        "longitude_arrivee": lon_arr,
        "created_at": demande.created_at,
        "updated_at": demande.updated_at
    }