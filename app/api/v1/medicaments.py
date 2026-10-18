from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from datetime import datetime
import json

from ...core.database import get_db
from ...core.dependencies import get_current_user, require_pharmacie
from ...models.user import User, UserStatus
from ...models.pharmacie import Pharmacie
from ...models.medicament import Medicament
from ...models.notification import Notification
from ...schemas.medicament import (
    MedicamentCreate,
    MedicamentUpdate,
    MedicamentResponse,
    MedicamentWithPharmacie,
    StockUpdate
)

router = APIRouter(prefix="/medicaments", tags=["Médicaments"])


# ============================================
# PHARMACIE : GESTION DU STOCK
# ============================================

@router.post("/", response_model=MedicamentResponse)
def create_medicament(
    medicament_data: MedicamentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_pharmacie)
):
    """Ajouter un médicament au stock (Pharmacie)"""
    
    pharmacie = db.query(Pharmacie).filter(
        Pharmacie.user_id == current_user.id
    ).first()
    if not pharmacie:
        raise HTTPException(status_code=404, detail="Pharmacie non trouvée")
    
    medicament = Medicament(
        pharmacie_id=pharmacie.id,
        **medicament_data.dict()
    )
    
    db.add(medicament)
    db.commit()
    db.refresh(medicament)
    
    return medicament


@router.get("/", response_model=List[MedicamentWithPharmacie])
def search_medicaments(
    q: Optional[str] = Query(None, description="Recherche par nom"),
    categorie: Optional[str] = None,
    forme: Optional[str] = None,
    disponible: Optional[bool] = None,
    ordonnance_requise: Optional[bool] = None,
    prix_max: Optional[float] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Rechercher des médicaments dans toutes les pharmacies"""
    
    query = db.query(Medicament).join(Pharmacie).join(User).filter(
        User.status == UserStatus.APPROVED
    )
    
    if q:
        query = query.filter(Medicament.nom.ilike(f"%{q}%"))
    if categorie:
        query = query.filter(Medicament.categorie == categorie)
    if forme:
        query = query.filter(Medicament.forme == forme)
    if disponible is not None:
        query = query.filter(
            Medicament.quantite_stock > 0 if disponible else Medicament.quantite_stock == 0
        )
    if ordonnance_requise is not None:
        query = query.filter(Medicament.ordonnance_requise == ordonnance_requise)
    if prix_max:
        query = query.filter(Medicament.prix_unitaire <= prix_max)
    
    medicaments = query.offset(offset).limit(limit).all()
    
    # Enrichir avec les infos pharmacie
    result = []
    for m in medicaments:
        pharmacie = db.query(Pharmacie).filter(Pharmacie.id == m.pharmacie_id).first()
        
        # Extraire les coordonnées de la pharmacie
        latitude, longitude = None, None
        if pharmacie and pharmacie.localisation:
            point_text = db.execute(func.ST_AsText(pharmacie.localisation)).scalar()
            if point_text:
                coords = point_text.replace("POINT(", "").replace(")", "").split()
                longitude = float(coords[0])
                latitude = float(coords[1])
        
        result.append({
            "id": m.id,
            "pharmacie_id": m.pharmacie_id,
            "nom": m.nom,
            "description": m.description,
            "categorie": m.categorie,
            "dosage": m.dosage,
            "forme": m.forme,
            "prix_unitaire": m.prix_unitaire,
            "quantite_stock": m.quantite_stock,
            "quantite_minimum": m.quantite_minimum,
            "ordonnance_requise": m.ordonnance_requise,
            "is_disponible": m.is_disponible,
            "date_expiration": m.date_expiration,
            "created_at": m.created_at,
            "updated_at": m.updated_at,
            "pharmacie_nom": pharmacie.nom if pharmacie else None,
            "pharmacie_adresse": pharmacie.adresse if pharmacie else None,
            "pharmacie_telephone": pharmacie.telephone if pharmacie else None,
            "pharmacie_latitude": latitude,
            "pharmacie_longitude": longitude
        })
    
    return result


@router.get("/me", response_model=List[MedicamentResponse])
def get_my_stock(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_pharmacie)
):
    """Voir le stock de sa pharmacie"""
    
    pharmacie = db.query(Pharmacie).filter(
        Pharmacie.user_id == current_user.id
    ).first()
    if not pharmacie:
        raise HTTPException(status_code=404, detail="Pharmacie non trouvée")
    
    medicaments = db.query(Medicament).filter(
        Medicament.pharmacie_id == pharmacie.id
    ).offset(offset).limit(limit).all()
    
    return medicaments


@router.get("/{medicament_id}", response_model=MedicamentResponse)
def get_medicament(
    medicament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Détails d'un médicament"""
    medicament = db.query(Medicament).filter(Medicament.id == medicament_id).first()
    if not medicament:
        raise HTTPException(status_code=404, detail="Médicament non trouvé")
    return medicament


@router.put("/{medicament_id}", response_model=MedicamentResponse)
def update_medicament(
    medicament_id: int,
    update_data: MedicamentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_pharmacie)
):
    """Mettre à jour un médicament (Pharmacie)"""
    
    pharmacie = db.query(Pharmacie).filter(
        Pharmacie.user_id == current_user.id
    ).first()
    if not pharmacie:
        raise HTTPException(status_code=404, detail="Pharmacie non trouvée")
    
    medicament = db.query(Medicament).filter(
        Medicament.id == medicament_id,
        Medicament.pharmacie_id == pharmacie.id
    ).first()
    if not medicament:
        raise HTTPException(status_code=404, detail="Médicament non trouvé")
    
    old_stock = medicament.quantite_stock
    
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(medicament, field, value)
    
    db.commit()
    db.refresh(medicament)
    
    # Notification si stock faible ou épuisé
    if medicament.quantite_stock <= medicament.quantite_minimum and old_stock > medicament.quantite_minimum:
        notif_type = "stock_epuise" if medicament.quantite_stock == 0 else "stock_faible"
        notification = Notification(
            user_id=current_user.id,
            title=f"⚠️ Stock {notif_type.replace('_', ' ')}",
            message=(
                f"Le médicament '{medicament.nom}' a un stock "
                f"{'épuisé' if medicament.quantite_stock == 0 else f'faible ({medicament.quantite_stock} unités)'}"
            ),
            type=notif_type,
            data=json.dumps({
                "medicament_id": medicament.id,
                "nom": medicament.nom,
                "stock": medicament.quantite_stock,
                "seuil": medicament.quantite_minimum
            }),
            is_read=False
        )
        db.add(notification)
        db.commit()
    
    return medicament


