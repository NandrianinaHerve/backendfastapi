from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ...core.database import get_db
from ...models.specialite import Specialite
from ...schemas.specialite import SpecialiteResponse, SpecialiteCreate

router = APIRouter(prefix="/specialites", tags=["Spécialités"])


# ============================================
# LISTE DES SPÉCIALITÉS (public, sans auth)
# ============================================
@router.get("/", response_model=List[SpecialiteResponse])
def get_specialites(
    db: Session = Depends(get_db),
):
    """Liste toutes les spécialités médicales (endpoint public)"""
    specialites = db.query(Specialite).order_by(Specialite.nom).all()
    return specialites


# ============================================
# DÉTAIL D'UNE SPÉCIALITÉ
# ============================================
@router.get("/{specialite_id}", response_model=SpecialiteResponse)
def get_specialite(
    specialite_id: int,
    db: Session = Depends(get_db),
):
    """Détail d'une spécialité"""
    specialite = db.query(Specialite).filter(Specialite.id == specialite_id).first()
    if not specialite:
        raise HTTPException(status_code=404, detail="Spécialité non trouvée")
    return specialite


# ============================================
# CRÉER UNE SPÉCIALITÉ (admin)
# ============================================
@router.post("/", response_model=SpecialiteResponse, status_code=201)
def create_specialite(
    data: SpecialiteCreate,
    db: Session = Depends(get_db),
):
    """Créer une spécialité (admin)"""
    existing = db.query(Specialite).filter(Specialite.nom == data.nom).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette spécialité existe déjà",
        )
    
    specialite = Specialite(
        nom=data.nom,
        description=data.description,
        icone=data.icone,
    )
    db.add(specialite)
    db.commit()
    db.refresh(specialite)
    return specialite