import math
import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from geoalchemy2.shape import to_shape

from ..models.docteur import Docteur
from ..models.specialite import Specialite
from ..models.localisation import Localisation
from ..models.avis import StatistiqueAvis, TypeService

logger = logging.getLogger(__name__)


class DocteurRecommender:
    """Recommande des docteurs selon spécialité, note, distance et expérience"""

    NOTE_GLOBALE_MOYENNE = 3.5
    POIDS_MOYENNE_GLOBALE = 5

    @staticmethod
    def _haversine_distance(lat1, lon1, lat2, lon2) -> float:
        """Distance en km entre deux points GPS"""
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
        """Score bayésien : (n × note + m × note_globale) / (n + m)"""
        if nb_avis == 0:
            return cls.NOTE_GLOBALE_MOYENNE
        m = cls.POIDS_MOYENNE_GLOBALE
        return (nb_avis * note_moyenne + m * cls.NOTE_GLOBALE_MOYENNE) / (nb_avis + m)

    @classmethod
    def _get_stats_avis(cls, db: Session, docteur_id: int) -> Tuple[float, int]:
        """Récupère (note_moyenne, nb_avis) pour un docteur"""
        stats = (
            db.query(StatistiqueAvis)
            .filter(
                StatistiqueAvis.type_service == TypeService.DOCTEUR,
                StatistiqueAvis.service_id == docteur_id,
            )
            .first()
        )
        if not stats or stats.nb_avis == 0:
            return (0.0, 0)
        note = stats.note_moyenne / 10.0 if stats.note_moyenne else 0.0
        return (round(note, 2), stats.nb_avis)

    # ============================================
    # LECTURE POSTGIS
    # ============================================
    @staticmethod
    def _extraire_coords_postgis(geometry) -> Tuple[Optional[float], Optional[float]]:
        """
        Convertit un objet PostGIS (WKBElement) en (latitude, longitude).
        Retourne (None, None) si la géométrie est absente ou illisible.
        """
        if geometry is None:
            return (None, None)
        try:
            point = to_shape(geometry)
            # ⚠️ Attention : longitude = X, latitude = Y
            return (point.y, point.x)
        except Exception as e:
            logger.warning(f"⚠️ Impossible de lire la géométrie PostGIS: {e}")
            return (None, None)

    @classmethod
    def recommander(
        cls,
        db: Session,
        specialites_noms: List[str],
        patient_lat: Optional[float] = None,
        patient_lon: Optional[float] = None,
        limit: int = 5,
        rayon_km: Optional[float] = 50.0,
        ponderation: str = "equilibre",
        prix_max: Optional[float] = None,
        experience_min: Optional[int] = None,
        note_min: Optional[float] = None,
    ) -> List[dict]:
        """
        Recommande des docteurs.
        ponderation: "equilibre" | "distance" | "note" | "prix"
        """
        if not specialites_noms:
            return []

        specialites_noms = [s.strip().lower() for s in specialites_noms]

        # 1. Trouver les spécialités
        specialites = (
            db.query(Specialite)
            .filter(
                or_(*[Specialite.nom.ilike(f"%{nom}%") for nom in specialites_noms])
            )
            .all()
        )
        if not specialites:
            return []

        priorite_map = {s.lower(): i for i, s in enumerate(specialites_noms)}

        # 2. Récupérer les docteurs disponibles
        docteurs = (
            db.query(Docteur)
            .filter(
                Docteur.specialite_id.in_([s.id for s in specialites]),
                Docteur.is_available == True,
            )
            .all()
        )

        resultats = []
        for docteur in docteurs:
            specialite_nom = (
                docteur.specialite.nom if docteur.specialite else "Inconnue"
            )

            # Note depuis les avis
            note, nb_avis = cls._get_stats_avis(db, docteur.id)

            if note_min is not None and note < note_min:
                continue

            note_bayesienne = cls._get_bayesian_note(note, nb_avis)

            # ============================================
            # LOCALISATION : lecture directe de Docteur.localisation
            # ============================================
            distance = None
            latitude = longitude = None
            adresse = getattr(docteur, "adresse", None)

            # ✅ Lire la colonne PostGIS du docteur directement
            latitude, longitude = cls._extraire_coords_postgis(
                getattr(docteur, "localisation", None)
            )

            # Fallback : si rien dans docteur, chercher dans Localisation
            if latitude is None or longitude is None:
                loc = (
                    db.query(Localisation)
                    .filter(Localisation.user_id == docteur.user_id)
                    .first()
                )
                if loc:
                    latitude = getattr(loc, "latitude", None)
                    longitude = getattr(loc, "longitude", None)
                    adresse = adresse or getattr(loc, "adresse", None)

            # Calcul de distance si on a les deux positions
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

            experience = getattr(docteur, "experience_years", 0) or 0
            prix = getattr(docteur, "consultation_price", 0) or 0

            if prix_max is not None and prix > prix_max:
                continue
            if experience_min is not None and experience < experience_min:
                continue

            resultats.append({
                "id": docteur.id,
                "nom": docteur.user.nom if docteur.user else "",
                "prenom": docteur.user.prenom if docteur.user else "",
                "specialite": specialite_nom,
                "specialite_id": docteur.specialite_id,
                "email": docteur.user.email if docteur.user else None,
                "telephone": getattr(docteur.user, "telephone", None) if docteur.user else None,
                "adresse": adresse,
                "latitude": latitude,
                "longitude": longitude,
                "distance_km": distance,
                "is_available": docteur.is_available,
                "consultation_price": prix,
                "experience_years": experience,
                "note_moyenne": note,
                "nb_avis": nb_avis,
                "note_bayesienne": round(note_bayesienne, 2),
                "photo_url": getattr(docteur, "photo_url", None),
                "_priorite": priorite_map.get(specialite_nom.lower(), 999),
                "_distance": distance if distance is not None else 999999,
                "_note": note_bayesienne,
                "_experience": experience,
                "_prix": prix,
            })

        # 3. Tri
        if ponderation == "distance":
            resultats.sort(key=lambda d: (d["_priorite"], d["_distance"], -d["_note"]))
        elif ponderation == "note":
            resultats.sort(key=lambda d: (d["_priorite"], -d["_note"], d["_distance"]))
        elif ponderation == "prix":
            resultats.sort(key=lambda d: (d["_priorite"], d["_prix"], -d["_note"]))
        else:  # equilibre
            for d in resultats:
                score_note = d["_note"] / 5.0
                score_dist = 1 - min(d["_distance"], 100) / 100
                score_exp = min(d["_experience"], 30) / 30
                d["_score_composite"] = (
                    0.4 * score_note + 0.3 * score_dist + 0.3 * score_exp
                )
            resultats.sort(key=lambda d: (d["_priorite"], -d["_score_composite"]))

        # 4. Nettoyage
        for r in resultats:
            for k in ["_priorite", "_distance", "_note", "_experience", "_prix", "_score_composite"]:
                r.pop(k, None)

        return resultats[:limit]