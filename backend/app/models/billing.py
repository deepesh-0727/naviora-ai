import datetime
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, Text, DateTime, JSON, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base

class Billing(Base):
    __tablename__ = "billing"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"))
    appointment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("appointments.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(20), default="pending") # pending, paid, cancelled
    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    transaction_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True)
    items: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
