from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database.connection import get_db
from app.schemas.user import (
    UserResponse,
    UserLocationUpdate,
    NearbyUserResponse,
    NearbyUsersResponse,
)
from app.schemas.user_settings import UserSettingsResponse, UserSettingsUpdate
from app.utils.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.user_settings import UserSettings
from datetime import datetime, timedelta, timezone
import math
import time

router = APIRouter(prefix="/api/users", tags=["Users"])

STALE_THRESHOLD_MINUTES = 5
DEFAULT_NEARBY_RADIUS_KM = 10
MAX_LOCATION_AGE_SECONDS = 60


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)) * R


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.post("/location", response_model=UserResponse)
async def update_location(
    data: UserLocationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = int(time.time() * 1000)
    client_timestamp = data.timestamp or now
    location_age_ms = now - client_timestamp

    if location_age_ms > MAX_LOCATION_AGE_SECONDS * 1000:
        raise HTTPException(
            status_code=400,
            detail=f"Location timestamp too old: {location_age_ms}ms (max {MAX_LOCATION_AGE_SECONDS * 1000}ms)"
        )

    if current_user.location_timestamp is not None:
        if client_timestamp <= current_user.location_timestamp:
            return UserResponse.model_validate(current_user)

    current_user.last_latitude = data.latitude
    current_user.last_longitude = data.longitude
    if data.accuracy is not None:
        current_user.location_accuracy = data.accuracy
    current_user.location_timestamp = client_timestamp
    current_user.last_location_update = datetime.now(timezone.utc)
    current_user.is_online = True

    await db.flush()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.get("/nearby", response_model=NearbyUsersResponse)
async def get_nearby_users(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(DEFAULT_NEARBY_RADIUS_KM, ge=0.1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stale_threshold = datetime.now(timezone.utc) - timedelta(minutes=STALE_THRESHOLD_MINUTES)
    stale_threshold_ts = int(time.time() * 1000) - (STALE_THRESHOLD_MINUTES * 60 * 1000)

    result = await db.execute(
        select(User).where(
            User.id != current_user.id,
            User.location_visibility == True,
            User.last_latitude.is_not(None),
            User.last_longitude.is_not(None),
            User.last_location_update >= stale_threshold,
        )
    )
    nearby_users = result.scalars().all()

    users_response = []
    for user in nearby_users:
        if user.location_timestamp is not None and user.location_timestamp < stale_threshold_ts:
            continue
        distance = haversine_distance(lat, lng, user.last_latitude, user.last_longitude)
        if distance <= radius_km:
            users_response.append(
                NearbyUserResponse(
                    user_id=user.id,
                    full_name=user.full_name,
                    latitude=user.last_latitude,
                    longitude=user.last_longitude,
                    distance_km=round(distance, 3),
                    last_seen=user.last_location_update,
                    status="active",
                )
            )

    users_response.sort(key=lambda u: u.distance_km)

    return NearbyUsersResponse(users=users_response, count=len(users_response))


@router.get("/settings", response_model=UserSettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
        await db.flush()
        await db.refresh(settings)
    return settings


@router.put("/settings", response_model=UserSettingsResponse)
async def update_settings(
    data: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(settings, key, value)

    await db.flush()
    await db.refresh(settings)
    return settings
