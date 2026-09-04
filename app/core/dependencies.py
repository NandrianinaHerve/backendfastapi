from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import List, Optional

from .config import settings
from .database import get_db
from ..models.user import User, UserRole, UserStatus

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login-form")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Utilisateur inactif"
        )
    return current_user

def require_role(*allowed_roles: UserRole):
    """Dépendance pour vérifier le rôle de l'utilisateur"""
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        # Vérifier le rôle
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès non autorisé. Rôle requis: {[r.value for r in allowed_roles]}"
            )
        
        # Vérifier le statut (pour les professionnels)
        if current_user.role != UserRole.PATIENT and current_user.role != UserRole.ADMIN:
            if current_user.status != UserStatus.APPROVED:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Compte en attente de validation par un administrateur"
                )
        
        return current_user
    
    return role_checker

# Dépendances prêtes à l'emploi
require_patient = require_role(UserRole.PATIENT)
require_docteur = require_role(UserRole.DOCTEUR)
require_pharmacie = require_role(UserRole.PHARMACIE)
require_hopital = require_role(UserRole.HOPITAL)
require_chauffeur = require_role(UserRole.CHAUFFEUR)
require_admin = require_role(UserRole.ADMIN)