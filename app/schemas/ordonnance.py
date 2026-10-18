from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class OrdonnanceMedicamentCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=255)
    dosage: str = Field(..., min_length=1, max_length=100)
    posologie: str = Field(..., min_length=1, max_length=255)
    duree: str = Field(..., min_length=1, max_length=100)
    quantite: Optional[int] = Field(None, ge=1)
    instructions: Optional[str] = None


class OrdonnanceCreate(BaseModel):
    diagnostic: Optional[str] = None
    instructions: Optional[str] = None
    medicaments: List[OrdonnanceMedicamentCreate] = Field(..., min_length=1)


class OrdonnanceMedicamentResponse(OrdonnanceMedicamentCreate):
    id: int

    class Config:
        from_attributes = True


class OrdonnanceResponse(BaseModel):
    id: int
    rendez_vous_id: int
    patient_id: int
    patient_nom: str
    docteur_id: int
    docteur_nom: str
    diagnostic: Optional[str] = None
    instructions: Optional[str] = None
    medicaments: List[OrdonnanceMedicamentResponse]
    created_at: datetime

    class Config:
        from_attributes = True
