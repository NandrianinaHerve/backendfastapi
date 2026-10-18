
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint, ST_AsText

from ...core.database import get_db
from ...core.dependencies import require_chauffeur, require_admin
from ...core.security import get_password_hash
from ...models.user import User, UserRole, UserStatus
from ...models.chauffeur import Chauffeur
from ...models.vehicule import Vehicule
from ...schemas.chauffeur import ChauffeurCreate, ChauffeurResponse, ChauffeurUpdate

router = APIRouter(prefix="/chauffeurs", tags=["Chauffeurs"])


@router.post("/register", response_model=ChauffeurResponse)
def register_chauffeur(
    chauffeur_data: ChauffeurCreate,
    db: Session = Depends(get_db)
):
    """Inscription d'un nouveau chauffeur (en attente de validation)"""
    existing_user = db.query(User).filter(
        (User.email == chauffeur_data.user.email) | 
        (User.telephone == chauffeur_data.user.telephone)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email ou téléphone déjà utilisé"
        )
    
    vehicle_type = chauffeur_data.vehicle_type.upper()
    if vehicle_type not in ['TAXI', 'AMBULANCE']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="vehicle_type doit être 'TAXI' ou 'AMBULANCE'"
        )
    
    user = User(
        nom=chauffeur_data.user.nom,
        prenom=chauffeur_data.user.prenom,
        email=chauffeur_data.user.email,
        telephone=chauffeur_data.user.telephone,
        password=get_password_hash(chauffeur_data.user.password),
        role=UserRole.CHAUFFEUR,
        status=UserStatus.PENDING
    )
    db.add(user)
    db.flush()
    
    chauffeur = Chauffeur(
        user_id=user.id,
        vehicle_type=vehicle_type,
        license_number=chauffeur_data.license_number
    )
    
    if chauffeur_data.latitude and chauffeur_data.longitude:
        chauffeur.localisation = ST_SetSRID(
            ST_MakePoint(chauffeur_data.longitude, chauffeur_data.latitude),
            4326
        )
    
    db.add(chauffeur)
    db.flush()
    
    vehicule = Vehicule(
        chauffeur_id=chauffeur.id,
        immatriculation=chauffeur_data.immatriculation,
        modele=chauffeur_data.modele,
        couleur=chauffeur_data.couleur,
        type=vehicle_type,
        is_active=True
    )
    db.add(vehicule)
    
    db.commit()
    db.refresh(chauffeur)
    db.refresh(vehicule)
    
    return {
        "id": chauffeur.id,
        "user_id": chauffeur.user_id,
        "vehicle_type": chauffeur.vehicle_type,
        "license_number": chauffeur.license_number,
        "latitude": chauffeur_data.latitude,
        "longitude": chauffeur_data.longitude,
        "is_available": chauffeur.is_available,
        "user": user,
        "vehicule": vehicule
    }


