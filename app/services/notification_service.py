from sqlalchemy.orm import Session
from datetime import datetime
import json
from ..models.notification import Notification
from ..models.user import User

class NotificationService:
    """Service pour créer des notifications automatiques"""
    
    @staticmethod
    def create_appointment_notification(
        db: Session,
        doctor_user_id: int,
        patient_name: str,
        appointment_date: datetime,
        appointment_id: int
    ):
        """Notification pour un nouveau rendez-vous"""
        notification = Notification(
            user_id=doctor_user_id,
            title="📅 Nouveau rendez-vous",
            message=f"Nouveau rendez-vous de {patient_name} le {appointment_date.strftime('%d/%m/%Y à %H:%M')}",
            type="appointment_created",
            data=json.dumps({
                "appointment_id": appointment_id,
                "patient_name": patient_name,
                "date": str(appointment_date)
            }),
            is_read=False
        )
        db.add(notification)
        db.commit()
        return notification
    
    @staticmethod
    def create_appointment_confirmed_notification(
        db: Session,
        patient_user_id: int,
        doctor_name: str,
        appointment_date: datetime,
        appointment_id: int
    ):
        """Notification quand un docteur confirme"""
        notification = Notification(
            user_id=patient_user_id,
            title="✅ Rendez-vous confirmé",
            message=f"Votre rendez-vous avec Dr. {doctor_name} est confirmé pour le {appointment_date.strftime('%d/%m/%Y à %H:%M')}",
            type="appointment_confirmed",
            data=json.dumps({
                "appointment_id": appointment_id,
                "doctor_name": doctor_name
            }),
            is_read=False
        )
        db.add(notification)
        db.commit()
        return notification
    
    @staticmethod
    def create_transport_request_notification(
        db: Session,
        chauffeur_user_id: int,
        patient_name: str,
        destination: str,
        demande_id: int
    ):
        """Notification pour une demande de transport"""
        notification = Notification(
            user_id=chauffeur_user_id,
            title="🚗 Nouvelle demande de transport",
            message=f"Demande de transport de {patient_name} vers {destination}",
            type="transport_request",
            data=json.dumps({
                "demande_id": demande_id,
                "patient_name": patient_name,
                "destination": destination
            }),
            is_read=False
        )
        db.add(notification)
        db.commit()
        return notification
    
    @staticmethod
    def create_account_approved_notification(
        db: Session,
        user_id: int,
        user_role: str
    ):
        """Notification quand un compte est approuvé"""
        notification = Notification(
            user_id=user_id,
            title="🎉 Compte approuvé",
            message=f"Votre compte {user_role} a été approuvé. Vous pouvez maintenant vous connecter.",
            type="account_approved",
            data=json.dumps({"role": user_role}),
            is_read=False
        )
        db.add(notification)
        db.commit()
        return notification
    
    @staticmethod
    def create_pharmacie_garde_notification(
        db: Session,
        patient_user_id: int,
        pharmacie_name: str,
        date_debut: datetime,
        date_fin: datetime
    ):
        """Notification pour une pharmacie de garde"""
        notification = Notification(
            user_id=patient_user_id,
            title="💊 Pharmacie de garde",
            message=f"{pharmacie_name} est de garde du {date_debut.strftime('%d/%m')} au {date_fin.strftime('%d/%m')}",
            type="pharmacie_garde",
            data=json.dumps({
                "pharmacie_name": pharmacie_name,
                "date_debut": str(date_debut),
                "date_fin": str(date_fin)
            }),
            is_read=False
        )
        db.add(notification)
        db.commit()
        return notification


notification_service = NotificationService()