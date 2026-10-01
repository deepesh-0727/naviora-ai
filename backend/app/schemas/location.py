from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class LocationBase(BaseModel):
    latitude: float
    longitude: float
    accuracy: float = 1.0
    floor: int = 0
    building: str = "Main"

class LocationUpdate(LocationBase):
    user_id: int

class LocationInDBBase(LocationBase):
    id: int
    user_id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Location(LocationInDBBase):
    pass
