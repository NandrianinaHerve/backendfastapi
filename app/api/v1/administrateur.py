# app/api/v1/administrateur.py
import json

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from geoalchemy2 import functions as geo_func
from sqlalchemy import func

from app.models.notification import Notification

from ...core.database import get_db
from ...core.dependencies import require_admin
from ...core.security import get_password_hash
from ...models.user import User, UserStatus, UserRole
from ...models.administrateur import Administrateur
from ...schemas.administrateur import AdministrateurCreate, AdministrateurResponse, AdministrateurUpdate
from ...schemas.user import UserResponse
from ...models.docteur import Docteur
from ...models.pharmacie import Pharmacie
from ...models.hopital import Hopital
from ...models.chauffeur import Chauffeur
from ...models.patient import Patient

router = APIRouter(prefix="/admin", tags=["Administration"])

# ============================================
# INSCRIPTION ADMIN
# ============================================

@router.post("/register", response_model=AdministrateurResponse)
def register_admin(
    admin_data: AdministrateurCreate,
    db: Session = Depends(get_db)
):
    """Inscription d'un administrateur (compte directement approuvé)"""
    existing_user = db.query(User).filter(
        (User.email == admin_data.user.email) | 
        (User.telephone == admin_data.user.telephone)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email ou téléphone déjà utilisé"
        )
    
    # Créer l'utilisateur admin
    user = User(
        nom=admin_data.user.nom,
        prenom=admin_data.user.prenom,
        email=admin_data.user.email,
        telephone=admin_data.user.telephone,
        password=get_password_hash(admin_data.user.password),
        role=UserRole.ADMIN,
        status=UserStatus.APPROVED  # Admin directement approuvé
    )
    db.add(user)
    db.flush()
    
    # Créer le profil administrateur
    administrateur = Administrateur(
        user_id=user.id,
        poste=admin_data.poste,
        notes=admin_data.notes
    )
    db.add(administrateur)
    db.commit()
    db.refresh(administrateur)
    return administrateur

# ============================================
# GESTION DES UTILISATEURS
# ============================================

