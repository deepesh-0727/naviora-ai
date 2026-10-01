import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class PatientVitals(Base):
    __tablename__ = "patient_vitals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), index=True)
    recorded_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    blood_pressure_systolic: Mapped[int] = mapped_column(Integer)
    blood_pressure_diastolic: Mapped[int] = mapped_column(Integer)
    heart_rate: Mapped[int] = mapped_column(Integer)
    temperature: Mapped[float] = mapped_column(Float)
    spo2: Mapped[int] = mapped_column(Integer)
    weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    height: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, index=True
    )
