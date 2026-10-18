from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta
import json

from ...core.database import get_db
from ...core.dependencies import get_current_user, require_admin
from ...models.user import User
from ...models.notification import Notification
from ...schemas.notification import (
    NotificationCreate,
    NotificationResponse,
    NotificationUpdate,
    NotificationMarkRead,
    NotificationStats,
    NotificationType
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ============================================
# CRÉATION DE NOTIFICATIONS
# ============================================

@router.post("/", response_model=NotificationResponse)
def create_notification(
    notification_data: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Créer une notification (Admin ou système)"""
    
    # Vérifier que l'utilisateur existe
    user = db.query(User).filter(User.id == notification_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    notification = Notification(
        user_id=notification_data.user_id,
        title=notification_data.title,
        message=notification_data.message,
        type=notification_data.type,
        data=notification_data.data,
        is_read=False
    )
    
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


# ============================================
# LECTURE DES NOTIFICATIONS
# ============================================

@router.get("/", response_model=List[NotificationResponse])
def get_my_notifications(
    is_read: Optional[bool] = None,
    type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtenir toutes les notifications de l'utilisateur connecté
    
    - **is_read**: Filtrer par statut de lecture
    - **type**: Filtrer par type de notification
    - **limit**: Nombre maximum de notifications
    - **offset**: Pagination
    """
    query = db.query(Notification).filter(
        Notification.user_id == current_user.id
    )
    
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
    
    if type:
        query = query.filter(Notification.type == type)
    
    notifications = query.order_by(
        desc(Notification.created_at)
    ).offset(offset).limit(limit).all()
    
    return notifications


@router.get("/unread", response_model=List[NotificationResponse])
def get_unread_notifications(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir uniquement les notifications non lues"""
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).order_by(
        desc(Notification.created_at)
    ).limit(limit).all()
    
    return notifications


@router.get("/count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir le nombre de notifications non lues"""
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    
    return {
        "unread_count": count,
        "user_id": current_user.id
    }


@router.get("/stats", response_model=NotificationStats)
def get_notification_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir les statistiques des notifications"""
    total = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).count()
    
    unread = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    
    read = total - unread
    
    # Stats par type
    type_counts = db.query(
        Notification.type,
        func.count(Notification.id).label('count')
    ).filter(
        Notification.user_id == current_user.id
    ).group_by(Notification.type).all()
    
    by_type = {t[0]: t[1] for t in type_counts}
    
    return {
        "total": total,
        "unread": unread,
        "read": read,
        "by_type": by_type
    }


@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir une notification spécifique"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification non trouvée"
        )
    
    # Vérifier que la notification appartient à l'utilisateur
    if notification.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )
    
    return notification


# ============================================
# MARQUER COMME LU
# ============================================

@router.put("/{notification_id}/read", response_model=NotificationResponse)
def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Marquer une notification comme lue"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification non trouvée"
        )
    
    notification.is_read = True
    notification.read_at = datetime.now()
    
    db.commit()
    db.refresh(notification)
    return notification


@router.put("/read-all")
def mark_all_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Marquer toutes les notifications comme lues"""
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({
        "is_read": True,
        "read_at": datetime.now()
    })
    
    db.commit()
    
    return {
        "message": f"{count} notification(s) marquée(s) comme lue(s)",
        "count": count
    }


@router.put("/read-multiple")
def mark_multiple_as_read(
    data: NotificationMarkRead,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Marquer plusieurs notifications comme lues"""
    count = db.query(Notification).filter(
        Notification.id.in_(data.notification_ids),
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({
        "is_read": True,
        "read_at": datetime.now()
    }, synchronize_session=False)
    
    db.commit()
    
    return {
        "message": f"{count} notification(s) marquée(s) comme lue(s)",
        "count": count
    }


# ============================================
# SUPPRESSION
# ============================================

@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Supprimer une notification"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification non trouvée"
        )
    
    db.delete(notification)
    db.commit()
    
    return {"message": "Notification supprimée avec succès"}


@router.delete("/")
def delete_all_notifications(
    only_read: bool = Query(True, description="Supprimer seulement les notifications lues"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Supprimer toutes les notifications (ou seulement les lues)"""
    query = db.query(Notification).filter(
        Notification.user_id == current_user.id
    )
    
    if only_read:
        query = query.filter(Notification.is_read == True)
    
    count = query.delete(synchronize_session=False)
    db.commit()
    
    return {
        "message": f"{count} notification(s) supprimée(s)",
        "count": count
    }


# ============================================
# NOTIFICATIONS ADMIN
# ============================================

@router.post("/send-to-user/{user_id}")
def send_notification_to_user(
    user_id: int,
    title: str,
    message: str,
    type: str = "system",
    data: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """Envoyer une notification à un utilisateur spécifique (Admin)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        data=data,
        is_read=False
    )
    
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    return {
        "message": "Notification envoyée",
        "notification_id": notification.id,
        "user_id": user_id
    }


@router.post("/broadcast")
def broadcast_notification(
    title: str,
    message: str,
    type: str = "system",
    role: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """Envoyer une notification à tous les utilisateurs (Admin)"""
    
    query = db.query(User)
    
    if role:
        from ...models.user import UserRole
        try:
            role_enum = UserRole(role.lower())
            query = query.filter(User.role == role_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Rôle invalide: {role}"
            )
    
    users = query.all()
    
    notifications = []
    for user in users:
        notification = Notification(
            user_id=user.id,
            title=title,
            message=message,
            type=type,
            is_read=False
        )
        notifications.append(notification)
    
    db.add_all(notifications)
    db.commit()
    
    return {
        "message": f"Notification envoyée à {len(notifications)} utilisateur(s)",
        "count": len(notifications)
    }