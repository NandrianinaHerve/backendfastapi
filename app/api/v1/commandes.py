from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
import json

from ...core.database import get_db
from ...core.dependencies import get_current_user, require_patient, require_pharmacie
from ...models.user import User, UserStatus
from ...models.patient import Patient
from ...models.pharmacie import Pharmacie
from ...models.medicament import Medicament, Commande, CommandeItem
from ...models.notification import Notification
from ...schemas.medicament import (
    CommandeCreate,
    CommandeUpdate,
    CommandeResponse,
    CommandeItemResponse,
    StatutCommande
)

router = APIRouter(prefix="/commandes", tags=["Commandes"])


# ============================================
# CRÉER UNE COMMANDE (Patient)
# ============================================
@router.post("/", response_model=CommandeResponse)
def create_commande(
    commande_data: CommandeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient)
):
    """Créer une commande de médicaments (Patient)"""
    
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient non trouvé")
    
    pharmacie = db.query(Pharmacie).filter(
        Pharmacie.id == commande_data.pharmacie_id
    ).first()
    if not pharmacie:
        raise HTTPException(status_code=404, detail="Pharmacie non trouvée")
    
    # Créer la commande
    commande = Commande(
        patient_id=patient.id,
        pharmacie_id=commande_data.pharmacie_id,
        notes=commande_data.notes,
        statut="en_attente",
        montant_total=0.0
    )
    db.add(commande)
    db.flush()
    
    montant_total = 0.0
    items_data = []
    
    # Ajouter les items
    for item in commande_data.items:
        medicament = db.query(Medicament).filter(
            Medicament.id == item.medicament_id,
            Medicament.pharmacie_id == commande_data.pharmacie_id
        ).first()
        
        if not medicament:
            raise HTTPException(
                status_code=404,
                detail=f"Médicament ID {item.medicament_id} non trouvé dans cette pharmacie"
            )
        
        if medicament.quantite_stock < item.quantite:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuffisant pour '{medicament.nom}'. Disponible: {medicament.quantite_stock}"
            )
        
        sous_total = medicament.prix_unitaire * item.quantite
        montant_total += sous_total
        
        commande_item = CommandeItem(
            commande_id=commande.id,
            medicament_id=medicament.id,
            quantite=item.quantite,
            prix_unitaire=medicament.prix_unitaire,
            sous_total=sous_total
        )
        db.add(commande_item)
        
        items_data.append({
            "medicament_id": medicament.id,
            "nom": medicament.nom,
            "quantite": item.quantite,
            "prix": medicament.prix_unitaire,
            "sous_total": sous_total
        })
    
    commande.montant_total = montant_total
    
    # Notifications
    # 1. Notification à la PHARMACIE
    notification_pharmacie = Notification(
        user_id=pharmacie.user_id,
        title="💊 Nouvelle commande",
        message=(
            f"{patient.user.prenom} {patient.user.nom} a passé une commande "
            f"de {len(items_data)} article(s) pour un montant de {montant_total:.0f} Ar."
        ),
        type="nouvelle_commande",
        data=json.dumps({
            "commande_id": commande.id,
            "patient_name": f"{patient.user.prenom} {patient.user.nom}",
            "patient_phone": patient.user.telephone,
            "items_count": len(items_data),
            "montant_total": montant_total,
            "items": items_data
        }),
        is_read=False
    )
    db.add(notification_pharmacie)
    
    # 2. Notification au PATIENT (confirmation)
    notification_patient = Notification(
        user_id=patient.user_id,
        title="📦 Commande envoyée",
        message=(
            f"Votre commande chez {pharmacie.nom} a été envoyée. "
            f"Montant: {montant_total:.0f} Ar. En attente de confirmation."
        ),
        type="commande_envoyee",
        data=json.dumps({
            "commande_id": commande.id,
            "pharmacie_nom": pharmacie.nom,
            "montant_total": montant_total
        }),
        is_read=False
    )
    db.add(notification_patient)
    
    db.commit()
    db.refresh(commande)
    
    return commande


