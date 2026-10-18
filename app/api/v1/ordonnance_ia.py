from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from datetime import datetime

from ...core.database import get_db
from ...core.dependencies import get_current_user, require_patient
from ...models.user import User
from ...models.patient import Patient
from ...models.ordonnance import Ordonnance, OrdonnanceMedicament
from ...models.pharmacie import Pharmacie
from ...models.medicament import Medicament, Commande, CommandeItem
from ...models.notification import Notification
from ...schemas.ordonnance_ia import (
    AnalyseOrdonnanceResponse,
    CommandeAutomatiqueRequest,
    CommandeAutomatiqueResponse
)
from ...services.ordonnance_ia_service import ordonnance_ia_service

router = APIRouter(prefix="/ia/ordonnance", tags=["IA Ordonnance"])


def create_notification(db, user_id, title, message, type, data=None):
    """Créer une notification"""
    try:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type,
            data=json.dumps(data) if data else None,
            is_read=False
        )
        db.add(notif)
        return notif
    except Exception as e:
        print(f"⚠️ Erreur notification: {e}")
        return None


# ============================================
# ANALYSER UNE ORDONNANCE
# ============================================
@router.post("/analyser/{ordonnance_id}", response_model=AnalyseOrdonnanceResponse)
def analyser_ordonnance(
    ordonnance_id: int,
    latitude: Optional[float] = Query(None, description="Latitude du patient"),
    longitude: Optional[float] = Query(None, description="Longitude du patient"),
    radius_km: float = Query(10.0, description="Rayon de recherche en km"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient)
):
    """
    🤖 Analyser une ordonnance et proposer des pharmacies
    
    - Cherche les médicaments dans toutes les pharmacies
    - Propose les pharmacies qui ont TOUS les médicaments
    - Propose aussi les pharmacies partielles
    """
    
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient non trouvé")
    
    # Vérifier que l'ordonnance appartient au patient
    ordonnance = db.query(Ordonnance).filter(
        Ordonnance.id == ordonnance_id,
        Ordonnance.patient_id == patient.id
    ).first()
    if not ordonnance:
        raise HTTPException(status_code=404, detail="Ordonnance non trouvée")
    
    # Analyser
    result = ordonnance_ia_service.analyze_ordonnance(
        db=db,
        ordonnance=ordonnance,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km
    )
    
    return result


# ============================================
# ANALYSER SANS ORDONNANCE (Recherche libre)
# ============================================
@router.post("/rechercher", response_model=AnalyseOrdonnanceResponse)
def rechercher_medicaments(
    medicaments: List[str],
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    radius_km: float = Query(10.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient)
):
    """
    🤖 Rechercher des médicaments dans les pharmacies (sans ordonnance)
    
    Body: liste de noms de médicaments
    """
    
    # Créer une ordonnance virtuelle
    class FakeOrdonnance:
        def __init__(self):
            self.id = 0
            self.medicaments = []
    
    fake = FakeOrdonnance()
    for i, nom in enumerate(medicaments):
        med = OrdonnanceMedicament()
        med.id = i + 1
        med.nom_medicament = nom
        med.dosage = None
        med.forme = None
        med.quantite = None
        med.duree = None
        fake.medicaments.append(med)
    
    result = ordonnance_ia_service.analyze_ordonnance(
        db=db,
        ordonnance=fake,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km
    )
    
    return result


