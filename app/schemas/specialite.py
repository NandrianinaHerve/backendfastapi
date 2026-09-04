from pydantic import BaseModel
from typing import Optional

class SpecialiteBase(BaseModel):
    nom: str
    description: Optional[str] = None
    icone: Optional[str] = None

class SpecialiteCreate(SpecialiteBase):
    pass

class SpecialiteResponse(SpecialiteBase):
    id: int
    
    class Config:
        from_attributes = True