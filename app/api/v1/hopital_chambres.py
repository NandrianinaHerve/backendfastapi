from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json

from ...core.database import get_db
from ...core.dependencies import get_current_user, require_hopital, require_patient
from ...models.user import User, UserStatus
from ...models.hopital import Hopital
from ...models.hopital_chambre import Chambre, Hospitalisation
from ...models.patient import Patient
from ...models.notification import Notification
from ...schemas.hopital_chambre import (
    ChambreCreate,
    ChambreUpdate,
    ChambreResponse,
    ChambreStats,
    HospitalisationCreate,
    HospitalisationUpdate,
    HospitalisationResponse,
    HospitalisationWithChambre,
    RechercheFamille,
    ResultatRechercheFamille
)

router = APIRouter(prefix="/hopitaux/chambres", tags=["Chambres"])


# ============================================
# HELPER NOTIFICATION
# ============================================
def create_notification(db, user_id, title, message, type, data=None):
    """Créer une notification"""
    try:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type,
            data=json.dumps(data) if data else None,
            is_read=False
        )
        db.add(notif)
        return notif
    except Exception as e:
        print(f"⚠️ Erreur notification: {e}")
        return None


# ============================================
# GESTION DES CHAMBRES (Hôpital)
# ============================================

@router.post("/", response_model=ChambreResponse)
def create_chambre(
    chambre_data: ChambreCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hopital)
):
    """Créer une chambre (Hôpital)"""
    
    hopital = db.query(Hopital).filter(Hopital.user_id == current_user.id).first()
    if not hopital:
        raise HTTPException(status_code=404, detail="Hôpital non trouvé")
    
    existing = db.query(Chambre).filter(
        Chambre.hopital_id == hopital.id,
        Chambre.numero == chambre_data.numero
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"La chambre '{chambre_data.numero}' existe déjà"
        )
    
    chambre = Chambre(hopital_id=hopital.id, **chambre_data.dict())
    db.add(chambre)
    db.commit()
    db.refresh(chambre)
    return chambre


@router.post("/batch")
def create_chambres_batch(
    nombre: int = Query(..., ge=1, le=50),
    prefixe: str = Query("CH"),
    etage: str = Query("0"),
    aile: Optional[str] = None,
    capacite_lits: int = Query(1, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hopital)
):
    """Créer plusieurs chambres (Hôpital)"""
    
    hopital = db.query(Hopital).filter(Hopital.user_id == current_user.id).first()
    if not hopital:
        raise HTTPException(status_code=404, detail="Hôpital non trouvé")
    
    created = []
    for i in range(1, nombre + 1):
        numero = f"{prefixe}-{etage}{i:02d}"
        
        existing = db.query(Chambre).filter(
            Chambre.hopital_id == hopital.id,
            Chambre.numero == numero
        ).first()
        if existing:
            continue
        
        chambre = Chambre(
            hopital_id=hopital.id,
            numero=numero,
            etage=etage,
            aile=aile,
            capacite_lits=capacite_lits
        )
        db.add(chambre)
        created.append(numero)
    
    db.commit()
    return {"message": f"{len(created)} chambre(s) créée(s)", "numeros": created}


@router.get("/me", response_model=List[ChambreResponse])
def get_my_chambres(
    is_disponible: Optional[bool] = None,
    etage: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hopital)
):
    """Voir les chambres de son hôpital"""
    
    hopital = db.query(Hopital).filter(Hopital.user_id == current_user.id).first()
    if not hopital:
        raise HTTPException(status_code=404, detail="Hôpital non trouvé")
    
    query = db.query(Chambre).filter(Chambre.hopital_id == hopital.id)
    
    if is_disponible is not None:
        query = query.filter(Chambre.is_disponible == is_disponible)
    if etage:
        query = query.filter(Chambre.etage == etage)
    
    return query.order_by(Chambre.numero).offset(offset).limit(limit).all()


