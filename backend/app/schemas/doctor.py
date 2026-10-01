from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None
    floor: int
    building: str
    wing: str
    phone: str
    email: str

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    floor: Optional[int] = None
    building: Optional[str] = None
    wing: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

class DepartmentInDBBase(DepartmentBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Department(DepartmentInDBBase):
    pass

class DoctorBase(BaseModel):
    first_name: str
    last_name: str
    specialization: str
    department_id: int
    license_number: str
    years_of_experience: int
    is_available: bool = True
    max_patients_per_day: int = 20
    consultation_fee: float = 500.0

class DoctorCreate(DoctorBase):
    user_id: int

class DoctorUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    specialization: Optional[str] = None
    department_id: Optional[int] = None
    license_number: Optional[str] = None
    years_of_experience: Optional[int] = None
    is_available: Optional[bool] = None
    max_patients_per_day: Optional[int] = None
    consultation_fee: Optional[float] = None

class DoctorInDBBase(DoctorBase):
    id: int
    user_id: int
    current_patients: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Doctor(DoctorInDBBase):
    department: Optional[Department] = None
