from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, json
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint, ST_Distance, ST_Transform
from geoalchemy2.types import Geography
from sqlalchemy import func,cast

from app.models.notification import Notification
from ...core.database import get_db
from ...core.dependencies import require_pharmacie, require_admin
from ...core.security import get_password_hash
from ...models.user import User, UserRole, UserStatus
from ...models.pharmacie import Pharmacie
from ...models.pharmacie_garde import PharmacieGarde
from ...schemas.pharmacie import PharmacieCreate, PharmacieResponse, PharmacieUpdate

router = APIRouter(prefix="/pharmacie", tags=["Pharmacie"])


class PharmacieGardeCreate(BaseModel):
    date_debut: datetime
    date_fin: datetime


def serialize_garde(garde: PharmacieGarde):
    return {
        "id": garde.id,
        "pharmacie_id": garde.pharmacie_id,
        "date_debut": garde.date_debut,
        "date_fin": garde.date_fin,
        "created_at": garde.created_at,
    }

# @router.post("/register", response_model=PharmacieResponse)
# def register_pharmacie(
#     pharmacie_data: PharmacieCreate,
#     db: Session = Depends(get_db)
# ):
#     """Inscription d'une nouvelle pharmacie (en attente de validation)"""
#     existing_user = db.query(User).filter(
#         (User.email == pharmacie_data.user.email) | 
#         (User.telephone == pharmacie_data.user.telephone)
#     ).first()
#     if existing_user:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Email ou téléphone déjà utilisé"
#         )
    
#     user = User(
#         nom=pharmacie_data.user.nom,
#         prenom=pharmacie_data.user.prenom,
#         email=pharmacie_data.user.email,
#         telephone=pharmacie_data.user.telephone,
#         password=get_password_hash(pharmacie_data.user.password),
#         role=UserRole.PHARMACIE,
#         status=UserStatus.PENDING
#     )
#     db.add(user)
#     db.flush()
    
#     pharmacie = Pharmacie(
#         user_id=user.id,
#         nom=pharmacie_data.nom,
#         adresse=pharmacie_data.adresse,
#         telephone=pharmacie_data.telephone
#     )
    
#     # if pharmacie_data.latitude and pharmacie_data.longitude:
#     #     pharmacie.localisation = ST_SetSRID(
#     #         ST_MakePoint(pharmacie_data.longitude, pharmacie_data.latitude),
#     #         4326
#     #     )
#     if (
#     pharmacie_data.latitude is not None
#     and pharmacie_data.longitude is not None
#         ):
#      pharmacie.localisation = ST_SetSRID(
#         ST_MakePoint(
#             pharmacie_data.longitude,
#             pharmacie_data.latitude
#         ),
#         4326
#     )
    
