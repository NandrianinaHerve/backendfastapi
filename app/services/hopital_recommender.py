import math
import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape

from ..models.hopital import Hopital
from ..models.localisation import Localisation
from ..models.avis import StatistiqueAvis, TypeService

logger = logging.getLogger(__name__)


class HopitalRecommender:
    """Recommande des hôpitaux selon maladie, distance et avis"""

    NOTE_GLOBALE_MOYENNE = 3.5
    POIDS_MOYENNE_GLOBALE = 5

    MALADIE_TO_SERVICES = {
        # Urgences / réanimation
        "infarctus": ["Cardiologie", "Urgences", "Réanimation"],
        "avc": ["Neurologie", "Urgences", "Réanimation"],
        "méningite": ["Infectiologie", "Urgences", "Réanimation"],
        "hémorragie": ["Urgences", "Chirurgie", "Réanimation"],
        "traumatisme": ["Urgences", "Chirurgie", "Orthopédie"],
        "fracture": ["Orthopédie", "Urgences", "Chirurgie"],
        # Chirurgie
        "appendicite": ["Chirurgie", "Urgences"],
        "hernie": ["Chirurgie"],
        "calcul rénal": ["Urologie", "Chirurgie"],
        # Maternité
        "grossesse": ["Maternité", "Gynécologie", "Obstétrique"],
        "accouchement": ["Maternité", "Obstétrique"],
        # Pédiatrie
        "pédiatrique": ["Pédiatrie"],
        "enfant": ["Pédiatrie"],
        # Infectieux
        "paludisme": ["Infectiologie", "Médecine interne"],
        "tuberculose": ["Pneumologie", "Infectiologie"],
        "dengue": ["Infectiologie", "Médecine interne"],
        "typhoïde": ["Infectiologie"],
        # Cardio
        "insuffisance cardiaque": ["Cardiologie"],
        "hypertension": ["Cardiologie", "Médecine générale"],
        # Cancer
        "cancer": ["Oncologie"],
        "tumeur": ["Oncologie", "Chirurgie"],
        # Dialyse
        "insuffisance rénale": ["Néphrologie", "Dialyse"],
        # Psychiatrie
        "dépression": ["Psychiatrie"],
        "anxiété": ["Psychiatrie"],
        "schizophrénie": ["Psychiatrie"],
    }

    DEFAULT_SERVICES = ["Médecine générale", "Urgences"]

    @staticmethod
    def _haversine_distance(lat1, lon1, lat2, lon2) -> float:
        R = 6371.0
        lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c, 2)

    @classmethod
    def _get_bayesian_note(cls, note_moyenne: float, nb_avis: int) -> float:
        if nb_avis == 0:
            return cls.NOTE_GLOBALE_MOYENNE
        m = cls.POIDS_MOYENNE_GLOBALE
        return (nb_avis * note_moyenne + m * cls.NOTE_GLOBALE_MOYENNE) / (nb_avis + m)

    @classmethod
    def _get_stats_avis(cls, db: Session, hopital_id: int) -> Tuple[float, int]:
        stats = (
            db.query(StatistiqueAvis)
            .filter(
                StatistiqueAvis.type_service == TypeService.HOPITAL,
                StatistiqueAvis.service_id == hopital_id,
            )
            .first()
        )
        if not stats or stats.nb_avis == 0:
            return (0.0, 0)
        note = stats.note_moyenne / 10.0 if stats.note_moyenne else 0.0
        return (round(note, 2), stats.nb_avis)

    @classmethod
    def get_services_for_maladie(cls, maladie: str) -> List[str]:
        if not maladie:
            return cls.DEFAULT_SERVICES
        maladie_lower = maladie.lower().strip()

        if maladie_lower in cls.MALADIE_TO_SERVICES:
            return cls.MALADIE_TO_SERVICES[maladie_lower]

        for key, services in cls.MALADIE_TO_SERVICES.items():
            if key in maladie_lower or maladie_lower in key:
                return services

        mots_maladie = set(maladie_lower.split())
        for key, services in cls.MALADIE_TO_SERVICES.items():
            if mots_maladie & set(key.split()):
                return services

        return cls.DEFAULT_SERVICES

    # ============================================
    # LECTURE POSTGIS
    # ============================================
    @staticmethod
    def _extraire_coords_postgis(geometry) -> Tuple[Optional[float], Optional[float]]:
        """
        Convertit un objet PostGIS (WKBElement) en (latitude, longitude).
        """
        if geometry is None:
            return (None, None)
        try:
            point = to_shape(geometry)
            return (point.y, point.x)
        except Exception as e:
            logger.warning(f"⚠️ Impossible de lire la géométrie PostGIS: {e}")
            return (None, None)

    @classmethod
    def recommander(
        cls,
        db: Session,
        maladie: str,
        patient_lat: Optional[float] = None,
        patient_lon: Optional[float] = None,
        limit: int = 5,
        rayon_km: Optional[float] = 100.0,
        ponderation: str = "equilibre",
        urgence_seulement: bool = False,
    ) -> List[dict]:
        services_requis = cls.get_services_for_maladie(maladie)

        query = db.query(Hopital)
        if urgence_seulement:
            if hasattr(Hopital, "urgence_24h"):
                query = query.filter(Hopital.urgence_24h == True)
            elif hasattr(Hopital, "has_urgence"):
                query = query.filter(Hopital.has_urgence == True)

        hopitaux = query.all()

        resultats = []
        for hopital in hopitaux:
            note, nb_avis = cls._get_stats_avis(db, hopital.id)
            note_bayesienne = cls._get_bayesian_note(note, nb_avis)

            # ============================================
            # LOCALISATION : lecture directe de Hopital.localisation
            # ============================================
            distance = None
            latitude = longitude = None
            adresse = getattr(hopital, "adresse", None)

            # ✅ Lire la colonne PostGIS de l'hôpital directement
            latitude, longitude = cls._extraire_coords_postgis(
                getattr(hopital, "localisation", None)
            )

            # Fallback : si rien dans hopital, chercher dans Localisation
            if latitude is None or longitude is None:
                loc = (
                    db.query(Localisation)
                    .filter(Localisation.user_id == hopital.user_id)
                    .first()
                )
                if loc:
                    latitude = getattr(loc, "latitude", None)
                    longitude = getattr(loc, "longitude", None)
                    adresse = adresse or getattr(loc, "adresse", None)

            # Calcul de distance
            if (
                patient_lat is not None
                and patient_lon is not None
                and latitude is not None
                and longitude is not None
            ):
                distance = cls._haversine_distance(
                    patient_lat, patient_lon, latitude, longitude
                )
                if rayon_km and distance > rayon_km:
                    continue

            services_hopital = getattr(hopital, "services", None) or []
            if isinstance(services_hopital, str):
                services_hopital = [s.strip() for s in services_hopital.split(",")]

            score_services = 0
            if services_hopital:
                for service_requis in services_requis:
                    for service_hop in services_hopital:
                        if service_requis.lower() in service_hop.lower():
                            score_services += 1
                            break

            resultats.append({
                "id": hopital.id,
                "nom": hopital.nom,
                "type_etablissement": getattr(hopital, "type_etablissement", None),
                "adresse": adresse,
                "ville": getattr(hopital, "ville", None),
                "telephone": getattr(hopital, "telephone", None),
                "email": getattr(hopital.user, "email", None) if hopital.user else None,
                "latitude": latitude,
                "longitude": longitude,
                "distance_km": distance,
                "urgence_24h": bool(getattr(hopital, "urgence_24h", False)),
                "nb_lits_disponibles": getattr(hopital, "nb_lits_disponibles", None),
                "services": services_hopital,
                "note_moyenne": note,
                "nb_avis": nb_avis,
                "note_bayesienne": round(note_bayesienne, 2),
                "_distance": distance if distance is not None else 999999,
                "_note": note_bayesienne,
                "_services_score": score_services,
                "_urgence": 1 if getattr(hopital, "urgence_24h", False) else 0,
            })

        # Tri
        if ponderation == "distance":
            resultats.sort(key=lambda h: (h["_distance"], -h["_note"]))
        elif ponderation == "note":
            resultats.sort(key=lambda h: (-h["_note"], h["_distance"]))
        else:
            for h in resultats:
                score_note = h["_note"] / 5.0
                score_dist = 1 - min(h["_distance"], 100) / 100
                score_services = min(h["_services_score"], 5) / 5.0
                h["_score_composite"] = (
                    0.4 * score_note
                    + 0.3 * score_dist
                    + 0.2 * score_services
                    + 0.1 * h["_urgence"]
                )
            resultats.sort(key=lambda h: -h["_score_composite"])

        for h in resultats:
            for k in ["_distance", "_note", "_services_score", "_urgence", "_score_composite"]:
                h.pop(k, None)

        return resultats[:limit]