# ✅ NOUVELLE ROUTE - LISTE DES CHAUFFEURS
@router.get("/", response_model=List[ChauffeurResponse])
def get_chauffeurs(
    vehicle_type: Optional[str] = None,
    available: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Obtenir la liste des chauffeurs approuvés avec coordonnées GPS"""

    query = (
        db.query(
            Chauffeur,
            func.ST_Y(Chauffeur.localisation).label("latitude"),
            func.ST_X(Chauffeur.localisation).label("longitude")
        )
        .join(User, Chauffeur.user_id == User.id)
        .filter(User.status == UserStatus.APPROVED)
    )

    if vehicle_type is not None:
        query = query.filter(
            Chauffeur.vehicle_type == vehicle_type.upper()
        )

    if available is not None:
        query = query.filter(
            Chauffeur.is_available == available
        )

    rows = query.offset(offset).limit(limit).all()

    result = []

    for chauffeur, latitude, longitude in rows:
        vehicule = db.query(Vehicule).filter(
            Vehicule.chauffeur_id == chauffeur.id
        ).first()

        result.append(
            ChauffeurResponse(
                id=chauffeur.id,
                user_id=chauffeur.user_id,
                vehicle_type=chauffeur.vehicle_type,
                license_number=chauffeur.license_number,
                is_available=chauffeur.is_available,

                latitude=float(latitude) if latitude is not None else None,
                longitude=float(longitude) if longitude is not None else None,

                user=chauffeur.user,
                vehicule=vehicule
            )
        )

    return result


@router.get("/me", response_model=ChauffeurResponse)
def get_my_chauffeur_profile(
    current_user: User = Depends(require_chauffeur),
    db: Session = Depends(get_db)
):
    """Obtenir le profil du chauffeur connecté"""
    chauffeur = db.query(Chauffeur).filter(Chauffeur.user_id == current_user.id).first()
    if not chauffeur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil chauffeur non trouvé"
        )
    
    vehicule = db.query(Vehicule).filter(Vehicule.chauffeur_id == chauffeur.id).first()
    
    latitude = None
    longitude = None
    if chauffeur.localisation:
        point_text = db.execute(func.ST_AsText(chauffeur.localisation)).scalar()
        if point_text:
            coords = point_text.replace("POINT(", "").replace(")", "").split()
            longitude = float(coords[0])
            latitude = float(coords[1])
    
    return {
        "id": chauffeur.id,
        "user_id": chauffeur.user_id,
        "vehicle_type": chauffeur.vehicle_type,
        "license_number": chauffeur.license_number,
        "latitude": latitude,
        "longitude": longitude,
        "is_available": chauffeur.is_available,
        "user": chauffeur.user,
        "vehicule": vehicule
    }


@router.put("/me", response_model=ChauffeurResponse)
def update_my_chauffeur_profile(
    chauffeur_update: ChauffeurUpdate,
    current_user: User = Depends(require_chauffeur),
    db: Session = Depends(get_db)
):
    """Mettre à jour le profil du chauffeur connecté"""
    chauffeur = db.query(Chauffeur).filter(Chauffeur.user_id == current_user.id).first()
    if not chauffeur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil chauffeur non trouvé"
        )
    
    if chauffeur_update.license_number is not None:
        chauffeur.license_number = chauffeur_update.license_number
    
    if chauffeur_update.latitude is not None and chauffeur_update.longitude is not None:
        chauffeur.localisation = ST_SetSRID(
            ST_MakePoint(chauffeur_update.longitude, chauffeur_update.latitude),
            4326
        )
    
    db.commit()
    db.refresh(chauffeur)
    
    vehicule = db.query(Vehicule).filter(Vehicule.chauffeur_id == chauffeur.id).first()
    
    latitude = None
    longitude = None
    if chauffeur.localisation:
        point_text = db.execute(func.ST_AsText(chauffeur.localisation)).scalar()
        if point_text:
            coords = point_text.replace("POINT(", "").replace(")", "").split()
            longitude = float(coords[0])
            latitude = float(coords[1])
    
    return {
        "id": chauffeur.id,
        "user_id": chauffeur.user_id,
        "vehicle_type": chauffeur.vehicle_type,
        "license_number": chauffeur.license_number,
        "latitude": latitude,
        "longitude": longitude,
        "is_available": chauffeur.is_available,
        "user": chauffeur.user,
        "vehicule": vehicule
    }


@router.patch("/me/availability")
def toggle_my_availability(
    is_available: bool,
    current_user: User = Depends(require_chauffeur),
    db: Session = Depends(get_db)
):
    """Activer/désactiver la disponibilité du chauffeur"""
    chauffeur = db.query(Chauffeur).filter(Chauffeur.user_id == current_user.id).first()
    if not chauffeur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil chauffeur non trouvé"
        )
    
    chauffeur.is_available = is_available
    db.commit()
    return {
        "message": f"Disponibilité {'activée' if is_available else 'désactivée'}",
        "is_available": is_available
    }