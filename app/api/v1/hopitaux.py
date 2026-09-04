from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint, ST_Distance, ST_Transform

from ...core.database import get_db
from ...core.dependencies import require_hopital, require_admin
from ...core.security import get_password_hash
from ...models.user import User, UserRole, UserStatus
from ...models.hopital import Hopital
from ...schemas.hopital import HopitalCreate, HopitalResponse, HopitalUpdate

router = APIRouter(prefix="/hopitaux", tags=["Hopitaux"])

@router.post("/register", response_model=HopitalResponse)
def register_hopital(
    hopital_data: HopitalCreate,
    db: Session = Depends(get_db)
):
    """Inscription d'un nouvel hôpital (en attente de validation)"""
    existing_user = db.query(User).filter(
        (User.email == hopital_data.user.email) | 
        (User.telephone == hopital_data.user.telephone)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email ou téléphone déjà utilisé"
        )
    
    user = User(
        nom=hopital_data.user.nom,
        prenom=hopital_data.user.prenom,
        email=hopital_data.user.email,
        telephone=hopital_data.user.telephone,
        password=get_password_hash(hopital_data.user.password),
        role=UserRole.HOPITAL,
        status=UserStatus.PENDING
    )
    db.add(user)
    db.flush()
    
    hopital = Hopital(
        user_id=user.id,
        nom=hopital_data.nom,
        adresse=hopital_data.adresse,
        telephone=hopital_data.telephone,
        services=hopital_data.services
    )
    
    if hopital_data.latitude and hopital_data.longitude:
        hopital.localisation = ST_SetSRID(
            ST_MakePoint(hopital_data.longitude, hopital_data.latitude),
            4326
        )
    
    db.add(hopital)
    db.commit()
    db.refresh(hopital)
    return hopital

@router.get("/me", response_model=HopitalResponse)
def get_my_hopital_profile(
    current_user: User = Depends(require_hopital),
    db: Session = Depends(get_db)
):
    """Obtenir le profil de l'hôpital connecté"""
    hopital = db.query(Hopital).filter(Hopital.user_id == current_user.id).first()
    if not hopital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil hôpital non trouvé"
        )
    return hopital

@router.put("/me", response_model=HopitalResponse)
def update_my_hopital_profile(
    hopital_update: HopitalUpdate,
    current_user: User = Depends(require_hopital),
    db: Session = Depends(get_db)
):
    """Mettre à jour le profil de l'hôpital connecté"""
    hopital = db.query(Hopital).filter(Hopital.user_id == current_user.id).first()
    if not hopital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil hôpital non trouvé"
        )
    
    if hopital_update.nom:
        hopital.nom = hopital_update.nom
    if hopital_update.adresse is not None:
        hopital.adresse = hopital_update.adresse
    if hopital_update.telephone is not None:
        hopital.telephone = hopital_update.telephone
    if hopital_update.services is not None:
        hopital.services = hopital_update.services
    
    if hopital_update.latitude is not None and hopital_update.longitude is not None:
        hopital.localisation = ST_SetSRID(
            ST_MakePoint(hopital_update.longitude, hopital_update.latitude),
            4326
        )
    
    db.commit()
    db.refresh(hopital)
    return hopital

@router.get("/", response_model=List[HopitalResponse])
def get_hopitaux(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Obtenir la liste des hôpitaux (uniquement approuvés)"""
    return db.query(Hopital).join(User).filter(
        User.status == UserStatus.APPROVED
    ).offset(offset).limit(limit).all()

@router.get("/nearby", response_model=List[dict])
def get_nearby_hopitaux(
    latitude: float,
    longitude: float,
    radius: float = Query(10.0, description="Rayon en km"),
    db: Session = Depends(get_db)
):
    """Trouver les hôpitaux proches d'une position"""
    from sqlalchemy import func
    
    user_point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
    
    hopitaux = db.query(Hopital).join(User).filter(
        User.status == UserStatus.APPROVED,
        Hopital.localisation.is_not(None),
        ST_Distance(
            ST_Transform(Hopital.localisation, 3857),
            ST_Transform(user_point, 3857)
        ) <= radius * 1000
    ).all()
    
    result = []
    for h in hopitaux:
        distance = db.execute(
            ST_Distance(
                ST_Transform(h.localisation, 3857),
                ST_Transform(user_point, 3857)
            ) / 1000
        ).scalar()
        
        point = db.execute(func.ST_AsText(h.localisation)).scalar()
        if point:
            coords = point.replace("POINT(", "").replace(")", "").split()
            longitude_val = float(coords[0])
            latitude_val = float(coords[1])
        else:
            latitude_val = None
            longitude_val = None
        
        result.append({
            "id": h.id,
            "nom": h.nom,
            "adresse": h.adresse,
            "telephone": h.telephone,
            "services": h.services,
            "is_open": h.is_open,
            "latitude": latitude_val,
            "longitude": longitude_val,
            "distance": round(distance if distance else 0, 2)
        })
    
    return sorted(result, key=lambda x: x["distance"])