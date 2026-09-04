from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint, ST_Distance, ST_Transform

from ...core.database import get_db
from ...core.dependencies import get_current_user
from ...models.user import User
from ...models.patient import Patient
from ...models.chauffeur import Chauffeur
from ...models.demande_transport import DemandeTransport, TransportStatus, TransportType
from ...models.vehicule import Vehicule
from ...schemas.demande_transport import DemandeTransportCreate, DemandeTransportResponse, DemandeTransportUpdate

router = APIRouter(prefix="/transport", tags=["Transport"])

@router.post("/demande", response_model=DemandeTransportResponse)
def create_transport_request(
    demande_data: DemandeTransportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Créer une demande de transport (ambulance ou taxi)"""
    # Vérifier que l'utilisateur est un patient
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=403, detail="Seuls les patients peuvent faire une demande de transport")
    
    point_depart = ST_SetSRID(ST_MakePoint(demande_data.longitude_depart, demande_data.latitude_depart), 4326)
    point_arrivee = None
    if demande_data.latitude_arrivee and demande_data.longitude_arrivee:
        point_arrivee = ST_SetSRID(ST_MakePoint(demande_data.longitude_arrivee, demande_data.latitude_arrivee), 4326)
    
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
    
    # Rechercher automatiquement le chauffeur le plus proche
    find_nearest_driver(demande, db)
    
    return demande

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
    
    return query.order_by(DemandeTransport.created_at.desc()).all()

@router.get("/demandes/pending", response_model=List[DemandeTransportResponse])
def get_pending_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir les demandes en attente (pour les chauffeurs)"""
    if current_user.role.value != "chauffeur":
        raise HTTPException(status_code=403, detail="Seuls les chauffeurs peuvent voir les demandes en attente")
    
    chauffeur = db.query(Chauffeur).filter(Chauffeur.user_id == current_user.id).first()
    if not chauffeur:
        raise HTTPException(status_code=404, detail="Chauffeur non trouvé")
    
    # Trouver les demandes du même type que le véhicule du chauffeur
    type = chauffeur.vehicle_type
    if type == "ambulance":
        type_enum = TransportType.AMBULANCE
    else:
        type_enum = TransportType.TAXI
    
    return db.query(DemandeTransport).filter(
        DemandeTransport.type == type_enum,
        DemandeTransport.status == TransportStatus.PENDING
    ).order_by(DemandeTransport.created_at).all()

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
        if not chauffeur or (demande.chauffeur_id and demande.chauffeur_id != chauffeur.id):
            # Si la demande n'a pas de chauffeur, le chauffeur peut l'accepter
            if not demande.chauffeur_id:
                demande.chauffeur_id = chauffeur.id
                demande.status = TransportStatus.ACCEPTED
            else:
                raise HTTPException(status_code=403, detail="Accès non autorisé")
    elif current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
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
    return demande

@router.post("/demandes/{demande_id}/accept")
def accept_transport_request(
    demande_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Accepter une demande de transport (pour les chauffeurs)"""
    if current_user.role.value != "chauffeur":
        raise HTTPException(status_code=403, detail="Seuls les chauffeurs peuvent accepter des demandes")
    
    chauffeur = db.query(Chauffeur).filter(Chauffeur.user_id == current_user.id).first()
    if not chauffeur:
        raise HTTPException(status_code=404, detail="Chauffeur non trouvé")
    
    demande = db.query(DemandeTransport).filter(
        DemandeTransport.id == demande_id,
        DemandeTransport.status == TransportStatus.PENDING
    ).first()
    
    if not demande:
        raise HTTPException(status_code=404, detail="Demande non trouvée ou déjà traitée")
    
    # Vérifier que le type de véhicule correspond
    if demande.type.value != chauffeur.vehicle_type:
        raise HTTPException(status_code=400, detail="Type de véhicule ne correspond pas")
    
    demande.chauffeur_id = chauffeur.id
    demande.status = TransportStatus.ACCEPTED
    db.commit()
    
    return {"message": "Demande acceptée", "demande_id": demande.id}

def find_nearest_driver(demande: DemandeTransport, db: Session):
    """Trouver le chauffeur le plus proche pour une demande"""
    # Cette fonction serait appelée automatiquement
    # Elle pourrait utiliser Redis pour les positions en temps réel
    pass