#     db.add(pharmacie)
#     db.commit()
#     db.refresh(pharmacie)
#     return pharmacie
@router.post("/register", response_model=PharmacieResponse)
def register_pharmacie(
    pharmacie_data: PharmacieCreate,
    db: Session = Depends(get_db)
):
    """Inscription d'une nouvelle pharmacie (en attente de validation)."""

    # =========================================================
    # 1. Vérifier si l'email ou le téléphone existe déjà
    # =========================================================

    existing_user = db.query(User).filter(
        (User.email == pharmacie_data.user.email) |
        (User.telephone == pharmacie_data.user.telephone)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email ou téléphone déjà utilisé"
        )

    # =========================================================
    # 2. Créer l'utilisateur
    # =========================================================

    user = User(
        nom=pharmacie_data.user.nom,
        prenom=pharmacie_data.user.prenom,
        email=pharmacie_data.user.email,
        telephone=pharmacie_data.user.telephone,
        password=get_password_hash(
            pharmacie_data.user.password
        ),
        role=UserRole.PHARMACIE,
        status=UserStatus.PENDING
    )

    db.add(user)

    # Récupérer user.id
    db.flush()

    # =========================================================
    # 3. Créer la pharmacie
    # =========================================================

    pharmacie = Pharmacie(
        user_id=user.id,
        nom=pharmacie_data.nom,
        adresse=pharmacie_data.adresse,
        telephone=pharmacie_data.telephone,
        is_open=False
    )

    # =========================================================
    # 4. Enregistrer la localisation PostGIS
    # =========================================================

    if (
        pharmacie_data.latitude is not None
        and pharmacie_data.longitude is not None
    ):
        pharmacie.localisation = ST_SetSRID(
            ST_MakePoint(
                pharmacie_data.longitude,
                pharmacie_data.latitude
            ),
            4326
        )

    db.add(pharmacie)

    # =========================================================
    # 5. Sauvegarder
    # =========================================================

    db.commit()

    db.refresh(user)
    db.refresh(pharmacie)

    # =========================================================
    # 6. Récupérer les coordonnées depuis PostGIS
    # =========================================================

    coordinates = (
        db.query(
            func.ST_Y(
                Pharmacie.localisation
            ).label("latitude"),

            func.ST_X(
                Pharmacie.localisation
            ).label("longitude")
        )
        .filter(
            Pharmacie.id == pharmacie.id
        )
        .first()
    )

    latitude = None
    longitude = None

    if coordinates:
        if coordinates.latitude is not None:
            latitude = float(coordinates.latitude)

        if coordinates.longitude is not None:
            longitude = float(coordinates.longitude)

    # =========================================================
    # 7. Retourner la réponse
    # =========================================================

    return PharmacieResponse(
        id=pharmacie.id,
        user_id=pharmacie.user_id,
        nom=pharmacie.nom,
        adresse=pharmacie.adresse,
        telephone=pharmacie.telephone,
        is_open=pharmacie.is_open,
        latitude=latitude,
        longitude=longitude,
        user=pharmacie.user
    )

# @router.get("/me", response_model=PharmacieResponse)
# def get_my_pharmacie_profile(
#     current_user: User = Depends(require_pharmacie),
#     db: Session = Depends(get_db)
# ):
#     """Obtenir le profil de la pharmacie connectée"""
#     pharmacie = db.query(Pharmacie).filter(Pharmacie.user_id == current_user.id).first()
#     if not pharmacie:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Profil pharmacie non trouvé"
#         )
#     return pharmacie
@router.get("/me", response_model=PharmacieResponse)
def get_my_pharmacie_profile(
    current_user: User = Depends(require_pharmacie),
    db: Session = Depends(get_db)
):
    """Obtenir le profil de la pharmacie connectée avec coordonnées GPS"""

    pharmacie = (
        db.query(
            Pharmacie,
            func.ST_Y(Pharmacie.localisation).label("latitude"),
            func.ST_X(Pharmacie.localisation).label("longitude")
        )
        .filter(Pharmacie.user_id == current_user.id)
        .first()
    )

    if not pharmacie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil pharmacie non trouvé"
        )

    pharmacie_obj, latitude, longitude = pharmacie

    return PharmacieResponse(
        id=pharmacie_obj.id,
        user_id=pharmacie_obj.user_id,
        nom=pharmacie_obj.nom,
        adresse=pharmacie_obj.adresse,
        telephone=pharmacie_obj.telephone,
        latitude=float(latitude) if latitude is not None else None,
        longitude=float(longitude) if longitude is not None else None,
        is_open=pharmacie_obj.is_open,
        user=pharmacie_obj.user
    )

# @router.put("/me", response_model=PharmacieResponse)
# def update_my_pharmacie_profile(
#     pharmacie_update: PharmacieUpdate,
#     current_user: User = Depends(require_pharmacie),
#     db: Session = Depends(get_db)
# ):
#     """Mettre à jour le profil de la pharmacie connectée"""
#     pharmacie = db.query(Pharmacie).filter(Pharmacie.user_id == current_user.id).first()
#     if not pharmacie:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Profil pharmacie non trouvé"
#         )
    
#     if pharmacie_update.nom:
#         pharmacie.nom = pharmacie_update.nom
#     if pharmacie_update.adresse is not None:
#         pharmacie.adresse = pharmacie_update.adresse
#     if pharmacie_update.telephone is not None:
#         pharmacie.telephone = pharmacie_update.telephone
    
