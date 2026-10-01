from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class UserRegister(BaseModel):
    phone: str = Field(..., description="Phone number of the patient")
    email: str = Field(..., description="Email address")
    first_name: str
    last_name: str
    password: str
    date_of_birth: Optional[date] = None
    gender: str = "unknown"
    blood_group: Optional[str] = None
    allergies: Optional[List[str]] = None
    emergency_contact: str = ""
    emergency_contact_name: str = ""
    medical_history: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_number: Optional[str] = None

class OTPVerification(BaseModel):
    phone: str
    code: str
