import datetime
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, Text, DateTime, JSON, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String(20)) # push, SMS, email
    channel: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(150))
    message: Mapped[str] = mapped_column(Text)
    data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    is_delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    delivered_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

class ConversationHistory(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    session_id: Mapped[str] = mapped_column(String(100), index=True)
    query: Mapped[str] = mapped_column(Text)
    intent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    agent_used: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    response: Mapped[str] = mapped_column(Text)
    audio_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sentiment: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_voice: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
