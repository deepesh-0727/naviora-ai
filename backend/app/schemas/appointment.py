from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class AppointmentBase(BaseModel):
    patient_id: int
    doctor_id: int
    department_id: int
    appointment_type: str = "consultation"
    scheduled_time: datetime
    priority: str = "normal"
    symptoms: Optional[str] = None
    notes: Optional[str] = None
    is_telehealth: bool = False

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdate(BaseModel):
    status: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    actual_time: Optional[datetime] = None
    wait_time_minutes: Optional[int] = None
    priority: Optional[str] = None
    symptoms: Optional[str] = None
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = None
    is_telehealth: Optional[bool] = None

class AppointmentInDBBase(AppointmentBase):
    id: int
    status: str
    queue_position: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Appointment(AppointmentInDBBase):
    pass
