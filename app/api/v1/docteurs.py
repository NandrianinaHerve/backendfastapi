from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint, ST_Distance, ST_Transform

from ...core.database import get_db
from ...core.dependencies import require_docteur, require_admin
from ...core.security import get_password_hash
from ...models.user import User, UserRole, UserStatus
from ...models.docteur import Docteur
from ...models.specialite import Specialite
from ...schemas.docteur import DocteurCreate, DocteurResponse, DocteurUpdate
from ...schemas.user import UserCreate

router = APIRouter(prefix="/docteurs", tags=["Docteurs"])

@router.post("/register", response_model=DocteurResponse)
def register_docteur(
    docteur_data: DocteurCreate,
    db: Session = Depends(get_db)
):
    """Inscription d'un nouveau docteur (en attente de validation)"""
    # Vérifier si l'email ou téléphone existe déjà
    existing_user = db.query(User).filter(
        (User.email == docteur_data.user.email) | 
        (User.telephone == docteur_data.user.telephone)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email ou téléphone déjà utilisé"
        )
    
    # Vérifier la spécialité
    specialite = db.query(Specialite).filter(Specialite.id == docteur_data.specialite_id).first()
    if not specialite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spécialité non trouvée"
        )
    
    # Créer l'utilisateur
    user = User(
        nom=docteur_data.user.nom,
        prenom=docteur_data.user.prenom,
        email=docteur_data.user.email,
        telephone=docteur_data.user.telephone,
        password=get_password_hash(docteur_data.user.password),
        role=UserRole.DOCTEUR,
        status=UserStatus.PENDING  # En attente de validation
    )
    db.add(user)
    db.flush()
    
    # Créer le docteur
    docteur = Docteur(
        user_id=user.id,
        specialite_id=docteur_data.specialite_id,
        adresse=docteur_data.adresse,
        cabinet=docteur_data.cabinet,
        consultation_price=docteur_data.consultation_price,
        experience_years=docteur_data.experience_years,
        bio=docteur_data.bio
    )
    
    if docteur_data.latitude and docteur_data.longitude:
        docteur.localisation = ST_SetSRID(
            ST_MakePoint(docteur_data.longitude, docteur_data.latitude),
            4326
        )
    
    db.add(docteur)
    db.commit()
    db.refresh(docteur)
    return docteur

@router.get("/me", response_model=DocteurResponse)
def get_my_docteur_profile(
    current_user: User = Depends(require_docteur),
    db: Session = Depends(get_db)
):
    """Obtenir le profil du docteur connecté"""
    docteur = db.query(Docteur).filter(Docteur.user_id == current_user.id).first()
    if not docteur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil docteur non trouvé"
        )
    return docteur

@router.put("/me", response_model=DocteurResponse)
def update_my_docteur_profile(
    docteur_update: DocteurUpdate,
    current_user: User = Depends(require_docteur),
    db: Session = Depends(get_db)
):
    """Mettre à jour le profil du docteur connecté"""
    docteur = db.query(Docteur).filter(Docteur.user_id == current_user.id).first()
    if not docteur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil docteur non trouvé"
        )
    
    if docteur_update.specialite_id:
        specialite = db.query(Specialite).filter(Specialite.id == docteur_update.specialite_id).first()
        if not specialite:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Spécialité non trouvée"
            )
        docteur.specialite_id = docteur_update.specialite_id
    
    if docteur_update.adresse is not None:
        docteur.adresse = docteur_update.adresse
    if docteur_update.cabinet is not None:
        docteur.cabinet = docteur_update.cabinet
    if docteur_update.consultation_price is not None:
        docteur.consultation_price = docteur_update.consultation_price
    if docteur_update.experience_years is not None:
        docteur.experience_years = docteur_update.experience_years
    if docteur_update.bio is not None:
        docteur.bio = docteur_update.bio
    
    if docteur_update.latitude is not None and docteur_update.longitude is not None:
        docteur.localisation = ST_SetSRID(
            ST_MakePoint(docteur_update.longitude, docteur_update.latitude),
            4326
        )
    
    db.commit()
    db.refresh(docteur)
    return docteur

@router.patch("/me/availability")
def toggle_my_availability(
    is_available: bool,
    current_user: User = Depends(require_docteur),
    db: Session = Depends(get_db)
):
    """Activer/désactiver la disponibilité du docteur connecté"""
    docteur = db.query(Docteur).filter(Docteur.user_id == current_user.id).first()
    if not docteur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil docteur non trouvé"
        )
    
    docteur.is_available = is_available
    db.commit()
    return {
        "message": f"Disponibilité {'activée' if is_available else 'désactivée'}",
        "is_available": is_available
    }

@router.get("/", response_model=List[DocteurResponse])
def get_docteurs(
    specialite_id: Optional[int] = None,
    available: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Obtenir la liste des docteurs (uniquement approuvés)"""
    query = db.query(Docteur).join(User).filter(User.status == UserStatus.APPROVED)
    
    if specialite_id:
        query = query.filter(Docteur.specialite_id == specialite_id)
    
    if available is not None:
        query = query.filter(Docteur.is_available == available)
    
    return query.offset(offset).limit(limit).all()

@router.get("/nearby", response_model=List[dict])
def get_nearby_docteurs(
    latitude: float,
    longitude: float,
    radius: float = Query(10.0, description="Rayon en km"),
    specialite_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Trouver les docteurs proches d'une position (uniquement approuvés)"""
    from sqlalchemy import func
    
    user_point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
    
    query = db.query(Docteur).join(User).filter(
        User.status == UserStatus.APPROVED,
        Docteur.localisation.is_not(None),
        Docteur.is_available == True,
        ST_Distance(
            ST_Transform(Docteur.localisation, 3857),
            ST_Transform(user_point, 3857)
        ) <= radius * 1000
    )
    
    if specialite_id:
        query = query.filter(Docteur.specialite_id == specialite_id)
    
    docteurs = query.all()
    
    result = []
    for d in docteurs:
        distance = db.execute(
            ST_Distance(
                ST_Transform(d.localisation, 3857),
                ST_Transform(user_point, 3857)
            ) / 1000
        ).scalar()
        
        point = db.execute(func.ST_AsText(d.localisation)).scalar()
        if point:
            coords = point.replace("POINT(", "").replace(")", "").split()
            longitude_val = float(coords[0])
            latitude_val = float(coords[1])
        else:
            latitude_val = None
            longitude_val = None
        
        result.append({
            "id": d.id,
            "nom": d.user.nom,
            "prenom": d.user.prenom,
            "specialite": d.specialite.nom if d.specialite else None,
            "adresse": d.adresse,
            "cabinet": d.cabinet,
            "is_available": d.is_available,
            "consultation_price": d.consultation_price,
            "experience_years": d.experience_years,
            "latitude": latitude_val,
            "longitude": longitude_val,
            "distance": round(distance if distance else 0, 2)
        })
    
    return sorted(result, key=lambda x: x["distance"])