#     if pharmacie_update.latitude is not None and pharmacie_update.longitude is not None:
#         pharmacie.localisation = ST_SetSRID(
#             ST_MakePoint(pharmacie_update.longitude, pharmacie_update.latitude),
#             4326
#         )
    
#     db.commit()
#     db.refresh(pharmacie)
#     return pharmacie

@router.put("/me", response_model=PharmacieResponse)
def update_my_pharmacie_profile(
    pharmacie_update: PharmacieUpdate,
    current_user: User = Depends(require_pharmacie),
    db: Session = Depends(get_db)
):
    """Mettre à jour le profil de la pharmacie connectée"""

    pharmacie = (
        db.query(Pharmacie)
        .filter(Pharmacie.user_id == current_user.id)
        .first()
    )

    if not pharmacie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil pharmacie non trouvé"
        )

    # Mise à jour du nom
    if pharmacie_update.nom is not None:
        pharmacie.nom = pharmacie_update.nom

    # Mise à jour de l'adresse
    if pharmacie_update.adresse is not None:
        pharmacie.adresse = pharmacie_update.adresse

    # Mise à jour du téléphone
    if pharmacie_update.telephone is not None:
        pharmacie.telephone = pharmacie_update.telephone

    # Mise à jour des coordonnées GPS
    if (
        pharmacie_update.latitude is not None
        and pharmacie_update.longitude is not None
    ):
        pharmacie.localisation = ST_SetSRID(
            ST_MakePoint(
                pharmacie_update.longitude,
                pharmacie_update.latitude
            ),
            4326
        )

    db.commit()
    db.refresh(pharmacie)

    # Récupérer les coordonnées depuis PostGIS
    coordinates = db.query(
        func.ST_Y(Pharmacie.localisation).label("latitude"),
        func.ST_X(Pharmacie.localisation).label("longitude")
    ).filter(
        Pharmacie.id == pharmacie.id
    ).first()

    latitude = coordinates.latitude if coordinates else None
    longitude = coordinates.longitude if coordinates else None

    return PharmacieResponse(
        id=pharmacie.id,
        user_id=pharmacie.user_id,
        nom=pharmacie.nom,
        adresse=pharmacie.adresse,
        telephone=pharmacie.telephone,
        latitude=float(latitude) if latitude is not None else None,
        longitude=float(longitude) if longitude is not None else None,
        is_open=pharmacie.is_open,
        user=pharmacie.user
    )
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


@router.get("/me/garde")
def get_my_duties(
    current_user: User = Depends(require_pharmacie),
    db: Session = Depends(get_db)
):
    pharmacie = db.query(Pharmacie).filter(
        Pharmacie.user_id == current_user.id
    ).first()
    if not pharmacie:
        raise HTTPException(status_code=404, detail="Profil pharmacie non trouvé")

    gardes = db.query(PharmacieGarde).filter(
        PharmacieGarde.pharmacie_id == pharmacie.id
    ).order_by(PharmacieGarde.date_debut.desc()).all()
    return [serialize_garde(garde) for garde in gardes]


@router.post("/me/garde", status_code=status.HTTP_201_CREATED)
def create_my_duty(
    garde_data: PharmacieGardeCreate,
    current_user: User = Depends(require_pharmacie),
    db: Session = Depends(get_db)
):
    if garde_data.date_fin <= garde_data.date_debut:
        raise HTTPException(status_code=400, detail="La date de fin doit être postérieure au début")

    pharmacie = db.query(Pharmacie).filter(
        Pharmacie.user_id == current_user.id
    ).first()
    if not pharmacie:
        raise HTTPException(status_code=404, detail="Profil pharmacie non trouvé")

    garde = PharmacieGarde(
        pharmacie_id=pharmacie.id,
        date_debut=garde_data.date_debut,
        date_fin=garde_data.date_fin,
    )
    db.add(garde)
    db.commit()
    db.refresh(garde)
    return serialize_garde(garde)


