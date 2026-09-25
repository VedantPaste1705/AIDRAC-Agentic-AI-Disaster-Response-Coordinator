from sqlalchemy import Column, Integer, String, Text, Float, Index
from app.database.connection import Base


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    type = Column(String(50), nullable=True)
    state = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True, default="India")
    aliases = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_locations_state_district", "state", "district"),
    )