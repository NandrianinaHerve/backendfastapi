from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint, ST_Distance, ST_Transform

from ...core.database import get_db
from ...core.dependencies import require_pharmacie, require_admin
from ...core.security import get_password_hash
from ...models.user import User, UserRole, UserStatus
from ...models.pharmacie import Pharmacie
from ...models.pharmacie_garde import PharmacieGarde
from ...schemas.pharmacie import PharmacieCreate, PharmacieResponse, PharmacieUpdate

router = APIRouter(prefix="/pharmacie", tags=["Pharmacie"])

@router.post("/register", response_model=PharmacieResponse)
def register_pharmacie(
    pharmacie_data: PharmacieCreate,
    db: Session = Depends(get_db)
):
    """Inscription d'une nouvelle pharmacie (en attente de validation)"""
    existing_user = db.query(User).filter(
        (User.email == pharmacie_data.user.email) | 
        (User.telephone == pharmacie_data.user.telephone)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email ou téléphone déjà utilisé"
        )
    
    user = User(
        nom=pharmacie_data.user.nom,
        prenom=pharmacie_data.user.prenom,
        email=pharmacie_data.user.email,
        telephone=pharmacie_data.user.telephone,
        password=get_password_hash(pharmacie_data.user.password),
        role=UserRole.PHARMACIE,
        status=UserStatus.PENDING
    )
    db.add(user)
    db.flush()
    
    pharmacie = Pharmacie(
        user_id=user.id,
        nom=pharmacie_data.nom,
        adresse=pharmacie_data.adresse,
        telephone=pharmacie_data.telephone
    )
    
    if pharmacie_data.latitude and pharmacie_data.longitude:
        pharmacie.localisation = ST_SetSRID(
            ST_MakePoint(pharmacie_data.longitude, pharmacie_data.latitude),
            4326
        )
    
    db.add(pharmacie)
    db.commit()
    db.refresh(pharmacie)
    return pharmacie

@router.get("/me", response_model=PharmacieResponse)
def get_my_pharmacie_profile(
    current_user: User = Depends(require_pharmacie),
    db: Session = Depends(get_db)
):
    """Obtenir le profil de la pharmacie connectée"""
    pharmacie = db.query(Pharmacie).filter(Pharmacie.user_id == current_user.id).first()
    if not pharmacie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil pharmacie non trouvé"
        )
    return pharmacie

@router.put("/me", response_model=PharmacieResponse)
def update_my_pharmacie_profile(
    pharmacie_update: PharmacieUpdate,
    current_user: User = Depends(require_pharmacie),
    db: Session = Depends(get_db)
):
    """Mettre à jour le profil de la pharmacie connectée"""
    pharmacie = db.query(Pharmacie).filter(Pharmacie.user_id == current_user.id).first()
    if not pharmacie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil pharmacie non trouvé"
        )
    
    if pharmacie_update.nom:
        pharmacie.nom = pharmacie_update.nom
    if pharmacie_update.adresse is not None:
        pharmacie.adresse = pharmacie_update.adresse
    if pharmacie_update.telephone is not None:
        pharmacie.telephone = pharmacie_update.telephone
    
    if pharmacie_update.latitude is not None and pharmacie_update.longitude is not None:
        pharmacie.localisation = ST_SetSRID(
            ST_MakePoint(pharmacie_update.longitude, pharmacie_update.latitude),
            4326
        )
    
    db.commit()
    db.refresh(pharmacie)
    return pharmacie

@router.patch("/me/status")
def toggle_my_status(
    is_open: bool,
    current_user: User = Depends(require_pharmacie),
    db: Session = Depends(get_db)
):
    """Ouvrir/Fermer la pharmacie connectée"""
    pharmacie = db.query(Pharmacie).filter(Pharmacie.user_id == current_user.id).first()
    if not pharmacie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil pharmacie non trouvé"
        )
    
    pharmacie.is_open = is_open
    db.commit()
    return {
        "message": f"Pharmacie {'ouverte' if is_open else 'fermée'}",
        "is_open": is_open
    }

