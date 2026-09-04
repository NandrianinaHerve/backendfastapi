from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ...core.database import get_db
from ...core.dependencies import require_docteur, require_admin
from ...models.user import User
from ...models.disponibilite import Disponibilite
from ...models.docteur import Docteur
from ...schemas.disponibilite import DisponibiliteCreate, DisponibiliteResponse, DisponibiliteUpdate

# ✅ CRÉER LE ROUTER
router = APIRouter(prefix="/disponibilites", tags=["Disponibilites"])

@router.post("/", response_model=DisponibiliteResponse)
def create_disponibilite(
    disponibilite_data: DisponibiliteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_docteur)
):
    """Créer une disponibilité pour le docteur connecté"""
    docteur = db.query(Docteur).filter(Docteur.user_id == current_user.id).first()
    if not docteur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil docteur non trouvé"
        )
    
    disponibilite = Disponibilite(
        docteur_id=docteur.id,
        date=disponibilite_data.date,
        heure_debut=disponibilite_data.heure_debut,
        heure_fin=disponibilite_data.heure_fin,
        is_available=disponibilite_data.is_available
    )
    
    db.add(disponibilite)
    db.commit()
    db.refresh(disponibilite)
    return disponibilite

@router.get("/me", response_model=List[DisponibiliteResponse])
def get_my_disponibilites(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_docteur)
):
    """Obtenir les disponibilités du docteur connecté"""
    docteur = db.query(Docteur).filter(Docteur.user_id == current_user.id).first()
    if not docteur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil docteur non trouvé"
        )
    
    query = db.query(Disponibilite).filter(Disponibilite.docteur_id == docteur.id)
    
    if start_date:
        query = query.filter(Disponibilite.date >= start_date)
    if end_date:
        query = query.filter(Disponibilite.date <= end_date)
    
    return query.order_by(Disponibilite.date).all()

@router.get("/docteur/{docteur_id}", response_model=List[DisponibiliteResponse])
def get_docteur_disponibilites(
    docteur_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Obtenir les disponibilités d'un docteur spécifique"""
    docteur = db.query(Docteur).filter(Docteur.id == docteur_id).first()
    if not docteur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docteur non trouvé"
        )
    
    query = db.query(Disponibilite).filter(
        Disponibilite.docteur_id == docteur_id,
        Disponibilite.is_available == True
    )
    
    if start_date:
        query = query.filter(Disponibilite.date >= start_date)
    if end_date:
        query = query.filter(Disponibilite.date <= end_date)
    
    return query.order_by(Disponibilite.date).all()

@router.put("/{disponibilite_id}", response_model=DisponibiliteResponse)
def update_disponibilite(
    disponibilite_id: int,
    disponibilite_update: DisponibiliteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_docteur)
):
    """Mettre à jour une disponibilité"""
    disponibilite = db.query(Disponibilite).filter(Disponibilite.id == disponibilite_id).first()
    if not disponibilite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Disponibilité non trouvée"
        )
    
    # Vérifier que le docteur possède cette disponibilité
    docteur = db.query(Docteur).filter(Docteur.user_id == current_user.id).first()
    if not docteur or disponibilite.docteur_id != docteur.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )
    
    if disponibilite_update.date:
        disponibilite.date = disponibilite_update.date
    if disponibilite_update.heure_debut:
        disponibilite.heure_debut = disponibilite_update.heure_debut
    if disponibilite_update.heure_fin:
        disponibilite.heure_fin = disponibilite_update.heure_fin
    if disponibilite_update.is_available is not None:
        disponibilite.is_available = disponibilite_update.is_available
    
    db.commit()
    db.refresh(disponibilite)
    return disponibilite

@router.delete("/{disponibilite_id}")
def delete_disponibilite(
    disponibilite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_docteur)
):
    """Supprimer une disponibilité"""
    disponibilite = db.query(Disponibilite).filter(Disponibilite.id == disponibilite_id).first()
    if not disponibilite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Disponibilité non trouvée"
        )
    
    # Vérifier que le docteur possède cette disponibilité
    docteur = db.query(Docteur).filter(Docteur.user_id == current_user.id).first()
    if not docteur or disponibilite.docteur_id != docteur.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )
    
    db.delete(disponibilite)
    db.commit()
    return {"message": "Disponibilité supprimée avec succès"}