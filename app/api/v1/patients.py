from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint

from ...core.database import get_db
from ...core.dependencies import require_patient
from ...core.security import get_password_hash
from ...models.user import User, UserRole, UserStatus
from ...models.patient import Patient
from ...schemas.patient import PatientCreate, PatientResponse, PatientUpdate
from ...schemas.user import UserCreate

router = APIRouter(prefix="/patients", tags=["Patients"])

@router.post("/register", response_model=PatientResponse)
def register_patient(
    patient_data: PatientCreate,
    db: Session = Depends(get_db)
):
    """Inscription d'un nouveau patient"""
    # Vérifier si l'email ou téléphone existe déjà
    existing_user = db.query(User).filter(
        (User.email == patient_data.user.email) | 
        (User.telephone == patient_data.user.telephone)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email ou téléphone déjà utilisé"
        )
    
    # Créer l'utilisateur
    user = User(
        nom=patient_data.user.nom,
        prenom=patient_data.user.prenom,
        email=patient_data.user.email,
        telephone=patient_data.user.telephone,
        password=get_password_hash(patient_data.user.password),
        role=UserRole.PATIENT,
        status=UserStatus.APPROVED  # Patients automatiquement approuvés
    )
    db.add(user)
    db.flush()
    
    # Créer le patient
    patient = Patient(
        user_id=user.id,
        date_naissance=patient_data.date_naissance
    )
    
    if patient_data.latitude and patient_data.longitude:
        patient.localisation = ST_SetSRID(
            ST_MakePoint(patient_data.longitude, patient_data.latitude),
            4326
        )
    
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient

@router.get("/me", response_model=PatientResponse)
def get_my_patient_profile(
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    """Obtenir le profil du patient connecté"""
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil patient non trouvé"
        )
    return patient

@router.put("/me", response_model=PatientResponse)
def update_my_patient_profile(
    patient_update: PatientUpdate,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    """Mettre à jour le profil du patient connecté"""
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil patient non trouvé"
        )
    
    if patient_update.date_naissance:
        patient.date_naissance = patient_update.date_naissance
    
    if patient_update.latitude is not None and patient_update.longitude is not None:
        patient.localisation = ST_SetSRID(
            ST_MakePoint(patient_update.longitude, patient_update.latitude),
            4326
        )
    
    db.commit()
    db.refresh(patient)
    return patient

@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient_by_id(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient)
):
    """Obtenir un patient par ID (uniquement si c'est le sien ou admin)"""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient non trouvé"
        )
    
    if current_user.role != UserRole.ADMIN and current_user.id != patient.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )
    
    return patient