@router.get("/users/pending", response_model=List[UserResponse])
def get_pending_users(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Liste des utilisateurs en attente de validation"""
    users = db.query(User).filter(
        User.status == UserStatus.PENDING,
        User.role != UserRole.ADMIN
    ).offset(offset).limit(limit).all()
    return users

# @router.get("/users", response_model=List[UserResponse])
# def get_all_users(
#     status: Optional[UserStatus] = None,
#     role: Optional[UserRole] = None,
#     limit: int = Query(50, ge=1, le=100),
#     offset: int = Query(0, ge=0),
#     db: Session = Depends(get_db),
#     current_user: User = Depends(require_admin)
# ):
#     """Liste de tous les utilisateurs avec filtres"""
#     query = db.query(User)
#     if status:
#         query = query.filter(User.status == status)
#     if role:
#         query = query.filter(User.role == role)
#     return query.offset(offset).limit(limit).all()
@router.get("/users")
def get_all_users(
    status: Optional[UserStatus] = None,
    role: Optional[UserRole] = None,
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Liste de tous les utilisateurs avec coordonnées GPS"""
    query = db.query(User)
    if status:
        query = query.filter(User.status == status)
    if role:
        query = query.filter(User.role == role)
    
    users = query.offset(offset).limit(limit).all()
    
    # Enrichir chaque utilisateur avec ses coordonnées
    result = []
    for u in users:
        lat, lon = None, None
        adresse = None
        specialite = None
        services = None
        vehicle_type = None
        is_open = None
        
        if u.role == UserRole.DOCTEUR and u.docteur:
            if u.docteur.localisation is not None:
                coords = db.query(
                    geo_func.ST_Y(Docteur.localisation).label("lat"),
                    geo_func.ST_X(Docteur.localisation).label("lon")
                ).filter(Docteur.id == u.docteur.id).first()
                if coords:
                    lat = float(coords.lat) if coords.lat else None
                    lon = float(coords.lon) if coords.lon else None
            adresse = u.docteur.adresse
            specialite = u.docteur.specialite.nom if u.docteur.specialite else None
        
        elif u.role == UserRole.PHARMACIE and u.pharmacie:
            if u.pharmacie.localisation is not None:
                coords = db.query(
                    geo_func.ST_Y(Pharmacie.localisation).label("lat"),
                    geo_func.ST_X(Pharmacie.localisation).label("lon")
                ).filter(Pharmacie.id == u.pharmacie.id).first()
                if coords:
                    lat = float(coords.lat) if coords.lat else None
                    lon = float(coords.lon) if coords.lon else None
            adresse = u.pharmacie.adresse
            is_open = u.pharmacie.is_open
        
        elif u.role == UserRole.HOPITAL and u.hopital:
            if u.hopital.localisation is not None:
                coords = db.query(
                    geo_func.ST_Y(Hopital.localisation).label("lat"),
                    geo_func.ST_X(Hopital.localisation).label("lon")
                ).filter(Hopital.id == u.hopital.id).first()
                if coords:
                    lat = float(coords.lat) if coords.lat else None
                    lon = float(coords.lon) if coords.lon else None
            adresse = u.hopital.adresse
            services = u.hopital.services
        
        elif u.role == UserRole.CHAUFFEUR and u.chauffeur:
            if u.chauffeur.localisation is not None:
                coords = db.query(
                    geo_func.ST_Y(Chauffeur.localisation).label("lat"),
                    geo_func.ST_X(Chauffeur.localisation).label("lon")
                ).filter(Chauffeur.id == u.chauffeur.id).first()
                if coords:
                    lat = float(coords.lat) if coords.lat else None
                    lon = float(coords.lon) if coords.lon else None
            vehicle_type = u.chauffeur.vehicle_type.value if u.chauffeur.vehicle_type else None
        
        elif u.role == UserRole.PATIENT and u.patient:
            # Patient peut avoir une localisation si le modèle le supporte
            if hasattr(u.patient, 'localisation') and u.patient.localisation is not None:
                coords = db.query(
                    geo_func.ST_Y(Patient.localisation).label("lat"),
                    geo_func.ST_X(Patient.localisation).label("lon")
                ).filter(Patient.id == u.patient.id).first()
                if coords:
                    lat = float(coords.lat) if coords.lat else None
                    lon = float(coords.lon) if coords.lon else None
        
        result.append({
            "id": u.id,
            "nom": u.nom,
            "prenom": u.prenom,
            "email": u.email,
            "telephone": u.telephone,
            "role": u.role.value,
            "status": u.status.value,
            "is_active": u.is_active,
            "is_verified": u.is_verified,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            # ⭐ Coordonnées GPS
            "latitude": lat,
            "longitude": lon,
            "adresse": adresse,
            "specialite": specialite,
            "services": services,
            "vehicle_type": vehicle_type,
            "is_open": is_open,
        })
    
    return result

@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Détails d'un utilisateur"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return user

# @router.put("/users/{user_id}/approve", response_model=UserResponse)
# def approve_user(
#     user_id: int,
#     db: Session = Depends(get_db),
#     current_admin: User = Depends(require_admin)
# ):
#     """Approuver un utilisateur"""
#     user = db.query(User).filter(User.id == user_id).first()
#     if not user:
#         raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
#     if user.status != UserStatus.PENDING:
#         raise HTTPException(
#             status_code=400,
#             detail=f"L'utilisateur a déjà le statut: {user.status.value}"
#         )
    
#     user.status = UserStatus.APPROVED
#     user.validated_at = datetime.utcnow()
#     user.validated_by = current_admin.id
#     db.commit()
#     db.refresh(user)
#     return user

# @router.put("/users/{user_id}/reject", response_model=UserResponse)
# def reject_user(
#     user_id: int,
#     db: Session = Depends(get_db),
#     current_admin: User = Depends(require_admin)
# ):
#     """Rejeter un utilisateur"""
#     user = db.query(User).filter(User.id == user_id).first()
#     if not user:
#         raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
#     if user.status != UserStatus.PENDING:
#         raise HTTPException(
#             status_code=400,
#             detail=f"L'utilisateur a déjà le statut: {user.status.value}"
#         )
    
#     user.status = UserStatus.REJECTED
#     user.validated_at = datetime.utcnow()
#     user.validated_by = current_admin.id
#     db.commit()
#     db.refresh(user)
#     return user

# @router.put("/users/{user_id}/suspend", response_model=UserResponse)
# def suspend_user(
#     user_id: int,
#     db: Session = Depends(get_db),
#     current_admin: User = Depends(require_admin)
# ):
#     """Suspendre un utilisateur"""
#     user = db.query(User).filter(User.id == user_id).first()
#     if not user:
#         raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
#     if user.role == UserRole.ADMIN:
#         raise HTTPException(status_code=403, detail="Impossible de suspendre un administrateur")
    
#     user.status = UserStatus.SUSPENDED
#     db.commit()
#     db.refresh(user)
#     return user
@router.put("/users/{user_id}/approve", response_model=UserResponse)
def approve_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """Approuver un utilisateur"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    if user.status != UserStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"L'utilisateur a déjà le statut: {user.status.value}"
        )
    
    user.status = UserStatus.APPROVED
    user.validated_at = datetime.now()
    user.validated_by = current_admin.id
    db.commit()
    db.refresh(user)
    
    # ============================================
    # ✅ NOTIFICATION AU USER
    # ============================================
    notification = Notification(
        user_id=user.id,
        title="🎉 Compte approuvé",
        message=(
            f"Félicitations ! Votre compte {user.role.value} a été approuvé. "
            f"Vous pouvez maintenant accéder à toutes les fonctionnalités."
        ),
        type="account_approved",
        data=json.dumps({
            "user_id": user.id,
            "role": user.role.value,
            "validated_by": current_admin.id,
            "validated_at": str(user.validated_at)
        }),
        is_read=False
    )
    db.add(notification)
    db.commit()
    
    return user


@router.put("/users/{user_id}/reject", response_model=UserResponse)
def reject_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """Rejeter un utilisateur"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    if user.status != UserStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"L'utilisateur a déjà le statut: {user.status.value}"
        )
    
    user.status = UserStatus.REJECTED
    user.validated_at = datetime.now()
    user.validated_by = current_admin.id
    db.commit()
    db.refresh(user)
    
    # ============================================
    # ✅ NOTIFICATION AU USER
    # ============================================
    notification = Notification(
        user_id=user.id,
        title="❌ Compte rejeté",
        message=(
            f"Votre demande de compte {user.role.value} a été rejetée. "
            f"Veuillez contacter l'administration pour plus d'informations."
        ),
        type="account_rejected",
        data=json.dumps({
            "user_id": user.id,
            "role": user.role.value,
            "validated_by": current_admin.id
        }),
        is_read=False
    )
    db.add(notification)
    db.commit()
    
    return user