@router.delete("/me/garde/{garde_id}")
def delete_my_duty(
    garde_id: int,
    current_user: User = Depends(require_pharmacie),
    db: Session = Depends(get_db)
):
    pharmacie = db.query(Pharmacie).filter(
        Pharmacie.user_id == current_user.id
    ).first()
    if not pharmacie:
        raise HTTPException(status_code=404, detail="Profil pharmacie non trouvé")

    garde = db.query(PharmacieGarde).filter(
        PharmacieGarde.id == garde_id,
        PharmacieGarde.pharmacie_id == pharmacie.id,
    ).first()
    if not garde:
        raise HTTPException(status_code=404, detail="Période de garde non trouvée")

    db.delete(garde)
    db.commit()
    return {"message": "Période de garde supprimée"}


@router.get("/garde")
def get_on_duty_pharmacies(
    db: Session = Depends(get_db)
):
    """Retourner les pharmacies approuvées dont une période de garde est active."""
    now = datetime.now()
    rows = db.query(
        Pharmacie,
        PharmacieGarde.date_debut,
        PharmacieGarde.date_fin,
        func.ST_Y(Pharmacie.localisation).label("latitude"),
        func.ST_X(Pharmacie.localisation).label("longitude")
    ).join(User, Pharmacie.user_id == User.id).join(
        PharmacieGarde, PharmacieGarde.pharmacie_id == Pharmacie.id
    ).filter(
        User.status == UserStatus.APPROVED,
        PharmacieGarde.date_debut <= now,
        PharmacieGarde.date_fin >= now,
    ).all()

    return [
        {
            "id": pharmacie.id,
            "nom": pharmacie.nom,
            "adresse": pharmacie.adresse,
            "telephone": pharmacie.telephone,
            "is_open": pharmacie.is_open,
            "de_garde": True,
            "date_debut": date_debut,
            "date_fin": date_fin,
            "latitude": float(latitude) if latitude is not None else None,
            "longitude": float(longitude) if longitude is not None else None,
        }
        for pharmacie, date_debut, date_fin, latitude, longitude in rows
    ]

# @router.get("/", response_model=List[PharmacieResponse])
# def get_pharmacies(
#     limit: int = Query(100, ge=1, le=500),
#     offset: int = Query(0, ge=0),
#     db: Session = Depends(get_db)
# ):
#     """Obtenir la liste des pharmacies (uniquement approuvées)"""
#     return db.query(Pharmacie).join(User).filter(
#         User.status == UserStatus.APPROVED
#     ).offset(offset).limit(limit).all()

