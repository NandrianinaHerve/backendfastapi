from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
import enum

class NotificationType(str, enum.Enum):
    """Types de notifications"""
    APPOINTMENT_CREATED = "appointment_created"
    APPOINTMENT_CONFIRMED = "appointment_confirmed"
    APPOINTMENT_REJECTED = "appointment_rejected"
    APPOINTMENT_CANCELLED = "appointment_cancelled"
    APPOINTMENT_REMINDER = "appointment_reminder"
    
    TRANSPORT_REQUEST = "transport_request"
    TRANSPORT_ACCEPTED = "transport_accepted"
    TRANSPORT_ARRIVED = "transport_arrived"
    TRANSPORT_COMPLETED = "transport_completed"
    
    ACCOUNT_APPROVED = "account_approved"
    ACCOUNT_REJECTED = "account_rejected"
    ACCOUNT_SUSPENDED = "account_suspended"
    
    PHARMACIE_GARDE = "pharmacie_garde"
    IA_RECOMMENDATION = "ia_recommendation"
    
    NEW_MESSAGE = "new_message"
    SYSTEM = "system"


class NotificationBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    type: str = Field(..., description="Type de notification")
    data: Optional[str] = Field(None, description="Données JSON additionnelles")


class NotificationCreate(NotificationBase):
    user_id: int


class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None
    read_at: Optional[datetime] = None


class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class NotificationMarkRead(BaseModel):
    """Marquer plusieurs notifications comme lues"""
    notification_ids: List[int]


class NotificationStats(BaseModel):
    """Statistiques des notifications"""
    total: int
    unread: int
    read: int
    by_type: dict