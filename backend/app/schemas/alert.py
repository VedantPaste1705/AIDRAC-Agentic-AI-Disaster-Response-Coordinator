from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AlertCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    disaster_id: Optional[int] = None
    severity: str = "info"
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    accuracy: Optional[float] = Field(None, ge=0)
    timestamp: Optional[int] = Field(None, ge=0)


class AlertResponse(BaseModel):
    id: int
    title: str
    message: str
    disaster_id: Optional[int] = None
    severity: str
    created_at: datetime
    external_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    event: Optional[str] = None
    urgency: Optional[str] = None
    certainty: Optional[str] = None
    area: Optional[str] = None
    is_active: bool = True
    expired_at: Optional[datetime] = None
    polygons: Optional[str] = None
    source: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy: Optional[float] = None
    timestamp: Optional[int] = None

    class Config:
        from_attributes = True