# ============================================
# LISTE DES COMMANDES
# ============================================
@router.get("/", response_model=List[CommandeResponse])
def get_my_commandes(
    statut: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Voir ses commandes"""
    
    query = db.query(Commande)
    
    if current_user.role.value == "patient":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if patient:
            query = query.filter(Commande.patient_id == patient.id)
    elif current_user.role.value == "pharmacie":
        pharmacie = db.query(Pharmacie).filter(Pharmacie.user_id == current_user.id).first()
        if pharmacie:
            query = query.filter(Commande.pharmacie_id == pharmacie.id)
    elif current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    if statut:
        query = query.filter(Commande.statut == statut)
    
    commandes = query.order_by(Commande.date_commande.desc()).offset(offset).limit(limit).all()
    return commandes


@router.get("/{commande_id}", response_model=CommandeResponse)
def get_commande(
    commande_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Voir une commande spécifique"""
    commande = db.query(Commande).filter(Commande.id == commande_id).first()
    if not commande:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    return commande


# ============================================
# PHARMACIE : CONFIRMER / REFUSER
# ============================================
@router.put("/{commande_id}/confirmer", response_model=CommandeResponse)
def confirmer_commande(
    commande_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_pharmacie)
):
    """Confirmer une commande (Pharmacie)"""
    
    pharmacie = db.query(Pharmacie).filter(
        Pharmacie.user_id == current_user.id
    ).first()
    if not pharmacie:
        raise HTTPException(status_code=404, detail="Pharmacie non trouvée")
    
    commande = db.query(Commande).filter(
        Commande.id == commande_id,
        Commande.pharmacie_id == pharmacie.id,
        Commande.statut == "en_attente"
    ).first()
    if not commande:
        raise HTTPException(status_code=404, detail="Commande non trouvée ou déjà traitée")
    
    # Décrémenter le stock
    for item in commande.items:
        medicament = db.query(Medicament).filter(Medicament.id == item.medicament_id).first()
        if medicament:
            if medicament.quantite_stock < item.quantite:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stock insuffisant pour {medicament.nom}"
                )
            medicament.quantite_stock -= item.quantite
            if medicament.quantite_stock == 0:
                medicament.is_disponible = False
    
    commande.statut = "confirmee"
    commande.date_confirmation = datetime.now()
    db.commit()
    db.refresh(commande)
    
    # Notification au patient
    patient = db.query(Patient).filter(Patient.id == commande.patient_id).first()
    notification = Notification(
        user_id=patient.user_id,
        title="✅ Commande confirmée",
        message=(
            f"Votre commande chez {pharmacie.nom} a été confirmée. "
            f"Vous pouvez venir la récupérer."
        ),
        type="commande_confirmee",
        data=json.dumps({
            "commande_id": commande.id,
            "pharmacie_nom": pharmacie.nom,
            "pharmacie_adresse": pharmacie.adresse,
            "pharmacie_telephone": pharmacie.telephone,
            "montant_total": commande.montant_total
        }),
        is_read=False
    )
    db.add(notification)
    db.commit()
    
    return commande


@router.put("/{commande_id}/refuser", response_model=CommandeResponse)
def refuser_commande(
    commande_id: int,
    motif: str = "Indisponible",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_pharmacie)
):
    """Refuser une commande (Pharmacie)"""
    
    pharmacie = db.query(Pharmacie).filter(
        Pharmacie.user_id == current_user.id
    ).first()
    if not pharmacie:
        raise HTTPException(status_code=404, detail="Pharmacie non trouvée")
    
    commande = db.query(Commande).filter(
        Commande.id == commande_id,
        Commande.pharmacie_id == pharmacie.id,
        Commande.statut == "en_attente"
    ).first()
    if not commande:
        raise HTTPException(status_code=404, detail="Commande non trouvée ou déjà traitée")
    
    commande.statut = "refusee"
    commande.motif_annulation = motif
    commande.date_annulation = datetime.now()
    db.commit()
    db.refresh(commande)
    
    # Notification au patient
    patient = db.query(Patient).filter(Patient.id == commande.patient_id).first()
    notification = Notification(
        user_id=patient.user_id,
        title="❌ Commande refusée",
        message=(
            f"Votre commande chez {pharmacie.nom} a été refusée. "
            f"Motif: {motif}"
        ),
        type="commande_refusee",
        data=json.dumps({
            "commande_id": commande.id,
            "pharmacie_nom": pharmacie.nom,
            "motif": motif
        }),
        is_read=False
    )
    db.add(notification)
    db.commit()
    
    return commande


