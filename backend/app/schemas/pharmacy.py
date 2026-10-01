from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class PrescriptionBase(BaseModel):
    medication: str
    dosage: str
    frequency: str
    duration: str
    instructions: Optional[str] = None

class PrescriptionCreate(PrescriptionBase):
    appointment_id: int
    patient_id: int
    doctor_id: int

class PrescriptionUpdate(BaseModel):
    status: Optional[str] = None
    instructions: Optional[str] = None

class PrescriptionInDBBase(PrescriptionBase):
    id: int
    appointment_id: int
    patient_id: int
    doctor_id: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Prescription(PrescriptionInDBBase):
    pass

class InventoryBase(BaseModel):
    name: str
    category: str
    quantity: int
    unit: str
    reorder_level: int
    location: str
    expiry_date: Optional[datetime] = None

class InventoryUpdate(BaseModel):
    quantity: Optional[int] = None
    reorder_level: Optional[int] = None

class InventoryInDBBase(InventoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Inventory(InventoryInDBBase):
    pass
