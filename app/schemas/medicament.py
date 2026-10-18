from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
import enum


class StatutCommande(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    CONFIRMEE = "confirmee"
    PRETE = "prete"
    RECUPEREE = "recuperee"
    ANNULEE = "annulee"
    REFUSEE = "refusee"


# ============================================
# MÉDICAMENT
# ============================================

class MedicamentBase(BaseModel):
    nom: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    categorie: Optional[str] = None
    dosage: Optional[str] = None
    forme: Optional[str] = None
    prix_unitaire: float = Field(..., ge=0)
    quantite_stock: int = Field(..., ge=0)
    quantite_minimum: int = Field(10, ge=0)
    ordonnance_requise: bool = False
    date_expiration: Optional[datetime] = None


class MedicamentCreate(MedicamentBase):
    pass


class MedicamentUpdate(BaseModel):
    nom: Optional[str] = None
    description: Optional[str] = None
    categorie: Optional[str] = None
    dosage: Optional[str] = None
    forme: Optional[str] = None
    prix_unitaire: Optional[float] = Field(None, ge=0)
    quantite_stock: Optional[int] = Field(None, ge=0)
    quantite_minimum: Optional[int] = Field(None, ge=0)
    ordonnance_requise: Optional[bool] = None
    is_disponible: Optional[bool] = None
    date_expiration: Optional[datetime] = None


class MedicamentResponse(MedicamentBase):
    id: int
    pharmacie_id: int
    is_disponible: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class MedicamentWithPharmacie(MedicamentResponse):
    """Médicament avec infos pharmacie"""
    pharmacie_nom: Optional[str] = None
    pharmacie_adresse: Optional[str] = None
    pharmacie_telephone: Optional[str] = None
    pharmacie_latitude: Optional[float] = None
    pharmacie_longitude: Optional[float] = None


class StockUpdate(BaseModel):
    """Mise à jour rapide du stock"""
    quantite: int = Field(..., description="Nouvelle quantité (ou delta)")
    operation: str = Field("set", description="'set', 'add', ou 'subtract'")


# ============================================
# COMMANDE
# ============================================

class CommandeItemCreate(BaseModel):
    medicament_id: int
    quantite: int = Field(..., ge=1)


class CommandeItemResponse(BaseModel):
    id: int
    medicament_id: int
    quantite: int
    prix_unitaire: float
    sous_total: float
    medicament_nom: Optional[str] = None
    medicament_dosage: Optional[str] = None
    medicament_forme: Optional[str] = None
    
    class Config:
        from_attributes = True


class CommandeCreate(BaseModel):
    pharmacie_id: int
    items: List[CommandeItemCreate] = Field(..., min_length=1)
    notes: Optional[str] = None


class CommandeUpdate(BaseModel):
    statut: Optional[StatutCommande] = None
    motif_annulation: Optional[str] = None


class CommandeResponse(BaseModel):
    id: int
    patient_id: int
    pharmacie_id: int
    statut: str
    montant_total: float
    notes: Optional[str] = None
    motif_annulation: Optional[str] = None
    date_commande: datetime
    date_confirmation: Optional[datetime] = None
    date_prete: Optional[datetime] = None
    date_recuperation: Optional[datetime] = None
    date_annulation: Optional[datetime] = None
    items: List[CommandeItemResponse] = []
    
    class Config:
        from_attributes = True