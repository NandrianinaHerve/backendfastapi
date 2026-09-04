from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class LocalisationBase(BaseModel):
    latitude: float
    longitude: float

class LocalisationCreate(LocalisationBase):
    user_id: Optional[int] = None

class LocalisationResponse(BaseModel):
    id: int
    user_id: int
    latitude: float
    longitude: float
    is_active: bool
    updated_at: datetime
    
    class Config:
        from_attributes = True