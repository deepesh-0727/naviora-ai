import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class Bed(Base):
    __tablename__ = "beds"
    __table_args__ = (UniqueConstraint("ward", "bed_number", name="uq_beds_ward_bed_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ward: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    bed_number: Mapped[str] = mapped_column(String(40), nullable=False)
    floor: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="available", server_default="available", nullable=False
    )
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patients.id"), nullable=True, index=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        server_default=func.now(),
    )