@router.get("/me/stats", response_model=ChambreStats)
def get_my_chambre_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hopital)
):
    """Statistiques des chambres"""
    
    hopital = db.query(Hopital).filter(Hopital.user_id == current_user.id).first()
    if not hopital:
        raise HTTPException(status_code=404, detail="Hôpital non trouvé")
    
    chambres = db.query(Chambre).filter(Chambre.hopital_id == hopital.id).all()
    
    total = len(chambres)
    occupees = sum(1 for c in chambres if not c.is_disponible)
    disponibles = total - occupees
    lits_total = sum(c.capacite_lits for c in chambres)
    lits_occupes = sum(c.nb_lits_occupes for c in chambres)
    
    taux = (lits_occupes / lits_total * 100) if lits_total > 0 else 0
    
    return {
        "total": total,
        "disponibles": disponibles,
        "occupees": occupees,
        "lits_total": lits_total,
        "lits_occupes": lits_occupes,
        "taux_occupation": round(taux, 2)
    }


@router.put("/{chambre_id}", response_model=ChambreResponse)
def update_chambre(
    chambre_id: int,
    update_data: ChambreUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hopital)
):
    """Mettre à jour une chambre"""
    
    hopital = db.query(Hopital).filter(Hopital.user_id == current_user.id).first()
    if not hopital:
        raise HTTPException(status_code=404, detail="Hôpital non trouvé")
    
    chambre = db.query(Chambre).filter(
        Chambre.id == chambre_id,
        Chambre.hopital_id == hopital.id
    ).first()
    if not chambre:
        raise HTTPException(status_code=404, detail="Chambre non trouvée")
    
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(chambre, field, value)
    
    db.commit()
    db.refresh(chambre)
    return chambre


@router.delete("/{chambre_id}")
def delete_chambre(
    chambre_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hopital)
):
    """Supprimer une chambre"""
    
    hopital = db.query(Hopital).filter(Hopital.user_id == current_user.id).first()
    if not hopital:
        raise HTTPException(status_code=404, detail="Hôpital non trouvé")
    
    chambre = db.query(Chambre).filter(
        Chambre.id == chambre_id,
        Chambre.hopital_id == hopital.id
    ).first()
    if not chambre:
        raise HTTPException(status_code=404, detail="Chambre non trouvée")
    
    # Vérifier qu'aucune hospitalisation active
    active = db.query(Hospitalisation).filter(
        Hospitalisation.chambre_id == chambre_id,
        Hospitalisation.is_active == True
    ).first()
    if active:
        raise HTTPException(
            status_code=400,
            detail="Impossible de supprimer : chambre occupée"
        )
    
    db.delete(chambre)
    db.commit()
    return {"message": "Chambre supprimée avec succès"}


# ============================================
# AFFECTER UN PATIENT (Hôpital)
# ============================================