@router.put("/users/{user_id}/suspend", response_model=UserResponse)
def suspend_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """Suspendre un utilisateur"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Impossible de suspendre un administrateur")
    
    user.status = UserStatus.SUSPENDED
    db.commit()
    db.refresh(user)
    
    # ============================================
    # ✅ NOTIFICATION AU USER
    # ============================================
    notification = Notification(
        user_id=user.id,
        title="⛔ Compte suspendu",
        message=(
            "Votre compte a été suspendu. Veuillez contacter l'administration."
        ),
        type="account_suspended",
        data=json.dumps({
            "user_id": user.id,
            "role": user.role.value
        }),
        is_read=False
    )
    db.add(notification)
    db.commit()
    
    return user

@router.put("/users/{user_id}/activate", response_model=UserResponse)
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """Réactiver un utilisateur suspendu"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    if user.status != UserStatus.SUSPENDED:
        raise HTTPException(
            status_code=400,
            detail=f"L'utilisateur n'est pas suspendu: {user.status.value}"
        )
    
    user.status = UserStatus.APPROVED
    db.commit()
    db.refresh(user)
    return user

# ============================================
# STATISTIQUES
# ============================================

@router.get("/stats", response_model=dict)
def get_admin_stats(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """Statistiques globales"""
    return {
        "total_users": db.query(User).count(),
        "pending_users": db.query(User).filter(User.status == UserStatus.PENDING).count(),
        "approved_users": db.query(User).filter(User.status == UserStatus.APPROVED).count(),
        "rejected_users": db.query(User).filter(User.status == UserStatus.REJECTED).count(),
        "suspended_users": db.query(User).filter(User.status == UserStatus.SUSPENDED).count(),
        "by_role": {
            "patients": db.query(User).filter(User.role == UserRole.PATIENT).count(),
            "docteurs": db.query(User).filter(User.role == UserRole.DOCTEUR).count(),
            "pharmacies": db.query(User).filter(User.role == UserRole.PHARMACIE).count(),
            "hopitaux": db.query(User).filter(User.role == UserRole.HOPITAL).count(),
            "chauffeurs": db.query(User).filter(User.role == UserRole.CHAUFFEUR).count(),
            "admins": db.query(User).filter(User.role == UserRole.ADMIN).count(),
        }
    }

# ============================================
# PROFIL ADMIN
# ============================================

@router.get("/me", response_model=AdministrateurResponse)
def get_my_admin_profile(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Obtenir le profil de l'administrateur connecté"""
    admin = db.query(Administrateur).filter(Administrateur.user_id == current_user.id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil administrateur non trouvé"
        )
    return admin

@router.put("/me", response_model=AdministrateurResponse)
def update_my_admin_profile(
    admin_update: AdministrateurUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Mettre à jour le profil de l'administrateur connecté"""
    admin = db.query(Administrateur).filter(Administrateur.user_id == current_user.id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil administrateur non trouvé"
        )
    
    if admin_update.poste is not None:
        admin.poste = admin_update.poste
    if admin_update.notes is not None:
        admin.notes = admin_update.notes
    
    db.commit()
    db.refresh(admin)
    return admin