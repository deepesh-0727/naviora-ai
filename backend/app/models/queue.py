import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class QueueEntry(Base):
    __tablename__ = "queue_entries"
    __table_args__ = (UniqueConstraint("appointment_id", name="uq_queue_entries_appointment"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    appointment_id: Mapped[int] = mapped_column(Integer, ForeignKey("appointments.id"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="queued", server_default="queued", nullable=False
    )
    entered_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, server_default=func.now()
    )
    served_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
