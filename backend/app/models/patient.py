import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from .user import User
    from .appointment import Appointment

class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True)
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    date_of_birth: Mapped[datetime.date] = mapped_column(DateTime)
    gender: Mapped[str] = mapped_column(String(10))
    blood_group: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    allergies: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    emergency_contact: Mapped[str] = mapped_column(String(20))
    emergency_contact_name: Mapped[str] = mapped_column(String(100))
    medical_history: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    insurance_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    insurance_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    qr_code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="patient_profile")
    appointments: Mapped[List["Appointment"]] = relationship("Appointment", back_populates="patient")
