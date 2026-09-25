from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.sos import SOSStatus, SOSResponderType


class SOSIncidentCreate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: Optional[float] = Field(None, ge=0)
    timestamp: Optional[int] = Field(None, ge=0)
    emergency_type: Optional[str] = Field(None, max_length=100)
    emergency_details: Optional[str] = None


class SOSIncidentUpdate(BaseModel):
    status: Optional[SOSStatus] = None
    emergency_type: Optional[str] = Field(None, max_length=100)
    emergency_details: Optional[str] = None


class SOSIncidentResponse(BaseModel):
    id: int
    reporting_user_id: int
    assigned_responder_id: Optional[int] = None
    latitude: float
    longitude: float
    location_accuracy: Optional[float] = None
    location_timestamp: Optional[int] = None
    emergency_type: Optional[str] = None
    emergency_details: Optional[str] = None
    status: SOSStatus
    responder_type: Optional[SOSResponderType] = None
    created_at: datetime
    updated_at: datetime
    accepted_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SOSIncidentDetailResponse(SOSIncidentResponse):
    reporting_user_name: Optional[str] = None
    assigned_responder_name: Optional[str] = None


class SOSNearbyResponse(BaseModel):
    sos_id: int
    distance_km: float
    emergency_type: Optional[str] = None
    created_at: datetime
    victim_name: str


class SOSActiveResponse(BaseModel):
    sos: Optional[SOSIncidentDetailResponse] = None
    is_responder: bool = False
    responder_sos: Optional[SOSIncidentDetailResponse] = None


class SOSAdminListResponse(BaseModel):
    id: int
    reporting_user_id: int
    reporting_user_name: Optional[str] = None
    assigned_responder_id: Optional[int] = None
    assigned_responder_name: Optional[str] = None
    latitude: float
    longitude: float
    location_accuracy: Optional[float] = None
    emergency_type: Optional[str] = None
    status: SOSStatus
    responder_type: Optional[SOSResponderType] = None
    created_at: datetime
    updated_at: datetime
    accepted_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None