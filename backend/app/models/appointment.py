import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from .patient import Patient
    from .doctor import Doctor
    from .doctor import Department

class Appointment(Base):
    __tablename__ = "appointments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"))
    doctor_id: Mapped[int] = mapped_column(Integer, ForeignKey("doctors.id"))
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey("departments.id"))
    appointment_type: Mapped[str] = mapped_column(String(20), default="consultation") # consultation, follow-up, emergency
    status: Mapped[str] = mapped_column(String(20), default="scheduled") # scheduled, cancelled, check_in, treating, completed
    queue_position: Mapped[int] = mapped_column(Integer, default=0)
    scheduled_time: Mapped[datetime.datetime] = mapped_column(DateTime)
    actual_time: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    wait_time_minutes: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[str] = mapped_column(String(20), default="normal") # normal, urgent, emergency
    symptoms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_telehealth: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="appointments")
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="appointments")
    department: Mapped["Department"] = relationship("Department", back_populates="appointments")
