from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.models.user import UserRole
from datetime import datetime


class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: UserRole

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserLocationUpdate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: Optional[float] = Field(None, ge=0)
    timestamp: Optional[int] = Field(None, ge=0)


class NearbyUserResponse(BaseModel):
    user_id: int
    full_name: str
    latitude: float
    longitude: float
    distance_km: float
    last_seen: datetime
    status: str = "active"

    class Config:
        from_attributes = True


class NearbyUsersResponse(BaseModel):
    users: list[NearbyUserResponse]
    count: int
