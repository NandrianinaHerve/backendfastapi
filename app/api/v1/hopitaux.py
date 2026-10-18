from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint, ST_Distance, ST_Transform
from geoalchemy2.types import Geography
from sqlalchemy import func,cast

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
    """Inscription d'un nouvel hôpital (en attente de validation)."""

    # =========================================================
    # 1. Vérifier si l'email ou le téléphone existe déjà
    # =========================================================

    existing_user = db.query(User).filter(
        (User.email == hopital_data.user.email) |
        (User.telephone == hopital_data.user.telephone)
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
        nom=hopital_data.user.nom,
        prenom=hopital_data.user.prenom,
        email=hopital_data.user.email,
        telephone=hopital_data.user.telephone,
        password=get_password_hash(
            hopital_data.user.password
        ),
        role=UserRole.HOPITAL,
        status=UserStatus.PENDING
    )

    db.add(user)

    # Récupérer user.id
    db.flush()

    # =========================================================
    # 3. Créer l'hôpital
    # =========================================================

    hopital = Hopital(
        user_id=user.id,
        nom=hopital_data.nom,
        adresse=hopital_data.adresse,
        telephone=hopital_data.telephone,
        services=hopital_data.services,
        is_open=False
    )

    # =========================================================
    # 4. Enregistrer la localisation PostGIS
    # =========================================================

    if (
        hopital_data.latitude is not None
        and hopital_data.longitude is not None
    ):
        hopital.localisation = ST_SetSRID(
            ST_MakePoint(
                hopital_data.longitude,
                hopital_data.latitude
            ),
            4326
        )

    db.add(hopital)

    # =========================================================
    # 5. Sauvegarder
    # =========================================================

    db.commit()

    db.refresh(user)
    db.refresh(hopital)

    # =========================================================
    # 6. Récupérer les coordonnées depuis PostGIS
    # =========================================================

    coordinates = (
        db.query(
            func.ST_Y(
                Hopital.localisation
            ).label("latitude"),

            func.ST_X(
                Hopital.localisation
            ).label("longitude")
        )
        .filter(
            Hopital.id == hopital.id
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

    return HopitalResponse(
        id=hopital.id,
        user_id=hopital.user_id,
        nom=hopital.nom,
        adresse=hopital.adresse,
        telephone=hopital.telephone,
        services=hopital.services,
        is_open=hopital.is_open,
        latitude=latitude,
        longitude=longitude,
        user=hopital.user
    )

# @router.get("/me", response_model=HopitalResponse)
# def get_my_hopital_profile(
#     current_user: User = Depends(require_hopital),
#     db: Session = Depends(get_db)
# ):
#     """Obtenir le profil de l'hôpital connecté"""
#     hopital = db.query(Hopital).filter(Hopital.user_id == current_user.id).first()
#     if not hopital:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Profil hôpital non trouvé"
#         )
#     return hopital

@router.get("/me", response_model=HopitalResponse)
def get_my_hopital_profile(
    current_user: User = Depends(require_hopital),
    db: Session = Depends(get_db)
):
    """Obtenir le profil de l'hôpital connecté avec coordonnées GPS"""

    result = (
        db.query(
            Hopital,
            func.ST_Y(Hopital.localisation).label("latitude"),
            func.ST_X(Hopital.localisation).label("longitude")
        )
        .filter(Hopital.user_id == current_user.id)
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil hôpital non trouvé"
        )

    hopital, latitude, longitude = result

    return HopitalResponse(
        id=hopital.id,
        user_id=hopital.user_id,
        nom=hopital.nom,
        adresse=hopital.adresse,
        telephone=hopital.telephone,
        services=hopital.services,
        is_open=hopital.is_open,

        latitude=float(latitude)
        if latitude is not None else None,

        longitude=float(longitude)
        if longitude is not None else None,

        user=hopital.user
    )

# @router.put("/me", response_model=HopitalResponse)
# def update_my_hopital_profile(
#     hopital_update: HopitalUpdate,
#     current_user: User = Depends(require_hopital),
#     db: Session = Depends(get_db)
# ):
#     """Mettre à jour le profil de l'hôpital connecté"""
#     hopital = db.query(Hopital).filter(Hopital.user_id == current_user.id).first()
#     if not hopital:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Profil hôpital non trouvé"
#         )
    
#     if hopital_update.nom:
#         hopital.nom = hopital_update.nom
#     if hopital_update.adresse is not None:
#         hopital.adresse = hopital_update.adresse
#     if hopital_update.telephone is not None:
#         hopital.telephone = hopital_update.telephone
#     if hopital_update.services is not None:
#         hopital.services = hopital_update.services
    
#     if hopital_update.latitude is not None and hopital_update.longitude is not None:
#         hopital.localisation = ST_SetSRID(
#             ST_MakePoint(hopital_update.longitude, hopital_update.latitude),
#             4326
#         )
    
#     db.commit()
#     db.refresh(hopital)
#     return hopital
@router.put("/me", response_model=HopitalResponse)
def update_my_hopital_profile(
    hopital_update: HopitalUpdate,
    current_user: User = Depends(require_hopital),
    db: Session = Depends(get_db)
):
    """Mettre à jour le profil de l'hôpital connecté"""

    hopital = (
        db.query(Hopital)
        .filter(Hopital.user_id == current_user.id)
        .first()
    )

    if not hopital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil hôpital non trouvé"
        )

    # Nom
    if hopital_update.nom is not None:
        hopital.nom = hopital_update.nom

    # Adresse
    if hopital_update.adresse is not None:
        hopital.adresse = hopital_update.adresse

    # Téléphone
    if hopital_update.telephone is not None:
        hopital.telephone = hopital_update.telephone

    # Services
    if hopital_update.services is not None:
        hopital.services = hopital_update.services

    # Localisation GPS
    if (
        hopital_update.latitude is not None
        and hopital_update.longitude is not None
    ):
        hopital.localisation = ST_SetSRID(
            ST_MakePoint(
                hopital_update.longitude,
                hopital_update.latitude
            ),
            4326
        )

    db.commit()
    db.refresh(hopital)

    # Récupérer les coordonnées depuis PostGIS
    coordinates = (
        db.query(
            func.ST_Y(Hopital.localisation).label("latitude"),
            func.ST_X(Hopital.localisation).label("longitude")
        )
        .filter(Hopital.id == hopital.id)
        .first()
    )

    latitude = coordinates.latitude if coordinates else None
    longitude = coordinates.longitude if coordinates else None

    return HopitalResponse(
        id=hopital.id,
        user_id=hopital.user_id,
        nom=hopital.nom,
        adresse=hopital.adresse,
        telephone=hopital.telephone,
        services=hopital.services,
        is_open=hopital.is_open,

        latitude=float(latitude)
        if latitude is not None else None,

        longitude=float(longitude)
        if longitude is not None else None,

        user=hopital.user
    )

# @router.get("/", response_model=List[HopitalResponse])
# def get_hopitaux(
#     limit: int = Query(100, ge=1, le=500),
#     offset: int = Query(0, ge=0),
#     db: Session = Depends(get_db)
# ):
#     """Obtenir la liste des hôpitaux (uniquement approuvés)"""
#     return db.query(Hopital).join(User).filter(
#         User.status == UserStatus.APPROVED
#     ).offset(offset).limit(limit).all()
@router.get("/", response_model=List[HopitalResponse])
def get_hopitaux(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Obtenir la liste des hôpitaux approuvés avec coordonnées GPS"""

    rows = (
        db.query(
            Hopital,
            func.ST_Y(Hopital.localisation).label("latitude"),
            func.ST_X(Hopital.localisation).label("longitude")
        )
        .join(User, Hopital.user_id == User.id)
        .filter(User.status == UserStatus.APPROVED)
        .offset(offset)
        .limit(limit)
        .all()
    )

    result = []

    for hopital, latitude, longitude in rows:

        result.append(
            HopitalResponse(
                id=hopital.id,
                user_id=hopital.user_id,
                nom=hopital.nom,
                adresse=hopital.adresse,
                telephone=hopital.telephone,
                services=hopital.services,
                is_open=hopital.is_open,

                latitude=float(latitude)
                if latitude is not None else None,

                longitude=float(longitude)
                if longitude is not None else None,

                user=hopital.user
            )
        )

    return result

# @router.get("/nearby", response_model=List[dict])
# def get_nearby_hopitaux(
#     latitude: float,
#     longitude: float,
#     radius: float = Query(10.0, description="Rayon en km"),
#     db: Session = Depends(get_db)
# ):
#     """Trouver les hôpitaux proches d'une position"""
#     from sqlalchemy import func
    
#     user_point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
    
#     hopitaux = db.query(Hopital).join(User).filter(
#         User.status == UserStatus.APPROVED,
#         Hopital.localisation.is_not(None),
#         ST_Distance(
#             ST_Transform(Hopital.localisation, 3857),
#             ST_Transform(user_point, 3857)
#         ) <= radius * 1000
#     ).all()
    
#     result = []
#     for h in hopitaux:
#         distance = db.execute(
#             ST_Distance(
#                 ST_Transform(h.localisation, 3857),
#                 ST_Transform(user_point, 3857)
#             ) / 1000
#         ).scalar()
        
#         point = db.execute(func.ST_AsText(h.localisation)).scalar()
#         if point:
#             coords = point.replace("POINT(", "").replace(")", "").split()
#             longitude_val = float(coords[0])
#             latitude_val = float(coords[1])
#         else:
#             latitude_val = None
#             longitude_val = None
        
#         result.append({
#             "id": h.id,
#             "nom": h.nom,
#             "adresse": h.adresse,
#             "telephone": h.telephone,
#             "services": h.services,
#             "is_open": h.is_open,
#             "latitude": latitude_val,
#             "longitude": longitude_val,
#             "distance": round(distance if distance else 0, 2)
#         })
    
#     return sorted(result, key=lambda x: x["distance"])
@router.get("/nearby", response_model=List[dict])
def get_nearby_hopitaux(
    latitude: float,
    longitude: float,
    radius: float = Query(10.0, description="Rayon en km"),
    db: Session = Depends(get_db)
):
    """Trouver les hôpitaux proches d'une position."""

    user_point = ST_SetSRID(
        ST_MakePoint(longitude, latitude),
        4326
    )

    distance = (
        func.ST_Distance(
            cast(Hopital.localisation, Geography),
            cast(user_point, Geography)
        ) / 1000
    ).label("distance")

    rows = (
        db.query(
            Hopital,
            func.ST_Y(Hopital.localisation).label("latitude"),
            func.ST_X(Hopital.localisation).label("longitude"),
            distance
        )
        .join(User, Hopital.user_id == User.id)
        .filter(
            User.status == UserStatus.APPROVED,
            Hopital.localisation.isnot(None)
        )
        .filter(
            func.ST_DWithin(
                cast(Hopital.localisation, Geography),
                cast(user_point, Geography),
                radius * 1000
            )
        )
        .order_by(distance)
        .all()
    )

    result = []

    for h, lat, lng, dist in rows:
        result.append({
            "id": h.id,
            "nom": h.nom,
            "adresse": h.adresse,
            "telephone": h.telephone,
            "services": h.services,
            "is_open": h.is_open,
            "latitude": float(lat) if lat is not None else None,
            "longitude": float(lng) if lng is not None else None,
            "distance": round(float(dist), 2) if dist is not None else None
        })

    return result