@router.post("/hospitalisations", response_model=HospitalisationResponse)
def create_hospitalisation(
    hosp_data: HospitalisationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hopital)
):
    """Affecter un patient à une chambre (Hôpital)"""
    
    hopital = db.query(Hopital).filter(Hopital.user_id == current_user.id).first()
    if not hopital:
        raise HTTPException(status_code=404, detail="Hôpital non trouvé")
    
    chambre = db.query(Chambre).filter(
        Chambre.id == hosp_data.chambre_id,
        Chambre.hopital_id == hopital.id
    ).first()
    if not chambre:
        raise HTTPException(status_code=404, detail="Chambre non trouvée")
    
    if not chambre.is_disponible:
        raise HTTPException(status_code=400, detail="Chambre non disponible")
    
    if chambre.nb_lits_occupes >= chambre.capacite_lits:
        raise HTTPException(status_code=400, detail="Chambre pleine")
    
    if hosp_data.patient_id:
        patient = db.query(Patient).filter(Patient.id == hosp_data.patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient non trouvé")
    
    hosp = Hospitalisation(hopital_id=hopital.id, **hosp_data.dict())
    db.add(hosp)
    db.flush()
    
    # Mettre à jour la chambre
    chambre.nb_lits_occupes += 1
    if chambre.nb_lits_occupes >= chambre.capacite_lits:
        chambre.is_disponible = False
    
    # Notification à l'hôpital
    create_notification(
        db=db,
        user_id=current_user.id,
        title="🏥 Nouvelle hospitalisation",
        message=(
            f"{hosp.patient_nom} {hosp.patient_prenom} a été affecté(e) "
            f"à la chambre {chambre.numero} (Étage {chambre.etage or 'N/A'})"
        ),
        type="hospitalisation",
        data={
            "hospitalisation_id": hosp.id,
            "chambre_numero": chambre.numero,
            "patient_nom": hosp.patient_nom
        }
    )
    
    # Notification si chambre pleine
    if chambre.nb_lits_occupes >= chambre.capacite_lits:
        create_notification(
            db=db,
            user_id=current_user.id,
            title="⚠️ Chambre pleine",
            message=f"La chambre {chambre.numero} est maintenant pleine",
            type="chambre_pleine",
            data={"chambre_numero": chambre.numero}
        )
    
    db.commit()
    db.refresh(hosp)
    return hosp


@router.get("/hospitalisations/me", response_model=List[HospitalisationWithChambre])
def get_my_hospitalisations(
    is_active: Optional[bool] = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hopital)
):
    """Voir les hospitalisations de son hôpital"""
    
    hopital = db.query(Hopital).filter(Hopital.user_id == current_user.id).first()
    if not hopital:
        raise HTTPException(status_code=404, detail="Hôpital non trouvé")
    
    query = db.query(Hospitalisation).filter(
        Hospitalisation.hopital_id == hopital.id
    )
    
    if is_active is not None:
        query = query.filter(Hospitalisation.is_active == is_active)
    
    hospitalisations = query.order_by(Hospitalisation.date_entree.desc()).all()
    
    result = []
    for h in hospitalisations:
        chambre = db.query(Chambre).filter(Chambre.id == h.chambre_id).first()
        result.append({
            "id": h.id,
            "hopital_id": h.hopital_id,
            "chambre_id": h.chambre_id,
            "patient_id": h.patient_id,
            "patient_nom": h.patient_nom,
            "patient_prenom": h.patient_prenom,
            "patient_telephone": h.patient_telephone,
            "contact_nom": h.contact_nom,
            "contact_telephone": h.contact_telephone,
            "contact_relation": h.contact_relation,
            "date_entree": h.date_entree,
            "date_sortie_effective": h.date_sortie_effective,
            "visites_autorisees": h.visites_autorisees,
            "heures_visite": h.heures_visite,
            "is_active": h.is_active,
            "created_at": h.created_at,
            "updated_at": h.updated_at,
            "chambre_numero": chambre.numero if chambre else None,
            "chambre_etage": chambre.etage if chambre else None,
            "chambre_aile": chambre.aile if chambre else None,
            "hopital_nom": hopital.nom
        })
    
    return result


# ============================================
# LIBÉRER UNE CHAMBRE (Hôpital)
# ============================================

@router.put("/hospitalisations/{hosp_id}/sortie", response_model=HospitalisationResponse)
def enregistrer_sortie(
    hosp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hopital)
):
    """Libérer une chambre (sortie du patient)"""
    
    hopital = db.query(Hopital).filter(Hopital.user_id == current_user.id).first()
    if not hopital:
        raise HTTPException(status_code=404, detail="Hôpital non trouvé")
    
    hosp = db.query(Hospitalisation).filter(
        Hospitalisation.id == hosp_id,
        Hospitalisation.hopital_id == hopital.id,
        Hospitalisation.is_active == True
    ).first()
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospitalisation non trouvée")
    
    chambre = db.query(Chambre).filter(Chambre.id == hosp.chambre_id).first()
    
    hosp.is_active = False
    hosp.date_sortie_effective = datetime.utcnow()
    
    if chambre:
        chambre.nb_lits_occupes = max(0, chambre.nb_lits_occupes - 1)
        chambre.is_disponible = True
    
    # Notification
    create_notification(
        db=db,
        user_id=current_user.id,
        title="✅ Sortie enregistrée",
        message=(
            f"{hosp.patient_nom} {hosp.patient_prenom} est sorti(e). "
            f"Chambre {chambre.numero if chambre else 'N/A'} libérée."
        ),
        type="sortie",
        data={"hospitalisation_id": hosp.id}
    )
    
    db.commit()
    db.refresh(hosp)
    return hosp


