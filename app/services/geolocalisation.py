from sqlalchemy.orm import Session
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint, ST_Distance, ST_Transform
from ..models.docteur import Docteur
from ..models.pharmacie import Pharmacie
from ..models.chauffeur import Chauffeur
from typing import List, Dict, Any

class GeolocationService:
    """Service de gestion de la géolocalisation"""
    
    @staticmethod
    def find_nearby_doctors(db: Session, latitude: float, longitude: float, radius: float = 10.0, specialite_id: int = None) -> List[Docteur]:
        """Trouver les docteurs proches"""
        user_point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        
        query = db.query(Docteur).filter(
            Docteur.localisation.is_not(None),
            ST_Distance(
                ST_Transform(Docteur.localisation, 3857),
                ST_Transform(user_point, 3857)
            ) <= radius * 1000
        )
        
        if specialite_id:
            query = query.filter(Docteur.specialite_id == specialite_id)
        
        return query.order_by(
            ST_Distance(
                ST_Transform(Docteur.localisation, 3857),
                ST_Transform(user_point, 3857)
            )
        ).all()
    
    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculer la distance entre deux points en km (formule de Haversine)"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Rayon de la Terre en km
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c