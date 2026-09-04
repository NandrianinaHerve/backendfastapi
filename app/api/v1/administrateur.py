# app/api/v1/administrateur.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ...core.database import get_db
from ...core.dependencies import require_admin
from ...core.security import get_password_hash
from ...models.user import User, UserStatus, UserRole
from ...models.administrateur import Administrateur
from ...schemas.administrateur import AdministrateurCreate, AdministrateurResponse, AdministrateurUpdate
from ...schemas.user import UserResponse

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

@router.get("/users", response_model=List[UserResponse])
def get_all_users(
    status: Optional[UserStatus] = None,
    role: Optional[UserRole] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Liste de tous les utilisateurs avec filtres"""
    query = db.query(User)
    if status:
        query = query.filter(User.status == status)
    if role:
        query = query.filter(User.role == role)
    return query.offset(offset).limit(limit).all()

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
    user.validated_at = datetime.utcnow()
    user.validated_by = current_admin.id
    db.commit()
    db.refresh(user)
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
    user.validated_at = datetime.utcnow()
    user.validated_by = current_admin.id
    db.commit()
    db.refresh(user)
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