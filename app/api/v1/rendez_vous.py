from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ...core.database import get_db
from ...core.dependencies import get_current_user
from ...models.user import User
from ...models.rendez_vous import RendezVous, AppointmentStatus
from ...models.patient import Patient
from ...models.docteur import Docteur
from ...models.disponibilite import Disponibilite
from ...schemas.rendez_vous import RendezVousCreate, RendezVousResponse, RendezVousUpdate

router = APIRouter(prefix="/rendez-vous", tags=["Rendez-vous"])

@router.post("/", response_model=RendezVousResponse)
def create_rendez_vous(
    rdv_data: RendezVousCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Créer un rendez-vous"""
    # Vérifier que le patient existe
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient and current_user.role.value != "admin":
        # Si l'utilisateur est admin, on prend le patient_id du body
        if not rdv_data.patient_id:
            raise HTTPException(status_code=400, detail="patient_id requis")
        patient = db.query(Patient).filter(Patient.id == rdv_data.patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient non trouvé")
    else:
        rdv_data.patient_id = patient.id
    
    # Vérifier que le docteur existe
    docteur = db.query(Docteur).filter(Docteur.id == rdv_data.docteur_id).first()
    if not docteur:
        raise HTTPException(status_code=404, detail="Docteur non trouvé")
    
    # Vérifier la disponibilité du docteur
    disponibilite = db.query(Disponibilite).filter(
        Disponibilite.docteur_id == rdv_data.docteur_id,
        Disponibilite.date == rdv_data.date.date(),
        Disponibilite.heure_debut <= rdv_data.date,
        Disponibilite.heure_fin >= rdv_data.date,
        Disponibilite.is_available == True
    ).first()
    
    if not disponibilite:
        raise HTTPException(status_code=400, detail="Créneau non disponible")
    
    # Vérifier que le créneau n'est pas déjà pris
    existing = db.query(RendezVous).filter(
        RendezVous.docteur_id == rdv_data.docteur_id,
        RendezVous.date == rdv_data.date,
        RendezVous.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED])
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Créneau déjà réservé")
    
    rdv = RendezVous(
        patient_id=rdv_data.patient_id,
        docteur_id=rdv_data.docteur_id,
        date=rdv_data.date,
        motif=rdv_data.motif,
        notes=rdv_data.notes,
        status=AppointmentStatus.PENDING
    )
    
    db.add(rdv)
    db.commit()
    db.refresh(rdv)
    return rdv

@router.get("/", response_model=List[RendezVousResponse])
def get_rendez_vous(
    status: Optional[AppointmentStatus] = None,
    docteur_id: Optional[int] = None,
    patient_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir la liste des rendez-vous avec filtres"""
    query = db.query(RendezVous)
    
    # Filtres selon le rôle
    if current_user.role.value == "patient":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if patient:
            query = query.filter(RendezVous.patient_id == patient.id)
    elif current_user.role.value == "docteur":
        docteur = db.query(Docteur).filter(Docteur.user_id == current_user.id).first()
        if docteur:
            query = query.filter(RendezVous.docteur_id == docteur.id)
    elif current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    if status:
        query = query.filter(RendezVous.status == status)
    if docteur_id:
        query = query.filter(RendezVous.docteur_id == docteur_id)
    if patient_id:
        query = query.filter(RendezVous.patient_id == patient_id)
    if start_date:
        query = query.filter(RendezVous.date >= start_date)
    if end_date:
        query = query.filter(RendezVous.date <= end_date)
    
    return query.order_by(RendezVous.date).all()

@router.get("/my", response_model=List[RendezVousResponse])
def get_my_rendez_vous(
    status: Optional[AppointmentStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir les rendez-vous de l'utilisateur connecté"""
    query = db.query(RendezVous)
    
    if current_user.role.value == "patient":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if patient:
            query = query.filter(RendezVous.patient_id == patient.id)
    elif current_user.role.value == "docteur":
        docteur = db.query(Docteur).filter(Docteur.user_id == current_user.id).first()
        if docteur:
            query = query.filter(RendezVous.docteur_id == docteur.id)
    else:
        raise HTTPException(status_code=403, detail="Seuls les patients et docteurs peuvent voir leurs rendez-vous")
    
    if status:
        query = query.filter(RendezVous.status == status)
    
    return query.order_by(RendezVous.date).all()

@router.get("/{rdv_id}", response_model=RendezVousResponse)
def get_rendez_vous_by_id(
    rdv_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir un rendez-vous par ID"""
    rdv = db.query(RendezVous).filter(RendezVous.id == rdv_id).first()
    if not rdv:
        raise HTTPException(status_code=404, detail="Rendez-vous non trouvé")
    
    # Vérifier les droits
    if current_user.role.value == "patient":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if patient and rdv.patient_id != patient.id:
            raise HTTPException(status_code=403, detail="Accès non autorisé")
    elif current_user.role.value == "docteur":
        docteur = db.query(Docteur).filter(Docteur.user_id == current_user.id).first()
        if docteur and rdv.docteur_id != docteur.id:
            raise HTTPException(status_code=403, detail="Accès non autorisé")
    elif current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    return rdv

@router.put("/{rdv_id}", response_model=RendezVousResponse)
def update_rendez_vous(
    rdv_id: int,
    rdv_update: RendezVousUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mettre à jour un rendez-vous"""
    rdv = db.query(RendezVous).filter(RendezVous.id == rdv_id).first()
    if not rdv:
        raise HTTPException(status_code=404, detail="Rendez-vous non trouvé")
    
    # Vérifier les droits
    if current_user.role.value == "docteur":
        docteur = db.query(Docteur).filter(Docteur.user_id == current_user.id).first()
        if not docteur or rdv.docteur_id != docteur.id:
            raise HTTPException(status_code=403, detail="Accès non autorisé")
    elif current_user.role.value == "patient":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient or rdv.patient_id != patient.id:
            raise HTTPException(status_code=403, detail="Accès non autorisé")
    elif current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    if rdv_update.date:
        rdv.date = rdv_update.date
    if rdv_update.status:
        rdv.status = rdv_update.status
    if rdv_update.motif is not None:
        rdv.motif = rdv_update.motif
    if rdv_update.notes is not None:
        rdv.notes = rdv_update.notes
    
    db.commit()
    db.refresh(rdv)
    return rdv

@router.delete("/{rdv_id}")
def delete_rendez_vous(
    rdv_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Annuler un rendez-vous"""
    rdv = db.query(RendezVous).filter(RendezVous.id == rdv_id).first()
    if not rdv:
        raise HTTPException(status_code=404, detail="Rendez-vous non trouvé")
    
    if current_user.role.value != "admin":
        # Vérifier que l'utilisateur est le patient ou le docteur concerné
        if current_user.role.value == "patient":
            patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
            if not patient or rdv.patient_id != patient.id:
                raise HTTPException(status_code=403, detail="Accès non autorisé")
        elif current_user.role.value == "docteur":
            docteur = db.query(Docteur).filter(Docteur.user_id == current_user.id).first()
            if not docteur or rdv.docteur_id != docteur.id:
                raise HTTPException(status_code=403, detail="Accès non autorisé")
        else:
            raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    rdv.status = AppointmentStatus.CANCELLED
    db.commit()
    return {"message": "Rendez-vous annulé avec succès"}