# ============================================
# COMMANDE AUTOMATIQUE
# ============================================
@router.post("/commander", response_model=CommandeAutomatiqueResponse)
def commander_automatique(
    commande_data: CommandeAutomatiqueRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient)
):
    """
    🛒 Commander automatiquement tous les médicaments d'une ordonnance
    
    - Le patient choisit une pharmacie
    - Le système crée une commande automatique
    - La pharmacie reçoit une notification
    """
    
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient non trouvé")
    
    # Vérifier l'ordonnance
    ordonnance = db.query(Ordonnance).filter(
        Ordonnance.id == commande_data.ordonnance_id,
        Ordonnance.patient_id == patient.id
    ).first()
    if not ordonnance:
        raise HTTPException(status_code=404, detail="Ordonnance non trouvée")
    
    # Vérifier la pharmacie
    pharmacie = db.query(Pharmacie).filter(
        Pharmacie.id == commande_data.pharmacie_id
    ).first()
    if not pharmacie:
        raise HTTPException(status_code=404, detail="Pharmacie non trouvée")
    
    # Créer la commande
    commande = Commande(
        patient_id=patient.id,
        pharmacie_id=pharmacie.id,
        statut="en_attente",
        notes=commande_data.notes or f"Commande automatique depuis ordonnance {ordonnance.id}",
        montant_total=0.0
    )
    db.add(commande)
    db.flush()
    
    montant_total = 0.0
    medicaments_commandes = []
    medicaments_non_trouves = []
    
    # Pour chaque médicament de l'ordonnance
    for med in ordonnance.medicaments:
        # Chercher le médicament dans cette pharmacie
        medicament = db.query(Medicament).filter(
            Medicament.pharmacie_id == pharmacie.id,
            Medicament.nom.ilike(f"%{med.nom}%"),
            Medicament.is_disponible == True,
            Medicament.quantite_stock >= (med.quantite or 1),
        ).first()

        if medicament and medicament.quantite_stock > 0:
            quantite = med.quantite or 1
            
            sous_total = medicament.prix_unitaire * quantite
            montant_total += sous_total
            
            # Créer l'item de commande
            commande_item = CommandeItem(
                commande_id=commande.id,
                medicament_id=medicament.id,
                quantite=quantite,
                prix_unitaire=medicament.prix_unitaire,
                sous_total=sous_total
            )
            db.add(commande_item)
            
            medicaments_commandes.append({
                "medicament_id": medicament.id,
                "nom": medicament.nom,
                "dosage": medicament.dosage,
                "quantite": quantite,
                "prix": medicament.prix_unitaire,
                "sous_total": sous_total
            })
        else:
            medicaments_non_trouves.append({
                "nom": med.nom,
                "dosage": med.dosage,
                "raison": "Non disponible dans cette pharmacie"
            })
    
    # Mettre à jour le montant
    commande.montant_total = montant_total
    
    # Notification à la pharmacie
    create_notification(
        db=db,
        user_id=pharmacie.user_id,
        title="🛒 Nouvelle commande automatique",
        message=(
            f"{patient.user.prenom} {patient.user.nom} a passé une commande "
            f"automatique de {len(medicaments_commandes)} médicament(s) "
            f"depuis une ordonnance. Montant: {montant_total:.0f} Ar"
        ),
        type="commande_automatique",
        data={
            "commande_id": commande.id,
            "ordonnance_id": ordonnance.id,
            "patient_name": f"{patient.user.prenom} {patient.user.nom}",
            "montant_total": montant_total,
            "medicaments": medicaments_commandes
        }
    )
    
    # Notification au patient
    create_notification(
        db=db,
        user_id=patient.user_id,
        title="🛒 Commande automatique créée",
        message=(
            f"Votre commande a été créée à {pharmacie.nom}. "
            f"Montant: {montant_total:.0f} Ar. "
            f"{len(medicaments_commandes)} médicament(s), "
            f"{len(medicaments_non_trouves)} non trouvé(s)."
        ),
        type="commande_auto_patient",
        data={
            "commande_id": commande.id,
            "pharmacie_nom": pharmacie.nom,
            "montant_total": montant_total
        }
    )
    
    db.commit()
    db.refresh(commande)
    
    return {
        "success": True,
        "commande_id": commande.id,
        "pharmacie_id": pharmacie.id,
        "pharmacie_nom": pharmacie.nom,
        "montant_total": montant_total,
        "nb_medicaments": len(medicaments_commandes),
        "medicaments_commandes": medicaments_commandes,
        "medicaments_non_trouves": medicaments_non_trouves,
        "message": f"Commande créée avec {len(medicaments_commandes)} médicament(s)"
    }


# ============================================
# PROPOSER UNE PHARMACIE OPTIMALE
# ============================================
@router.get("/proposer/{ordonnance_id}")
def proposer_pharmacie_optimale(
    ordonnance_id: int,
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient)
):
    """
    🎯 Proposer LA meilleure pharmacie pour une ordonnance
    
    Critères:
    - A tous les médicaments
    - Plus proche
    - Ouverte
    """
    
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient non trouvé")
    
    ordonnance = db.query(Ordonnance).filter(
        Ordonnance.id == ordonnance_id,
        Ordonnance.patient_id == patient.id
    ).first()
    if not ordonnance:
        raise HTTPException(status_code=404, detail="Ordonnance non trouvée")
    
    # Analyser
    result = ordonnance_ia_service.analyze_ordonnance(
        db=db,
        ordonnance=ordonnance,
        latitude=latitude,
        longitude=longitude
    )
    
    if not result["success"]:
        return {
            "success": False,
            "message": "Aucune pharmacie trouvée"
        }
    
    # Choisir la meilleure pharmacie
    pharmacies_completes = result.get("pharmacies_completes", [])
    pharmacies_partielles = result.get("pharmacies_partielles", [])
    
    if pharmacies_completes:
        # Prendre la plus proche
        meilleure = pharmacies_completes[0]
        return {
            "success": True,
            "type": "complete",
            "pharmacie": meilleure,
            "message": (
                f"✅ {meilleure['pharmacie_nom']} peut fournir tous les médicaments. "
                f"Distance: {meilleure.get('distance_km', 'N/A')} km"
            )
        }
    elif pharmacies_partielles:
        # Prendre la plus complète et proche
        meilleure = pharmacies_partielles[0]
        return {
            "success": True,
            "type": "partielle",
            "pharmacie": meilleure,
            "message": (
                f"⚠️ {meilleure['pharmacie_nom']} peut fournir "
                f"{meilleure.get('nb_medicaments_disponibles', 0)}/"
                f"{meilleure.get('nb_medicaments_total', 0)} médicaments. "
                f"Distance: {meilleure.get('distance_km', 'N/A')} km"
            )
        }
    else:
        return {
            "success": False,
            "message": "Aucune pharmacie ne peut fournir ces médicaments"
        }