# ============================================
# RECHERCHE FAMILLE (Patient)
# ============================================

@router.post("/recherche-famille", response_model=ResultatRechercheFamille)
def rechercher_famille(
    recherche: RechercheFamille,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient)
):
    """
    Rechercher un membre de famille hospitalisé
    
    🔒 Retourne uniquement : nom + chambre + étage + heures de visite
    """
    
    query = db.query(Hospitalisation).filter(
        Hospitalisation.is_active == True,
        Hospitalisation.patient_nom.ilike(f"%{recherche.nom}%")
    )
    
    if recherche.prenom:
        query = query.filter(Hospitalisation.patient_prenom.ilike(f"%{recherche.prenom}%"))
    
    hospitalisations = query.all()
    
    if not hospitalisations:
        return {
            "trouve": False,
            "message": "Aucun patient trouvé avec ces informations"
        }
    
    hosp = hospitalisations[0]
    chambre = db.query(Chambre).filter(Chambre.id == hosp.chambre_id).first()
    hopital = db.query(Hopital).filter(Hopital.id == hosp.hopital_id).first()
    
    return {
        "trouve": True,
        "patient_nom": hosp.patient_nom,
        "patient_prenom": hosp.patient_prenom,
        "hopital_nom": hopital.nom if hopital else None,
        "hopital_adresse": hopital.adresse if hopital else None,
        "hopital_telephone": hopital.telephone if hopital else None,
        "chambre_numero": chambre.numero if chambre else None,
        "chambre_etage": chambre.etage if chambre else None,
        "chambre_aile": chambre.aile if chambre else None,
        "visites_autorisees": hosp.visites_autorisees,
        "heures_visite": hosp.heures_visite,
        "message": "Patient trouvé" if hosp.visites_autorisees else "Patient trouvé - Visites non autorisées"
    }


@router.get("/recherche-famille/{nom}", response_model=List[ResultatRechercheFamille])
def rechercher_famille_par_nom(
    nom: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient)
):
    """Rechercher par nom"""
    
    hospitalisations = db.query(Hospitalisation).filter(
        Hospitalisation.is_active == True,
        Hospitalisation.patient_nom.ilike(f"%{nom}%")
    ).all()
    
    if not hospitalisations:
        return [{"trouve": False, "message": "Aucun patient trouvé"}]
    
    result = []
    for hosp in hospitalisations:
        chambre = db.query(Chambre).filter(Chambre.id == hosp.chambre_id).first()
        hopital = db.query(Hopital).filter(Hopital.id == hosp.hopital_id).first()
        
        result.append({
            "trouve": True,
            "patient_nom": hosp.patient_nom,
            "patient_prenom": hosp.patient_prenom,
            "hopital_nom": hopital.nom if hopital else None,
            "hopital_adresse": hopital.adresse if hopital else None,
            "hopital_telephone": hopital.telephone if hopital else None,
            "chambre_numero": chambre.numero if chambre else None,
            "chambre_etage": chambre.etage if chambre else None,
            "chambre_aile": chambre.aile if chambre else None,
            "visites_autorisees": hosp.visites_autorisees,
            "heures_visite": hosp.heures_visite,
            "message": "Patient trouvé"
        })
    
    return result


# ============================================
# CONSULTATION PUBLIQUE (Patient)
# ============================================

@router.get("/hopital/{hopital_id}", response_model=List[ChambreResponse])
def get_hopital_chambres(
    hopital_id: int,
    is_disponible: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Voir les chambres d'un hôpital (Patient)"""
    
    hopital = db.query(Hopital).filter(Hopital.id == hopital_id).first()
    if not hopital:
        raise HTTPException(status_code=404, detail="Hôpital non trouvé")
    
    query = db.query(Chambre).filter(Chambre.hopital_id == hopital_id)
    
    if is_disponible is not None:
        query = query.filter(Chambre.is_disponible == is_disponible)
    
    return query.order_by(Chambre.numero).all()