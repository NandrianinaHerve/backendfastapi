from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.functions import ST_AsText, ST_SetSRID, ST_MakePoint, ST_Distance, ST_Transform
from typing import List, Optional

from ...core.database import get_db
from ...core.dependencies import get_current_user
from ...models.user import User
from ...models.localisation import Localisation
from ...schemas.localisation import LocalisationCreate, LocalisationResponse

router = APIRouter(prefix="/localisation", tags=["Localisation"])

@router.post("/", response_model=LocalisationResponse)
def update_location(
    location_data: LocalisationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mettre à jour la localisation d'un utilisateur"""
    allowed_roles = ["patient", "docteur", "pharmacie", "chauffeur", "hopital"]
    if current_user.role.value not in allowed_roles:
        raise HTTPException(
            status_code=403, 
            detail="Votre rôle ne permet pas le partage de position"
        )
    
    user_id = location_data.user_id if location_data.user_id else current_user.id
    
    location = db.query(Localisation).filter(
        Localisation.user_id == user_id,
        Localisation.is_active == True
    ).first()
    
    if location:
        location.point = ST_SetSRID(
            ST_MakePoint(location_data.longitude, location_data.latitude), 
            4326
        )
        location.is_active = True
    else:
        location = Localisation(
            user_id=user_id,
            point=ST_SetSRID(
                ST_MakePoint(location_data.longitude, location_data.latitude), 
                4326
            ),
            is_active=True
        )
        db.add(location)
    
    db.commit()
    db.refresh(location)
    
    point_text = db.execute(func.ST_AsText(location.point)).scalar()
    if point_text:
        coords = point_text.replace("POINT(", "").replace(")", "").split()
        longitude = float(coords[0])
        latitude = float(coords[1])
    else:
        latitude = location_data.latitude
        longitude = location_data.longitude
    
    return {
        "id": location.id,
        "user_id": location.user_id,
        "latitude": latitude,
        "longitude": longitude,
        "is_active": location.is_active,
        "updated_at": location.updated_at
    }

@router.get("/{user_id}", response_model=LocalisationResponse)
def get_user_location(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir la localisation d'un utilisateur"""
    if current_user.role.value != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=403, 
            detail="Accès non autorisé"
        )
    
    location = db.query(Localisation).filter(
        Localisation.user_id == user_id,
        Localisation.is_active == True
    ).first()
    
    if not location:
        raise HTTPException(
            status_code=404, 
            detail="Localisation non trouvée"
        )
    
    point_text = db.execute(func.ST_AsText(location.point)).scalar()
    if point_text:
        coords = point_text.replace("POINT(", "").replace(")", "").split()
        longitude = float(coords[0])
        latitude = float(coords[1])
    else:
        latitude = None
        longitude = None
    
    return {
        "id": location.id,
        "user_id": location.user_id,
        "latitude": latitude,
        "longitude": longitude,
        "is_active": location.is_active,
        "updated_at": location.updated_at
    }

@router.get("/nearby/docteurs", response_model=List[dict])
def get_nearby_docteurs(
    latitude: float,
    longitude: float,
    radius: float = Query(10.0, description="Rayon en km"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Trouver les docteurs proches"""
    from ...models.docteur import Docteur
    from ...models.user import User as UserModel, UserStatus
    
    user_point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
    
    query = db.query(
        Docteur,
        (ST_Distance(
            ST_Transform(Docteur.localisation, 3857),
            ST_Transform(user_point, 3857)
        ) / 1000).label("distance")
    ).join(UserModel).filter(
        Docteur.localisation.is_not(None),
        UserModel.status == UserStatus.APPROVED,
        ST_Distance(
            ST_Transform(Docteur.localisation, 3857),
            ST_Transform(user_point, 3857)
        ) <= radius * 1000
    )
    
    results = query.all()
    
    result = []
    for docteur, distance in results:
        point_text = db.execute(func.ST_AsText(docteur.localisation)).scalar()
        if point_text:
            coords = point_text.replace("POINT(", "").replace(")", "").split()
            longitude_val = float(coords[0])
            latitude_val = float(coords[1])
        else:
            latitude_val = None
            longitude_val = None
        
        result.append({
            "id": docteur.id,
            "nom": docteur.user.nom,
            "prenom": docteur.user.prenom,
            "specialite": docteur.specialite.nom if docteur.specialite else None,
            "adresse": docteur.adresse,
            "cabinet": docteur.cabinet,
            "is_available": docteur.is_available,
            "consultation_price": docteur.consultation_price,
            "experience_years": docteur.experience_years,
            "latitude": latitude_val,
            "longitude": longitude_val,
            "distance": round(distance if distance else 0, 2)
        })
    
    return sorted(result, key=lambda x: x["distance"])

@router.get("/nearby/pharmacies", response_model=List[dict])
def get_nearby_pharmacies(
    latitude: float,
    longitude: float,
    radius: float = Query(5.0, description="Rayon en km"),
    garde_only: bool = Query(False, description="Uniquement les pharmacies de garde"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Trouver les pharmacies proches"""
    from ...models.pharmacie import Pharmacie
    from ...models.pharmacie_garde import PharmacieGarde
    from ...models.user import User as UserModel, UserStatus
    from datetime import datetime
    
    user_point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
    
    query = db.query(
        Pharmacie,
        (ST_Distance(
            ST_Transform(Pharmacie.localisation, 3857),
            ST_Transform(user_point, 3857)
        ) / 1000).label("distance")
    ).join(UserModel).filter(
        Pharmacie.localisation.is_not(None),
        UserModel.status == UserStatus.APPROVED,
        ST_Distance(
            ST_Transform(Pharmacie.localisation, 3857),
            ST_Transform(user_point, 3857)
        ) <= radius * 1000
    )
    
    if garde_only:
        now = datetime.now()
        query = query.join(PharmacieGarde).filter(
            PharmacieGarde.date_debut <= now,
            PharmacieGarde.date_fin >= now
        )
    
    results = query.all()
    
    result = []
    for pharmacie, distance in results:
        point_text = db.execute(func.ST_AsText(pharmacie.localisation)).scalar()
        if point_text:
            coords = point_text.replace("POINT(", "").replace(")", "").split()
            longitude_val = float(coords[0])
            latitude_val = float(coords[1])
        else:
            latitude_val = None
            longitude_val = None
        
        result.append({
            "id": pharmacie.id,
            "nom": pharmacie.nom,
            "adresse": pharmacie.adresse,
            "telephone": pharmacie.telephone,
            "is_open": pharmacie.is_open,
            "latitude": latitude_val,
            "longitude": longitude_val,
            "distance": round(distance if distance else 0, 2)
        })
    
    return sorted(result, key=lambda x: x["distance"])