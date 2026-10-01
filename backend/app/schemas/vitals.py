from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PatientVitalsCreate(BaseModel):
    patient_id: int = Field(gt=0)
    blood_pressure_systolic: int = Field(gt=0, le=300)
    blood_pressure_diastolic: int = Field(gt=0, le=200)
    heart_rate: int = Field(gt=0, le=300)
    temperature: float = Field(gt=0, le=50)
    spo2: int = Field(gt=0, le=100)
    weight: Optional[float] = Field(None, gt=0, le=1000)
    height: Optional[float] = Field(None, gt=0, le=300)
    notes: Optional[str] = None


class PatientVitals(BaseModel):
    id: int
    patient_id: int
    recorded_by_id: int
    blood_pressure_systolic: int
    blood_pressure_diastolic: int
    heart_rate: int
    temperature: float
    spo2: int
    weight: Optional[float] = None
    height: Optional[float] = None
    notes: Optional[str] = None
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)
