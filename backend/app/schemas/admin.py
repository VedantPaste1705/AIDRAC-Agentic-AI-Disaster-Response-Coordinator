from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.schemas.sos import SOSStatus, SOSResponderType


class AdminOverviewResponse(BaseModel):
    active_alerts: int
    active_sos: int
    people_in_affected_zones: int
    people_marked_safe: int
    people_requiring_help: int
    available_responders: int
    active_response_tasks: int


class AdminAlertResponse(BaseModel):
    id: int
    title: str
    message: str
    severity: str
    created_at: datetime
    external_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    event: Optional[str] = None
    urgency: Optional[str] = None
    certainty: Optional[str] = None
    area: Optional[str] = None
    is_active: bool
    polygons: Optional[str] = None
    source: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_source: Optional[str] = None
    locations: List[dict] = []

    class Config:
        from_attributes = True


class AdminSOSResponse(BaseModel):
    id: int
    reporting_user_id: int
    reporting_user_name: Optional[str] = None
    assigned_responder_id: Optional[int] = None
    assigned_responder_name: Optional[str] = None
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


class AdminResponderResponse(BaseModel):
    id: int
    full_name: str
    email: str
    last_latitude: Optional[float] = None
    last_longitude: Optional[float] = None
    location_accuracy: Optional[float] = None
    last_location_update: Optional[datetime] = None
    is_online: bool
    active_sos_id: Optional[int] = None
    active_sos_status: Optional[SOSStatus] = None


class AdminUserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    last_latitude: Optional[float] = None
    last_longitude: Optional[float] = None
    location_accuracy: Optional[float] = None
    last_location_update: Optional[datetime] = None
    location_visibility: bool
    is_online: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminIncidentHistoryResponse(BaseModel):
    id: int
    reporting_user_id: int
    reporting_user_name: Optional[str] = None
    assigned_responder_id: Optional[int] = None
    assigned_responder_name: Optional[str] = None
    latitude: float
    longitude: float
    location_accuracy: Optional[float] = None
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


class AdminZoneStatsResponse(BaseModel):
    total_people_detected: int
    people_requiring_help: int
    active_sos: int
    people_helped: int
    people_marked_safe: int
    responders_active: int