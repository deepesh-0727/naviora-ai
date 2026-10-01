import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, ForeignKey, Text, DateTime, JSON, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    resource: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    appointment_id: Mapped[int] = mapped_column(Integer, ForeignKey("appointments.id"))
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"))
    rating: Mapped[int] = mapped_column(Integer)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    categories: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

class StaffSchedule(Base):
    __tablename__ = "staff_schedule"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    staff_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    date: Mapped[datetime.date] = mapped_column(DateTime)
    start_time: Mapped[datetime.datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime.datetime] = mapped_column(DateTime)
    shift_type: Mapped[str] = mapped_column(String(20), default="regular")
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