@router.get("/", response_model=List[PharmacieResponse])
def get_pharmacies(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Obtenir la liste des pharmacies (uniquement approuvées)"""
    return db.query(Pharmacie).join(User).filter(
        User.status == UserStatus.APPROVED
    ).offset(offset).limit(limit).all()

@router.get("/nearby", response_model=List[dict])
def get_nearby_pharmacies(
    latitude: float,
    longitude: float,
    radius: float = Query(10.0, description="Rayon en km"),
    db: Session = Depends(get_db)
):
    """Trouver les pharmacies proches d'une position"""
    from sqlalchemy import func
    
    user_point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
    
    pharmacies = db.query(Pharmacie).join(User).filter(
        User.status == UserStatus.APPROVED,
        Pharmacie.localisation.is_not(None),
        ST_Distance(
            ST_Transform(Pharmacie.localisation, 3857),
            ST_Transform(user_point, 3857)
        ) <= radius * 1000
    ).all()
    
    result = []
    for p in pharmacies:
        distance = db.execute(
            ST_Distance(
                ST_Transform(p.localisation, 3857),
                ST_Transform(user_point, 3857)
            ) / 1000
        ).scalar()
        
        point = db.execute(func.ST_AsText(p.localisation)).scalar()
        if point:
            coords = point.replace("POINT(", "").replace(")", "").split()
            longitude_val = float(coords[0])
            latitude_val = float(coords[1])
        else:
            latitude_val = None
            longitude_val = None
        
        result.append({
            "id": p.id,
            "nom": p.nom,
            "adresse": p.adresse,
            "telephone": p.telephone,
            "is_open": p.is_open,
            "latitude": latitude_val,
            "longitude": longitude_val,
            "distance": round(distance if distance else 0, 2)
        })
    
    return sorted(result, key=lambda x: x["distance"])

@router.post("/me/garde")
def set_pharmacie_garde(
    date_debut: str,
    date_fin: str,
    current_user: User = Depends(require_pharmacie),
    db: Session = Depends(get_db)
):
    """Déclarer une période de garde pour la pharmacie connectée"""
    from datetime import datetime
    
    pharmacie = db.query(Pharmacie).filter(Pharmacie.user_id == current_user.id).first()
    if not pharmacie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil pharmacie non trouvé"
        )
    
    try:
        debut = datetime.fromisoformat(date_debut)
        fin = datetime.fromisoformat(date_fin)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format de date invalide. Utilisez ISO format (YYYY-MM-DDTHH:MM:SS)"
        )
    
    garde = PharmacieGarde(
        pharmacie_id=pharmacie.id,
        date_debut=debut,
        date_fin=fin
    )
    
    db.add(garde)
    db.commit()
    
    return {
        "message": "Garde déclarée avec succès",
        "date_debut": debut,
        "date_fin": fin
    }

@router.get("/garde", response_model=List[dict])
def get_pharmacies_de_garde(
    db: Session = Depends(get_db)
):
    """Obtenir les pharmacies de garde actuelles"""
    from sqlalchemy import func
    from datetime import datetime
    
    now = datetime.now()
    
    pharmacies = db.query(Pharmacie).join(
        PharmacieGarde, Pharmacie.id == PharmacieGarde.pharmacie_id
    ).join(User).filter(
        User.status == UserStatus.APPROVED,
        PharmacieGarde.date_debut <= now,
        PharmacieGarde.date_fin >= now
    ).all()
    
    result = []
    for p in pharmacies:
        point = db.execute(func.ST_AsText(p.localisation)).scalar()
        if point:
            coords = point.replace("POINT(", "").replace(")", "").split()
            longitude_val = float(coords[0])
            latitude_val = float(coords[1])
        else:
            latitude_val = None
            longitude_val = None
        
        result.append({
            "id": p.id,
            "nom": p.nom,
            "adresse": p.adresse,
            "telephone": p.telephone,
            "latitude": latitude_val,
            "longitude": longitude_val,
            "is_open": p.is_open
        })
    
    return result