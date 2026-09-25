from sqlalchemy import Column, Integer, String, Float, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.connection import Base


class AlertLocation(Base):
    __tablename__ = "alert_locations"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location_source = Column(String(30), nullable=False)
    location_type = Column(String(50), nullable=True)
    state = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    resolved_order = Column(Integer, nullable=True)

    alert = relationship("Alert", back_populates="locations")

    __table_args__ = (
        Index("ix_alert_locations_alert_id", "alert_id"),
    )