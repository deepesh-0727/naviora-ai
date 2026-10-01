from sqlalchemy import Column, Integer, String, Float, Text
from app.db.base_class import Base

class LabService(Base):
    __tablename__ = "lab_services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    category = Column(String(100), index=True, nullable=False)
    price = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
