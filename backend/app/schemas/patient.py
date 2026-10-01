from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
import re

class PatientBase(BaseModel):
    """
    Base Clinical Profile schema with strict domain validation.
    """
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    date_of_birth: date
    gender: str = Field(..., pattern="^(male|female|other|unknown)$")
    blood_group: Optional[str] = Field(None, pattern="^(A|B|AB|O)[+-]$")
    allergies: Optional[List[str]] = []

    # Clinical Identity & Safety
    emergency_contact: str = Field(..., description="Phone number for next of kin")
    emergency_contact_name: str = Field(..., min_length=2)
    medical_history: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_number: Optional[str] = None

    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Date of birth cannot be in the future")
        if (date.today() - v).days / 365 > 120:
            raise ValueError("Age exceeds clinical maximum (120 years)")
        return v

    @field_validator("emergency_contact")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Strict International E.164 Format
        pattern = r"^\+?[1-9]\d{1,14}$"
        if not re.match(pattern, v):
            raise ValueError("Invalid phone number format. Use E.164 (e.g. +919876543210)")
        return v

class PatientCreate(PatientBase):
    user_id: int

class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    allergies: Optional[List[str]] = None
    emergency_contact: Optional[str] = None
    medical_history: Optional[str] = None

class PatientInDBBase(PatientBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Patient(PatientInDBBase):
    """Public Patient Profile returned to frontend."""
    pass
