from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, func, Float, BigInteger, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database.connection import Base
import enum


class SOSStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    RESOLVED = "resolved"
    RECEIVED = "received"
    ACKNOWLEDGED = "acknowledged"
    AWAITING_RESPONDER = "awaiting_responder"
    RESPONDER_ASSIGNED = "responder_assigned"
    RESPONDER_ACCEPTED = "responder_accepted"
    ASSISTANCE_IN_PROGRESS = "assistance_in_progress"
    ASSISTANCE_PROVIDED = "assistance_provided"
    USER_CONFIRMED_SAFE = "user_confirmed_safe"


class SOSResponderType(str, enum.Enum):
    COMMUNITY = "community"
    OFFICIAL = "official"


class SOSIncident(Base):
    __tablename__ = "sos_incidents"

    id = Column(Integer, primary_key=True, index=True)
    
    reporting_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    assigned_responder_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location_accuracy = Column(Float, nullable=True)
    location_timestamp = Column(BigInteger, nullable=True)
    
    emergency_type = Column(String(100), nullable=True)
    emergency_details = Column(Text, nullable=True)
    
    status = Column(SAEnum(SOSStatus), default=SOSStatus.ACTIVE, nullable=False, index=True)
    responder_type = Column(SAEnum(SOSResponderType), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    reporting_user = relationship("User", foreign_keys=[reporting_user_id], backref="sos_incidents_reported")
    assigned_responder = relationship("User", foreign_keys=[assigned_responder_id], backref="sos_incidents_responded")