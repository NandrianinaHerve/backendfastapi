import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Service d'envoi WhatsApp via liens wa.me (Alternative Rapide)"""
    
    @staticmethod
    def build_link(phone: str, message: str) -> str:
        """Construire un lien wa.me (sans envoyer)"""
        if not phone:
            return ''
        clean_phone = str(phone).replace(' ', '').replace('+', '').replace('-', '').replace('(', '').replace(')', '')
        return f"https://wa.me/{clean_phone}?text={httpx._utils.urlencode({'text': message})[5:]}"
    
    @staticmethod
    def get_whatsapp_url(phone: str, message: str) -> Optional[str]:
        """Générer l'URL WhatsApp (à inclure dans la notification)"""
        if not phone:
            return None
        clean_phone = (
            str(phone)
            .replace(' ', '')
            .replace('+', '')
            .replace('-', '')
            .replace('(', '')
            .replace(')', '')
        )
        from urllib.parse import quote
        encoded_message = quote(message)
        return f"https://wa.me/{clean_phone}?text={encoded_message}"
    
    @staticmethod
    def send_message(phone: str, message: str) -> bool:
        """
        Pour l'Alternative Rapide : cette fonction ne peut PAS envoyer automatiquement.
        Elle génère juste le lien.
        """
        url = WhatsAppService.get_whatsapp_url(phone, message)
        if url:
            logger.info(f"📱 Lien WhatsApp généré : {url}")
            return True
        return False


whatsapp_service = WhatsAppService()