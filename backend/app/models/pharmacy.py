import datetime
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base

class Prescription(Base):
    __tablename__ = "prescriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    appointment_id: Mapped[int] = mapped_column(Integer, ForeignKey("appointments.id"))
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"))
    doctor_id: Mapped[int] = mapped_column(Integer, ForeignKey("doctors.id"))
    medication: Mapped[str] = mapped_column(String(100))
    dosage: Mapped[str] = mapped_column(String(50))
    frequency: Mapped[str] = mapped_column(String(50))
    duration: Mapped[str] = mapped_column(String(50))
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class Inventory(Base):
    __tablename__ = "inventory"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    category: Mapped[str] = mapped_column(String(50))
    quantity: Mapped[int] = mapped_column(Integer)
    unit: Mapped[Optional[str]] = mapped_column(String(20), default="units") # Resilient field
    reorder_level: Mapped[int] = mapped_column(Integer)
    location: Mapped[str] = mapped_column(String(100))
    expiry_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