@router.put("/{commande_id}/prete", response_model=CommandeResponse)
def marquer_prete(
    commande_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_pharmacie)
):
    """Marquer la commande comme prête (Pharmacie)"""
    
    pharmacie = db.query(Pharmacie).filter(
        Pharmacie.user_id == current_user.id
    ).first()
    if not pharmacie:
        raise HTTPException(status_code=404, detail="Pharmacie non trouvée")
    
    commande = db.query(Commande).filter(
        Commande.id == commande_id,
        Commande.pharmacie_id == pharmacie.id,
        Commande.statut == "confirmee"
    ).first()
    if not commande:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    commande.statut = "prete"
    commande.date_prete = datetime.now()
    db.commit()
    db.refresh(commande)
    
    # Notification au patient
    patient = db.query(Patient).filter(Patient.id == commande.patient_id).first()
    notification = Notification(
        user_id=patient.user_id,
        title="🎉 Commande prête",
        message=(
            f"Votre commande chez {pharmacie.nom} est prête ! "
            f"Vous pouvez venir la récupérer."
        ),
        type="commande_prete",
        data=json.dumps({
            "commande_id": commande.id,
            "pharmacie_nom": pharmacie.nom,
            "pharmacie_adresse": pharmacie.adresse,
            "pharmacie_telephone": pharmacie.telephone
        }),
        is_read=False
    )
    db.add(notification)
    db.commit()
    
    return commande


# ============================================
# PATIENT : ANNULER
# ============================================
@router.put("/{commande_id}/annuler", response_model=CommandeResponse)
def annuler_commande(
    commande_id: int,
    motif: str = "Annulée par le patient",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient)
):
    """Annuler une commande (Patient)"""
    
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient non trouvé")
    
    commande = db.query(Commande).filter(
        Commande.id == commande_id,
        Commande.patient_id == patient.id,
        Commande.statut.in_(["en_attente", "confirmee"])
    ).first()
    if not commande:
        raise HTTPException(
            status_code=404, 
            detail="Commande non trouvée ou ne peut plus être annulée"
        )
    
    # Si confirmée, remettre le stock
    if commande.statut == "confirmee":
        for item in commande.items:
            medicament = db.query(Medicament).filter(Medicament.id == item.medicament_id).first()
            if medicament:
                medicament.quantite_stock += item.quantite
                medicament.is_disponible = True
    
    commande.statut = "annulee"
    commande.motif_annulation = motif
    commande.date_annulation = datetime.now()
    db.commit()
    db.refresh(commande)
    
    # Notification à la pharmacie
    pharmacie = db.query(Pharmacie).filter(Pharmacie.id == commande.pharmacie_id).first()
    notification = Notification(
        user_id=pharmacie.user_id,
        title="❌ Commande annulée",
        message=(
            f"{patient.user.prenom} {patient.user.nom} a annulé sa commande. "
            f"Motif: {motif}"
        ),
        type="commande_annulee",
        data=json.dumps({
            "commande_id": commande.id,
            "patient_name": f"{patient.user.prenom} {patient.user.nom}",
            "motif": motif
        }),
        is_read=False
    )
    db.add(notification)
    db.commit()
    
    return commande


@router.put("/{commande_id}/recuperer", response_model=CommandeResponse)
def marquer_recuperee(
    commande_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_pharmacie)
):
    """Marquer la commande comme récupérée (Pharmacie)"""
    
    pharmacie = db.query(Pharmacie).filter(
        Pharmacie.user_id == current_user.id
    ).first()
    if not pharmacie:
        raise HTTPException(status_code=404, detail="Pharmacie non trouvée")
    
    commande = db.query(Commande).filter(
        Commande.id == commande_id,
        Commande.pharmacie_id == pharmacie.id,
        Commande.statut == "prete"
    ).first()
    if not commande:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    commande.statut = "recuperee"
    commande.date_recuperation = datetime.now()
    db.commit()
    db.refresh(commande)
    
    # Notification au patient
    patient = db.query(Patient).filter(Patient.id == commande.patient_id).first()
    notification = Notification(
        user_id=patient.user_id,
        title="✅ Commande récupérée",
        message=f"Merci d'avoir utilisé Santé-Fianarantsoa !",
        type="commande_recuperee",
        data=json.dumps({"commande_id": commande.id}),
        is_read=False
    )
    db.add(notification)
    db.commit()
    
    return commande