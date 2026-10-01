import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, ForeignKey, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry

from app.db.base_class import Base

class EmergencyCase(Base):
    __tablename__ = "emergency_cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("patients.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="triggered") # triggered, staff_assigned, treating, resolved
    priority: Mapped[str] = mapped_column(String(20), default="CRITICAL")
    location_desc: Mapped[str] = mapped_column(String(255)) # description or GPS string
    location_coords = mapped_column(Geometry(geometry_type='POINT', srid=4326), nullable=True) # Matches Supabase
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_staff: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True) # list of staff names/IDs
    ambulance_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    response_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # in seconds
    arrival_time: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    treatment_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
