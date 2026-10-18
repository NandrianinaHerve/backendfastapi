from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


# ============================================
# 1. D'ABORD : MedicamentTrouve
# ============================================
class MedicamentTrouve(BaseModel):
    medicament_id: int
    nom: str
    dosage: Optional[str] = None
    posologie: Optional[str] = None
    prix_unitaire: float
    quantite_stock: int


# ============================================
# 2. ENSUITE : PharmacieProposee
# ============================================
class PharmacieProposee(BaseModel):
    pharmacie_id: int
    pharmacie_nom: str
    pharmacie_adresse: Optional[str] = None
    pharmacie_telephone: Optional[str] = None
    pharmacie_latitude: Optional[float] = None
    pharmacie_longitude: Optional[float] = None
    is_open: bool = False
    distance_km: Optional[float] = None
    medicaments_trouves: List[MedicamentTrouve] = []
    nb_medicaments_disponibles: Optional[int] = None
    nb_medicaments_total: Optional[int] = None


# ============================================
# 3. PUIS : MedicamentAvecPharmacies
# ============================================
class MedicamentAvecPharmacies(BaseModel):
    medicament: Dict
    pharmacies: List[PharmacieProposee] = []
    nb_pharmacies: int = 0
    trouve: bool = False


# ============================================
# 4. AnalyseOrdonnanceResponse
# ============================================
class AnalyseOrdonnanceResponse(BaseModel):
    success: bool
    ordonnance_id: Optional[int] = None
    nb_medicaments: int = 0
    medicaments: List[MedicamentAvecPharmacies] = []
    pharmacies_completes: List[PharmacieProposee] = []
    pharmacies_partielles: List[PharmacieProposee] = []
    message: Optional[str] = None


# ============================================
# 5. CommandeAutomatique
# ============================================
class CommandeAutomatiqueRequest(BaseModel):
    ordonnance_id: int
    pharmacie_id: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    notes: Optional[str] = None


class CommandeAutomatiqueResponse(BaseModel):
    success: bool
    commande_id: Optional[int] = None
    pharmacie_id: Optional[int] = None
    pharmacie_nom: Optional[str] = None
    montant_total: float = 0.0
    nb_medicaments: int = 0
    medicaments_commandes: List[Dict] = []
    medicaments_non_trouves: List[Dict] = []
    message: Optional[str] = None