"""
Service IA pour l'analyse d'ordonnances
Recherche les médicaments dans les pharmacies
"""

import json
import re
import unicodedata
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from ..models.ordonnance import Ordonnance, OrdonnanceMedicament
from ..models.pharmacie import Pharmacie
from ..models.medicament import Medicament
from ..models.user import User, UserStatus


class OrdonnanceIAService:
    """Service IA pour l'analyse d'ordonnances"""
    
    @staticmethod
    def normalize_medicament_name(name: str) -> str:
        """
        Normaliser le nom d'un médicament
        
        ✅ Gère :
        - Accents : Paracétamol → paracetamol
        - Casse : PARACETAMOL → paracetamol
        - Dosages : Paracétamol 500mg → paracetamol
        """
        if not name:
            return ""
        
        # Remplacer les caractères mal encodés courants
        replacements = {
            'Ú': 'e', 'É': 'e', 'È': 'e', 'Ê': 'e', 'Ë': 'e',
            'À': 'a', 'Â': 'a', 'Ä': 'a',
            'Î': 'i', 'Ï': 'i',
            'Ô': 'o', 'Ö': 'o',
            'Ù': 'u', 'Û': 'u', 'Ü': 'u',
            'Ç': 'c',
        }
        for old, new in replacements.items():
            name = name.replace(old, new)
        
        # Enlever les accents
        name = unicodedata.normalize('NFKD', name)
        name = name.encode('ASCII', 'ignore').decode('ASCII')
        
        # Mettre en minuscules
        name = name.lower().strip()
        
        # Enlever les dosages
        name = re.sub(r'\d+\s*(mg|g|ml|ui|mcg)', '', name)
        
        # Enlever les caractères spéciaux
        name = re.sub(r'[^\w\s]', ' ', name)
        name = re.sub(r'\s+', ' ', name)
        
        return name.strip()
    
    @staticmethod
    def extract_medicament_names(ordonnance) -> List[Dict]:
        """
        Extraire les noms des médicaments d'une ordonnance
        
        Adapté à votre modèle :
        - nom (pas nom_medicament)
        - dosage
        - posologie (pas frequence)
        - duree
        - quantite
        - instructions
        """
        medicaments = []
        for med in ordonnance.medicaments:
            nom = med.nom
            
            medicaments.append({
                "id": med.id,
                "nom": nom,
                "nom_normalise": OrdonnanceIAService.normalize_medicament_name(nom),
                "dosage": med.dosage,
                "posologie": med.posologie,
                "duree": med.duree,
                "quantite": med.quantite,
                "instructions": med.instructions
            })
        return medicaments
    
    @staticmethod
    def search_medicament_in_pharmacies(
        db: Session,
        nom_medicament: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: float = 10.0,
        limit: int = 20
    ) -> List[Dict]:
        """
        Chercher un médicament dans toutes les pharmacies
        avec recherche floue et normalisation
        """
        from geoalchemy2.functions import ST_Distance, ST_Transform, ST_SetSRID, ST_MakePoint
        
        if not nom_medicament:
            return []
        
        nom_norm = OrdonnanceIAService.normalize_medicament_name(nom_medicament)
        
        # ✅ Plusieurs patterns de recherche
        patterns = [
            f"%{nom_medicament}%",
            f"%{nom_norm}%",
        ]
        
        # Recherche par les 4 premiers caractères
        if len(nom_norm) >= 4:
            patterns.append(f"%{nom_norm[:4]}%")
        
        # Recherche par les 3 premiers caractères
        if len(nom_norm) >= 3:
            patterns.append(f"%{nom_norm[:3]}%")
        
        conditions = [Medicament.nom.ilike(p) for p in patterns]
        
        # Recherche dans la table "medicaments"
        query = db.query(Medicament).join(Pharmacie).join(User).filter(
            User.status == UserStatus.APPROVED,
            Medicament.is_disponible == True,
            Medicament.quantite_stock > 0,
            or_(*conditions)
        )
        
        # Filtrer par proximité
        if latitude and longitude:
            user_point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
            query = query.filter(
                Pharmacie.localisation.is_not(None),
                ST_Distance(
                    ST_Transform(Pharmacie.localisation, 3857),
                    ST_Transform(user_point, 3857)
                ) <= radius_km * 1000
            )
        
        medicaments = query.limit(limit).all()
        
        # Grouper par pharmacie
        pharmacies_dict = {}
        for med in medicaments:
            pharmacie = db.query(Pharmacie).filter(Pharmacie.id == med.pharmacie_id).first()
            if not pharmacie:
                continue
            
            # Calculer distance
            distance = None
            if latitude and longitude and pharmacie.localisation:
                user_point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
                dist_val = db.query(
                    ST_Distance(
                        ST_Transform(pharmacie.localisation, 3857),
                        ST_Transform(user_point, 3857)
                    ) / 1000
                ).scalar()
                distance = round(dist_val, 2) if dist_val else None
            
            # Extraire coordonnées
            pharmacie_lat, pharmacie_lon = None, None
            if pharmacie.localisation:
                point_text = db.execute(func.ST_AsText(pharmacie.localisation)).scalar()
                if point_text:
                    coords = point_text.replace("POINT(", "").replace(")", "").split()
                    pharmacie_lon = float(coords[0])
                    pharmacie_lat = float(coords[1])
            
            pharmacie_id = pharmacie.id
            if pharmacie_id not in pharmacies_dict:
                pharmacies_dict[pharmacie_id] = {
                    "pharmacie_id": pharmacie.id,
                    "pharmacie_nom": pharmacie.nom,
                    "pharmacie_adresse": pharmacie.adresse,
                    "pharmacie_telephone": pharmacie.telephone,
                    "pharmacie_latitude": pharmacie_lat,
                    "pharmacie_longitude": pharmacie_lon,
                    "is_open": pharmacie.is_open,
                    "distance_km": distance,
                    "medicaments_trouves": []
                }
            
            pharmacies_dict[pharmacie_id]["medicaments_trouves"].append({
                "medicament_id": med.id,
                "nom": med.nom,
                "dosage": med.dosage,
                "prix_unitaire": med.prix_unitaire,
                "quantite_stock": med.quantite_stock
            })
        
        result = list(pharmacies_dict.values())
        if latitude and longitude:
            result.sort(key=lambda x: x["distance_km"] if x["distance_km"] else 999999)
        
        return result
    
    @staticmethod
    def analyze_ordonnance(
        db: Session,
        ordonnance,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: float = 10.0
    ) -> Dict:
        """
        Analyser une ordonnance complète
        """
        medicaments = OrdonnanceIAService.extract_medicament_names(ordonnance)
        
        if not medicaments:
            return {
                "success": False,
                "message": "Aucun médicament dans l'ordonnance",
                "medicaments": [],
                "pharmacies_completes": [],
                "pharmacies_partielles": []
            }
        
        medicaments_result = []
        for med in medicaments:
            pharmacies = OrdonnanceIAService.search_medicament_in_pharmacies(
                db=db,
                nom_medicament=med["nom"],
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km
            )
            
            medicaments_result.append({
                "medicament": med,
                "pharmacies": pharmacies,
                "nb_pharmacies": len(pharmacies),
                "trouve": len(pharmacies) > 0
            })
        
        # Trouver les pharmacies qui ont TOUS les médicaments
        if medicaments_result:
            pharmacies_par_med = []
            for mr in medicaments_result:
                ids = set(p["pharmacie_id"] for p in mr["pharmacies"])
                pharmacies_par_med.append(ids)
            
            if pharmacies_par_med:
                communes = pharmacies_par_med[0]
                for ids in pharmacies_par_med[1:]:
                    communes = communes & ids
            else:
                communes = set()
            
            all_pharm_ids = set()
            for ids in pharmacies_par_med:
                all_pharm_ids |= ids

            pharmacies_agregees = {}
            for resultat_medicament in medicaments_result:
                for pharmacie in resultat_medicament["pharmacies"]:
                    pharmacie_id = pharmacie["pharmacie_id"]
                    if pharmacie_id not in pharmacies_agregees:
                        pharmacies_agregees[pharmacie_id] = {
                            **pharmacie,
                            "medicaments_trouves": [],
                            "nb_medicaments_disponibles": 0,
                            "nb_medicaments_total": len(medicaments),
                        }

                    pharmacie_agregee = pharmacies_agregees[pharmacie_id]
                    pharmacie_agregee["nb_medicaments_disponibles"] += 1
                    medicaments_deja_ajoutes = {
                        med["medicament_id"]
                        for med in pharmacie_agregee["medicaments_trouves"]
                    }
                    pharmacie_agregee["medicaments_trouves"].extend(
                        med
                        for med in pharmacie["medicaments_trouves"]
                        if med["medicament_id"] not in medicaments_deja_ajoutes
                    )

            pharmacies_completes = [
                pharmacie
                for pharmacie_id, pharmacie in pharmacies_agregees.items()
                if pharmacie_id in communes
            ]
            pharmacies_partielles = []
            for pharmacie_id in all_pharm_ids - communes:
                pharmacie = pharmacies_agregees.get(pharmacie_id)
                if pharmacie:
                    pharmacies_partielles.append(pharmacie)

            pharmacies_completes.sort(
                key=lambda pharmacie: pharmacie["distance_km"]
                if pharmacie["distance_km"] is not None
                else float("inf")
            )
            pharmacies_partielles.sort(
                key=lambda pharmacie: (
                    -pharmacie["nb_medicaments_disponibles"],
                    pharmacie["distance_km"]
                    if pharmacie["distance_km"] is not None
                    else float("inf"),
                )
            )
        else:
            pharmacies_completes = []
            pharmacies_partielles = []
        
        return {
            "success": True,
            "ordonnance_id": ordonnance.id,
            "nb_medicaments": len(medicaments),
            "medicaments": medicaments_result,
            "pharmacies_completes": pharmacies_completes,
            "pharmacies_partielles": pharmacies_partielles,
            "message": f"{len(pharmacies_completes)} pharmacie(s) peuvent fournir tous les médicaments"
        }


# Instance globale
ordonnance_ia_service = OrdonnanceIAService()