import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ...core.database import get_db
from ...core.dependencies import get_current_user, require_docteur
from ...models.docteur import Docteur
from ...models.notification import Notification
from ...models.ordonnance import Ordonnance, OrdonnanceMedicament
from ...models.patient import Patient
from ...models.rendez_vous import AppointmentStatus, RendezVous
from ...models.user import User
from ...schemas.ordonnance import OrdonnanceCreate, OrdonnanceResponse

router = APIRouter(prefix="/ordonnances", tags=["Ordonnances"])


def _ordonnance_response(ordonnance: Ordonnance) -> dict:
    return {
        "id": ordonnance.id,
        "rendez_vous_id": ordonnance.rendez_vous_id,
        "patient_id": ordonnance.patient_id,
        "patient_nom": (
            f"{ordonnance.patient.user.prenom} {ordonnance.patient.user.nom}".strip()
        ),
        "docteur_id": ordonnance.docteur_id,
        "docteur_nom": (
            f"Dr. {ordonnance.docteur.user.prenom} {ordonnance.docteur.user.nom}".strip()
        ),
        "diagnostic": ordonnance.diagnostic,
        "instructions": ordonnance.instructions,
        "medicaments": ordonnance.medicaments,
        "created_at": ordonnance.created_at,
    }


def _with_ordonnance_details(query):
    return query.options(
        joinedload(Ordonnance.patient).joinedload(Patient.user),
        joinedload(Ordonnance.docteur).joinedload(Docteur.user),
        joinedload(Ordonnance.medicaments),
    )


@router.post(
    "/rendez-vous/{rdv_id}",
    response_model=OrdonnanceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ordonnance(
    rdv_id: int,
    ordonnance_data: OrdonnanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_docteur),
):
    """Créer une ordonnance pour un rendez-vous confirmé ou terminé du docteur."""
    docteur = db.query(Docteur).filter(Docteur.user_id == current_user.id).first()
    if not docteur:
        raise HTTPException(status_code=404, detail="Profil docteur non trouvé")

    rdv = db.query(RendezVous).filter(RendezVous.id == rdv_id).first()
    if not rdv:
        raise HTTPException(status_code=404, detail="Rendez-vous non trouvé")
    if rdv.docteur_id != docteur.id:
        raise HTTPException(status_code=403, detail="Ce rendez-vous ne vous appartient pas")
    if rdv.status not in (AppointmentStatus.CONFIRMED, AppointmentStatus.COMPLETED):
        raise HTTPException(
            status_code=409,
            detail="Une ordonnance nécessite un rendez-vous confirmé ou terminé",
        )
    if db.query(Ordonnance.id).filter(Ordonnance.rendez_vous_id == rdv.id).first():
        raise HTTPException(
            status_code=409,
            detail="Une ordonnance existe déjà pour ce rendez-vous",
        )

    ordonnance = Ordonnance(
        rendez_vous_id=rdv.id,
        patient_id=rdv.patient_id,
        docteur_id=docteur.id,
        diagnostic=ordonnance_data.diagnostic,
        instructions=ordonnance_data.instructions,
        medicaments=[
            OrdonnanceMedicament(**medicament.model_dump())
            for medicament in ordonnance_data.medicaments
        ],
    )
    db.add(ordonnance)

    try:
        db.flush()
        db.add(
            Notification(
                user_id=rdv.patient.user_id,
                title="💊 Nouvelle ordonnance",
                message=f"Dr. {current_user.prenom} {current_user.nom} a créé une ordonnance pour votre rendez-vous.",
                type="ordonnance_created",
                data=json.dumps({
                    "ordonnance_id": ordonnance.id,
                    "rendez_vous_id": rdv.id,
                }),
                is_read=False,
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Une ordonnance existe déjà pour ce rendez-vous",
        )

    ordonnance = _with_ordonnance_details(
        db.query(Ordonnance).filter(Ordonnance.id == ordonnance.id)
    ).first()
    return _ordonnance_response(ordonnance)


@router.get("/mes", response_model=List[OrdonnanceResponse])
def get_my_ordonnances(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Historique privé des ordonnances du patient ou du docteur connecté."""
    query = _with_ordonnance_details(db.query(Ordonnance))

    if current_user.role.value == "patient":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Profil patient non trouvé")
        query = query.filter(Ordonnance.patient_id == patient.id)
    elif current_user.role.value == "docteur":
        docteur = db.query(Docteur).filter(Docteur.user_id == current_user.id).first()
        if not docteur:
            raise HTTPException(status_code=404, detail="Profil docteur non trouvé")
        query = query.filter(Ordonnance.docteur_id == docteur.id)
    else:
        raise HTTPException(
            status_code=403,
            detail="Seuls les patients et docteurs peuvent consulter leur historique",
        )

    ordonnances = query.order_by(Ordonnance.created_at.desc(), Ordonnance.id.desc()).all()
    return [_ordonnance_response(ordonnance) for ordonnance in ordonnances]


@router.get("/{ordonnance_id}", response_model=OrdonnanceResponse)
def get_ordonnance(
    ordonnance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ordonnance = _with_ordonnance_details(
        db.query(Ordonnance).filter(Ordonnance.id == ordonnance_id)
    ).first()
    if not ordonnance:
        raise HTTPException(status_code=404, detail="Ordonnance non trouvée")

    is_owner = (
        current_user.role.value == "patient"
        and ordonnance.patient.user_id == current_user.id
    )
    is_prescriber = (
        current_user.role.value == "docteur"
        and ordonnance.docteur.user_id == current_user.id
    )
    if not (is_owner or is_prescriber or current_user.role.value == "admin"):
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    return _ordonnance_response(ordonnance)
