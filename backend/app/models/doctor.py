import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey, Float, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry

from app.db.base_class import Base

if TYPE_CHECKING:
    from .user import User
    from .appointment import Appointment

class Doctor(Base):
    __tablename__ = "doctors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True)
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    specialization: Mapped[str] = mapped_column(String(100))
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey("departments.id"))
    license_number: Mapped[str] = mapped_column(String(50), unique=True)
    years_of_experience: Mapped[int] = mapped_column(Integer)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    max_patients_per_day: Mapped[int] = mapped_column(Integer, default=20)
    current_patients: Mapped[int] = mapped_column(Integer, default=0)
    consultation_fee: Mapped[float] = mapped_column(Float, default=500.0)
    avg_consultation_time: Mapped[int] = mapped_column(Integer, default=15) # in minutes
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="doctor_profile")
    department: Mapped["Department"] = relationship("Department", back_populates="doctors")
    appointments: Mapped[List["Appointment"]] = relationship("Appointment", back_populates="doctor")

class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    floor: Mapped[int] = mapped_column(Integer)
    building: Mapped[str] = mapped_column(String(50))
    wing: Mapped[str] = mapped_column(String(50))
    location = mapped_column(Geometry(geometry_type='POINT', srid=4326), nullable=True) # Matches Supabase
    phone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    doctors: Mapped[List["Doctor"]] = relationship("Doctor", back_populates="department")
    appointments: Mapped[List["Appointment"]] = relationship("Appointment", back_populates="department")
