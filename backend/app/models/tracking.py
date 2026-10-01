import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry

from app.db.base_class import Base

class LocationTracking(Base):
    __tablename__ = "location_tracking"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    accuracy: Mapped[float] = mapped_column(Float, default=1.0)
    floor: Mapped[int] = mapped_column(Integer, default=0)
    building: Mapped[str] = mapped_column(String(50), default="Main")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    # PostGIS Location spatial column representation
    location = mapped_column(Geometry(geometry_type='POINT', srid=4326), nullable=True)