@router.get("/", response_model=List[PharmacieResponse])
def get_pharmacies(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Obtenir la liste des pharmacies approuvées avec leurs coordonnées GPS"""

    rows = (
        db.query(
            Pharmacie,
            func.ST_Y(Pharmacie.localisation).label("latitude"),
            func.ST_X(Pharmacie.localisation).label("longitude")
        )
        .join(User, Pharmacie.user_id == User.id)
        .filter(User.status == UserStatus.APPROVED)
        .offset(offset)
        .limit(limit)
        .all()
    )

    result = []

    for pharmacie, latitude, longitude in rows:

        result.append(
            PharmacieResponse(
                id=pharmacie.id,
                user_id=pharmacie.user_id,
                nom=pharmacie.nom,
                adresse=pharmacie.adresse,
                telephone=pharmacie.telephone,

                latitude=float(latitude) if latitude is not None else None,
                longitude=float(longitude) if longitude is not None else None,

                is_open=pharmacie.is_open,
                user=pharmacie.user
            )
        )

    return result

# @router.get("/nearby", response_model=List[dict])
# def get_nearby_pharmacies(
#     latitude: float,
#     longitude: float,
#     radius: float = Query(10.0, description="Rayon en km"),
#     db: Session = Depends(get_db)
# ):
#     """Trouver les pharmacies proches d'une position"""
#     from sqlalchemy import func
    
#     user_point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
    
#     pharmacies = db.query(Pharmacie).join(User).filter(
#         User.status == UserStatus.APPROVED,
#         Pharmacie.localisation.is_not(None),
#         ST_Distance(
#             ST_Transform(Pharmacie.localisation, 3857),
#             ST_Transform(user_point, 3857)
#         ) <= radius * 1000
#     ).all()
    
#     result = []
#     for p in pharmacies:
#         distance = db.execute(
#             ST_Distance(
#                 ST_Transform(p.localisation, 3857),
#                 ST_Transform(user_point, 3857)
#             ) / 1000
#         ).scalar()
        
#         point = db.execute(func.ST_AsText(p.localisation)).scalar()
#         if point:
#             coords = point.replace("POINT(", "").replace(")", "").split()
#             longitude_val = float(coords[0])
#             latitude_val = float(coords[1])
#         else:
#             latitude_val = None
#             longitude_val = None
        
#         result.append({
#             "id": p.id,
#             "nom": p.nom,
#             "adresse": p.adresse,
#             "telephone": p.telephone,
#             "is_open": p.is_open,
#             "latitude": latitude_val,
#             "longitude": longitude_val,
#             "distance": round(distance if distance else 0, 2)
#         })
    
#     return sorted(result, key=lambda x: x["distance"])
@router.get("/nearby", response_model=List[dict])
def get_nearby_pharmacies(
    latitude: float,
    longitude: float,
    radius: float = Query(10.0, description="Rayon en km"),
    db: Session = Depends(get_db)
):
    """Trouver les pharmacies proches d'une position."""

    user_point = ST_SetSRID(
        ST_MakePoint(longitude, latitude),
        4326
    )

    distance = (
        func.ST_Distance(
            cast(Pharmacie.localisation, Geography),
            cast(user_point, Geography)
        ) / 1000
    ).label("distance")

    rows = (
        db.query(
            Pharmacie,
            func.ST_Y(Pharmacie.localisation).label("latitude"),
            func.ST_X(Pharmacie.localisation).label("longitude"),
            distance
        )
        .join(User, Pharmacie.user_id == User.id)
        .filter(
            User.status == UserStatus.APPROVED,
            Pharmacie.localisation.isnot(None)
        )
        .filter(
            func.ST_DWithin(
                cast(Pharmacie.localisation, Geography),
                cast(user_point, Geography),
                radius * 1000
            )
        )
        .order_by(distance)
        .all()
    )

    result = []

    for p, lat, lng, dist in rows:
        result.append({
            "id": p.id,
            "nom": p.nom,
            "adresse": p.adresse,
            "telephone": p.telephone,
            "is_open": p.is_open,
            "latitude": float(lat) if lat is not None else None,
            "longitude": float(lng) if lng is not None else None,
            "distance": round(float(dist), 2) if dist is not None else None
        })

    return result

# @router.get("/garde", response_model=List[dict])
# def get_pharmacies_de_garde(
#     db: Session = Depends(get_db)
# ):
#     """Obtenir les pharmacies de garde actuelles"""
#     from sqlalchemy import func
#     from datetime import datetime
    
#     now = datetime.now()
    
#     pharmacies = db.query(Pharmacie).join(
#         PharmacieGarde, Pharmacie.id == PharmacieGarde.pharmacie_id
#     ).join(User).filter(
#         User.status == UserStatus.APPROVED,
#         PharmacieGarde.date_debut <= now,
#         PharmacieGarde.date_fin >= now
#     ).all()
    
#     result = []
#     for p in pharmacies:
#         point = db.execute(func.ST_AsText(p.localisation)).scalar()
#         if point:
#             coords = point.replace("POINT(", "").replace(")", "").split()
#             longitude_val = float(coords[0])
#             latitude_val = float(coords[1])
#         else:
#             latitude_val = None
#             longitude_val = None
        
#         result.append({
#             "id": p.id,
#             "nom": p.nom,
#             "adresse": p.adresse,
#             "telephone": p.telephone,
#             "latitude": latitude_val,
#             "longitude": longitude_val,
#             "is_open": p.is_open
#         })
    
#     return result