@router.patch("/{medicament_id}/stock", response_model=MedicamentResponse)
def update_stock(
    medicament_id: int,
    stock_data: StockUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_pharmacie)
):
    """Mettre à jour rapidement le stock (Pharmacie)"""
    
    pharmacie = db.query(Pharmacie).filter(
        Pharmacie.user_id == current_user.id
    ).first()
    if not pharmacie:
        raise HTTPException(status_code=404, detail="Pharmacie non trouvée")
    
    medicament = db.query(Medicament).filter(
        Medicament.id == medicament_id,
        Medicament.pharmacie_id == pharmacie.id
    ).first()
    if not medicament:
        raise HTTPException(status_code=404, detail="Médicament non trouvé")
    
    old_stock = medicament.quantite_stock
    
    # Mettre à jour selon l'opération
    if stock_data.operation == "set":
        medicament.quantite_stock = stock_data.quantite
    elif stock_data.operation == "add":
        medicament.quantite_stock += stock_data.quantite
    elif stock_data.operation == "subtract":
        medicament.quantite_stock = max(0, medicament.quantite_stock - stock_data.quantite)
    else:
        raise HTTPException(status_code=400, detail="Opération invalide")
    
    # Mettre à jour is_disponible
    medicament.is_disponible = medicament.quantite_stock > 0
    
    db.commit()
    db.refresh(medicament)
    
    # Notification si stock faible
    if medicament.quantite_stock <= medicament.quantite_minimum and old_stock > medicament.quantite_minimum:
        notif_type = "stock_epuise" if medicament.quantite_stock == 0 else "stock_faible"
        notification = Notification(
            user_id=current_user.id,
            title=f"⚠️ Stock {notif_type.replace('_', ' ')}",
            message=f"Le médicament '{medicament.nom}' a un stock de {medicament.quantite_stock} unités",
            type=notif_type,
            data=json.dumps({
                "medicament_id": medicament.id,
                "nom": medicament.nom,
                "stock": medicament.quantite_stock
            }),
            is_read=False
        )
        db.add(notification)
        db.commit()
    
    return medicament


@router.delete("/{medicament_id}")
def delete_medicament(
    medicament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_pharmacie)
):
    """Supprimer un médicament du stock (Pharmacie)"""
    
    pharmacie = db.query(Pharmacie).filter(
        Pharmacie.user_id == current_user.id
    ).first()
    if not pharmacie:
        raise HTTPException(status_code=404, detail="Pharmacie non trouvée")
    
    medicament = db.query(Medicament).filter(
        Medicament.id == medicament_id,
        Medicament.pharmacie_id == pharmacie.id
    ).first()
    if not medicament:
        raise HTTPException(status_code=404, detail="Médicament non trouvé")
    
    db.delete(medicament)
    db.commit()
    
    return {"message": "Médicament supprimé avec succès"}


@router.get("/alerts/low-stock", response_model=List[MedicamentResponse])
def get_low_stock_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_pharmacie)
):
    """Voir les médicaments en stock faible (Pharmacie)"""
    
    pharmacie = db.query(Pharmacie).filter(
        Pharmacie.user_id == current_user.id
    ).first()
    if not pharmacie:
        raise HTTPException(status_code=404, detail="Pharmacie non trouvée")
    
    medicaments = db.query(Medicament).filter(
        Medicament.pharmacie_id == pharmacie.id,
        Medicament.quantite_stock <= Medicament.quantite_minimum
    ).all()
    
    return medicaments