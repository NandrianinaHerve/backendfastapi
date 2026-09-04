# app/schemas/administrateur.py
from pydantic import BaseModel
from typing import Optional
from .user import UserCreate, UserResponse

class AdministrateurBase(BaseModel):
    poste: Optional[str] = None
    notes: Optional[str] = None

class AdministrateurCreate(AdministrateurBase):
    user: UserCreate

class AdministrateurUpdate(BaseModel):
    poste: Optional[str] = None
    notes: Optional[str] = None

class AdministrateurResponse(AdministrateurBase):
    id: int
    user_id: int
    user: UserResponse
    
    class Config:
        from_attributes = True