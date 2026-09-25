import math
import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from app.models.sos import SOSIncident, SOSStatus, SOSResponderType
from app.models.user import User
from app.schemas.sos import SOSIncidentCreate, SOSIncidentUpdate, SOSIncidentResponse, SOSNearbyResponse
from app.utils.latency import LatencyTracker

logger = logging.getLogger("aidrac.services.sos")

EARTH_RADIUS_KM = 6371
SOS_SEARCH_RADIUS_KM = 10


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)) * EARTH_RADIUS_KM


class SOSService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_sos(self, user: User, data: SOSIncidentCreate) -> SOSIncident:
        existing_active = await self.get_active_sos_for_user(user.id)
        if existing_active:
            raise ValueError("User already has an active SOS incident")

        sos = SOSIncident(
            reporting_user_id=user.id,
            latitude=data.latitude,
            longitude=data.longitude,
            location_accuracy=data.accuracy,
            location_timestamp=data.timestamp,
            emergency_type=data.emergency_type,
            emergency_details=data.emergency_details,
            status=SOSStatus.ACTIVE,
        )
        self.db.add(sos)
        await self.db.flush()
        await self.db.refresh(sos)
        return sos

    async def get_sos_by_id(self, sos_id: int) -> Optional[SOSIncident]:
        result = await self.db.execute(
            select(SOSIncident).where(SOSIncident.id == sos_id)
        )
        return result.scalar_one_or_none()

    async def get_active_sos_for_user(self, user_id: int) -> Optional[SOSIncident]:
        result = await self.db.execute(
            select(SOSIncident).where(
                SOSIncident.reporting_user_id == user_id,
                SOSIncident.status.in_([
                    SOSStatus.ACTIVE,
                    SOSStatus.RECEIVED,
                    SOSStatus.ACKNOWLEDGED,
                    SOSStatus.AWAITING_RESPONDER,
                    SOSStatus.RESPONDER_ASSIGNED,
                    SOSStatus.RESPONDER_ACCEPTED,
                    SOSStatus.ASSISTANCE_IN_PROGRESS,
                    SOSStatus.ASSISTANCE_PROVIDED,
                    SOSStatus.USER_CONFIRMED_SAFE,
                ])
            ).order_by(SOSIncident.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_user_sos_incidents(self, user_id: int, limit: int = 50, offset: int = 0) -> List[SOSIncident]:
        result = await self.db.execute(
            select(SOSIncident)
            .where(SOSIncident.reporting_user_id == user_id)
            .order_by(SOSIncident.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_active_sos_nearby(
        self,
        lat: float,
        lng: float,
        radius_km: float = SOS_SEARCH_RADIUS_KM,
        exclude_user_id: Optional[int] = None,
    ) -> List[SOSNearbyResponse]:
        active_statuses = [
            SOSStatus.ACTIVE,
            SOSStatus.RECEIVED,
            SOSStatus.ACKNOWLEDGED,
            SOSStatus.AWAITING_RESPONDER,
        ]
        
        result = await self.db.execute(
            select(SOSIncident).where(
                SOSIncident.status.in_(active_statuses),
                SOSIncident.latitude.is_not(None),
                SOSIncident.longitude.is_not(None),
            )
        )
        sos_incidents = result.scalars().all()

        nearby = []
        for sos in sos_incidents:
            if exclude_user_id and sos.reporting_user_id == exclude_user_id:
                continue
            
            if sos.assigned_responder_id is not None:
                continue
            
            distance = _haversine(lat, lng, sos.latitude, sos.longitude)
            if distance <= radius_km:
                victim = await self.db.execute(
                    select(User).where(User.id == sos.reporting_user_id)
                )
                victim_user = victim.scalar_one_or_none()
                
                nearby.append(SOSNearbyResponse(
                    sos_id=sos.id,
                    distance_km=round(distance, 2),
                    emergency_type=sos.emergency_type,
                    created_at=sos.created_at,
                    victim_name=victim_user.full_name if victim_user else "Unknown",
                ))

        nearby.sort(key=lambda x: x.distance_km)
        return nearby

    async def accept_sos(self, sos_id: int, responder: User) -> SOSIncident:
        sos = await self.get_sos_by_id(sos_id)
        if not sos:
            raise ValueError("SOS incident not found")

        if sos.status not in [SOSStatus.ACTIVE, SOSStatus.RECEIVED, SOSStatus.ACKNOWLEDGED, SOSStatus.AWAITING_RESPONDER]:
            raise ValueError("SOS incident is no longer accepting responders")

        if sos.assigned_responder_id is not None:
            raise ValueError("SOS incident already has a responder assigned")

        if sos.reporting_user_id == responder.id:
            raise ValueError("Cannot respond to your own SOS")

        sos.assigned_responder_id = responder.id
        sos.responder_type = SOSResponderType.COMMUNITY
        sos.status = SOSStatus.RESPONDER_ACCEPTED
        sos.accepted_at = datetime.now(timezone.utc)
        sos.updated_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(sos)
        return sos

    async def update_sos_status(self, sos_id: int, user: User, status: SOSStatus) -> SOSIncident:
        sos = await self.get_sos_by_id(sos_id)
        if not sos:
            raise ValueError("SOS incident not found")

        is_victim = sos.reporting_user_id == user.id
        is_responder = sos.assigned_responder_id == user.id
        is_admin = user.role.value == "admin"

        if not (is_victim or is_responder or is_admin):
            raise ValueError("Not authorized to update this SOS incident")

        if is_victim:
            allowed_statuses = [SOSStatus.CANCELLED, SOSStatus.USER_CONFIRMED_SAFE]
            if status not in allowed_statuses:
                raise ValueError("Victim can only cancel or confirm safe")
            
            if status == SOSStatus.USER_CONFIRMED_SAFE:
                if sos.status != SOSStatus.ASSISTANCE_PROVIDED:
                    raise ValueError("Can only confirm safe after assistance provided")
                sos.resolved_at = datetime.now(timezone.utc)
                sos.status = SOSStatus.RESOLVED
            elif status == SOSStatus.CANCELLED:
                if sos.status in [SOSStatus.ASSISTANCE_PROVIDED, SOSStatus.USER_CONFIRMED_SAFE, SOSStatus.RESOLVED]:
                    raise ValueError("Cannot cancel after assistance provided")
                sos.status = SOSStatus.CANCELLED

        elif is_responder:
            allowed_transitions = {
                SOSStatus.RESPONDER_ACCEPTED: [SOSStatus.ASSISTANCE_IN_PROGRESS],
                SOSStatus.ASSISTANCE_IN_PROGRESS: [SOSStatus.ASSISTANCE_PROVIDED],
            }
            if sos.status not in allowed_transitions or status not in allowed_transitions.get(sos.status, []):
                raise ValueError(f"Invalid status transition from {sos.status} to {status}")
            sos.status = status

        elif is_admin:
            sos.status = status
            if status == SOSStatus.RESOLVED:
                sos.resolved_at = datetime.now(timezone.utc)

        sos.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(sos)
        return sos

    async def get_sos_for_responder(self, responder_id: int) -> Optional[SOSIncident]:
        result = await self.db.execute(
            select(SOSIncident).where(
                SOSIncident.assigned_responder_id == responder_id,
                SOSIncident.status.in_([
                    SOSStatus.RESPONDER_ACCEPTED,
                    SOSStatus.ASSISTANCE_IN_PROGRESS,
                    SOSStatus.ASSISTANCE_PROVIDED,
                ])
            ).order_by(SOSIncident.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_all_active_sos(self, db: AsyncSession) -> List[SOSIncident]:
        result = await db.execute(
            select(SOSIncident).where(
                SOSIncident.status.in_([
                    SOSStatus.ACTIVE,
                    SOSStatus.RECEIVED,
                    SOSStatus.ACKNOWLEDGED,
                    SOSStatus.AWAITING_RESPONDER,
                    SOSStatus.RESPONDER_ASSIGNED,
                    SOSStatus.RESPONDER_ACCEPTED,
                    SOSStatus.ASSISTANCE_IN_PROGRESS,
                    SOSStatus.ASSISTANCE_PROVIDED,
                    SOSStatus.USER_CONFIRMED_SAFE,
                ])
            ).order_by(SOSIncident.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_sos_history(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[SOSIncident]:
        result = await self.db.execute(
            select(SOSIncident)
            .where(SOSIncident.status.in_([SOSStatus.RESOLVED, SOSStatus.CANCELLED]))
            .order_by(SOSIncident.resolved_at.desc().nullslast(), SOSIncident.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def admin_override_responder(self, sos_id: int, new_responder_id: Optional[int]) -> SOSIncident:
        sos = await self.get_sos_by_id(sos_id)
        if not sos:
            raise ValueError("SOS incident not found")

        if new_responder_id is not None:
            result = await self.db.execute(select(User).where(User.id == new_responder_id))
            new_responder = result.scalar_one_or_none()
            if not new_responder:
                raise ValueError("New responder not found")
            sos.assigned_responder_id = new_responder_id
            sos.responder_type = SOSResponderType.OFFICIAL
            sos.status = SOSStatus.RESPONDER_ASSIGNED
            sos.accepted_at = datetime.now(timezone.utc)
        else:
            sos.assigned_responder_id = None
            sos.responder_type = None
            sos.status = SOSStatus.AWAITING_RESPONDER
            sos.accepted_at = None

        sos.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(sos)
        return sos