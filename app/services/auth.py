from sqlalchemy.orm import Session
from datetime import datetime
from ..models.user import User, UserStatus, UserRole
from ..core.security import verify_password, get_password_hash

def authenticate_user(db: Session, email: str, password: str) -> User:
    """Authentifier un utilisateur par email et mot de passe"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user

def create_user(db: Session, user_data) -> User:
    """Créer un utilisateur avec le rôle approprié"""
    user = User(
        nom=user_data.nom,
        prenom=user_data.prenom,
        email=user_data.email,
        telephone=user_data.telephone,
        password=get_password_hash(user_data.password),
        role=user_data.role,
        status=UserStatus.PENDING if user_data.role != UserRole.PATIENT else UserStatus.APPROVED
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_user_status(db: Session, user_id: int, status: UserStatus, admin_id: int) -> User:
    """Mettre à jour le statut d'un utilisateur (validation admin)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    
    user.status = status
    user.validated_at = datetime.now()
    user.validated_by = admin_id
    
    db.commit()
    db.refresh(user)
    return user