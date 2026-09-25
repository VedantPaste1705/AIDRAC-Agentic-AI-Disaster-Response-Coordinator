from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database.connection import get_db
from app.schemas.sos import (
    SOSIncidentCreate,
    SOSIncidentUpdate,
    SOSIncidentResponse,
    SOSIncidentDetailResponse,
    SOSNearbyResponse,
    SOSActiveResponse,
    SOSAdminListResponse,
)
from app.services.sos import SOSService
from app.models.user import User
from app.utils.dependencies import get_current_user, require_admin
from app.models.sos import SOSStatus

router = APIRouter(prefix="/api/sos", tags=["SOS"])


@router.post("", response_model=SOSIncidentResponse, status_code=201)
async def create_sos(
    data: SOSIncidentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SOSService(db)
    try:
        sos = await service.create_sos(current_user, data)
        return SOSIncidentResponse.model_validate(sos)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/active", response_model=SOSActiveResponse)
async def get_active_sos(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SOSService(db)
    
    victim_sos = await service.get_active_sos_for_user(current_user.id)
    
    responder_sos = await service.get_sos_for_responder(current_user.id)
    
    return SOSActiveResponse(
        sos=SOSIncidentDetailResponse.model_validate(victim_sos) if victim_sos else None,
        is_responder=responder_sos is not None,
        responder_sos=SOSIncidentDetailResponse.model_validate(responder_sos) if responder_sos else None,
    )


@router.get("/nearby", response_model=List[SOSNearbyResponse])
async def get_nearby_sos(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(10, ge=0.1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SOSService(db)
    nearby = await service.get_active_sos_nearby(lat, lng, radius_km, exclude_user_id=current_user.id)
    return nearby


@router.get("/{sos_id}", response_model=SOSIncidentDetailResponse)
async def get_sos(
    sos_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SOSService(db)
    sos = await service.get_sos_by_id(sos_id)
    
    if not sos:
        raise HTTPException(status_code=404, detail="SOS incident not found")
    
    is_victim = sos.reporting_user_id == current_user.id
    is_responder = sos.assigned_responder_id == current_user.id
    is_admin = current_user.role.value == "admin"
    
    if not (is_victim or is_responder or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to view this SOS incident")
    
    victim = await db.execute(
        select(User).where(User.id == sos.reporting_user_id)
    )
    victim_user = victim.scalar_one_or_none()
    
    responder_name = None
    if sos.assigned_responder_id:
        responder = await db.execute(
            select(User).where(User.id == sos.assigned_responder_id)
        )
        responder_user = responder.scalar_one_or_none()
        responder_name = responder_user.full_name if responder_user else None
    
    response = SOSIncidentDetailResponse.model_validate(sos)
    response.reporting_user_name = victim_user.full_name if victim_user else None
    response.assigned_responder_name = responder_name
    
    return response


@router.post("/{sos_id}/cancel", response_model=SOSIncidentResponse)
async def cancel_sos(
    sos_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SOSService(db)
    try:
        sos = await service.update_sos_status(sos_id, current_user, SOSStatus.CANCELLED)
        return SOSIncidentResponse.model_validate(sos)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{sos_id}/accept", response_model=SOSIncidentResponse)
async def accept_sos(
    sos_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SOSService(db)
    try:
        sos = await service.accept_sos(sos_id, current_user)
        return SOSIncidentResponse.model_validate(sos)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{sos_id}/status", response_model=SOSIncidentResponse)
async def update_sos_status(
    sos_id: int,
    data: SOSIncidentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.status is None:
        raise HTTPException(status_code=400, detail="Status is required")
    
    service = SOSService(db)
    try:
        sos = await service.update_sos_status(sos_id, current_user, data.status)
        return SOSIncidentResponse.model_validate(sos)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{sos_id}/confirm-safe", response_model=SOSIncidentResponse)
async def confirm_safe(
    sos_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SOSService(db)
    try:
        sos = await service.update_sos_status(sos_id, current_user, SOSStatus.USER_CONFIRMED_SAFE)
        return SOSIncidentResponse.model_validate(sos)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/my/history", response_model=List[SOSIncidentResponse])
async def get_my_sos_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SOSService(db)
    incidents = await service.get_user_sos_incidents(current_user.id, limit, offset)
    return [SOSIncidentResponse.model_validate(s) for s in incidents]


# Admin endpoints
@router.get("/admin/active", response_model=List[SOSAdminListResponse])
async def admin_get_active_sos(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = SOSService(db)
    incidents = await service.get_all_active_sos(db)
    
    result = []
    for sos in incidents:
        victim = await db.execute(select(User).where(User.id == sos.reporting_user_id))
        victim_user = victim.scalar_one_or_none()
        
        responder_name = None
        if sos.assigned_responder_id:
            responder = await db.execute(select(User).where(User.id == sos.assigned_responder_id))
            responder_user = responder.scalar_one_or_none()
            responder_name = responder_user.full_name if responder_user else None
        
        result.append(SOSAdminListResponse(
            id=sos.id,
            reporting_user_id=sos.reporting_user_id,
            reporting_user_name=victim_user.full_name if victim_user else None,
            assigned_responder_id=sos.assigned_responder_id,
            assigned_responder_name=responder_name,
            latitude=sos.latitude,
            longitude=sos.longitude,
            location_accuracy=sos.location_accuracy,
            emergency_type=sos.emergency_type,
            status=sos.status,
            responder_type=sos.responder_type,
            created_at=sos.created_at,
            updated_at=sos.updated_at,
            accepted_at=sos.accepted_at,
            resolved_at=sos.resolved_at,
        ))
    
    return result


@router.get("/admin/history", response_model=List[SOSAdminListResponse])
async def admin_get_sos_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = SOSService(db)
    incidents = await service.get_sos_history(limit, offset)
    
    result = []
    for sos in incidents:
        victim = await db.execute(select(User).where(User.id == sos.reporting_user_id))
        victim_user = victim.scalar_one_or_none()
        
        responder_name = None
        if sos.assigned_responder_id:
            responder = await db.execute(select(User).where(User.id == sos.assigned_responder_id))
            responder_user = responder.scalar_one_or_none()
            responder_name = responder_user.full_name if responder_user else None
        
        result.append(SOSAdminListResponse(
            id=sos.id,
            reporting_user_id=sos.reporting_user_id,
            reporting_user_name=victim_user.full_name if victim_user else None,
            assigned_responder_id=sos.assigned_responder_id,
            assigned_responder_name=responder_name,
            latitude=sos.latitude,
            longitude=sos.longitude,
            location_accuracy=sos.location_accuracy,
            emergency_type=sos.emergency_type,
            status=sos.status,
            responder_type=sos.responder_type,
            created_at=sos.created_at,
            updated_at=sos.updated_at,
            accepted_at=sos.accepted_at,
            resolved_at=sos.resolved_at,
        ))
    
    return result


@router.post("/admin/{sos_id}/responder", response_model=SOSIncidentResponse)
async def admin_assign_responder(
    sos_id: int,
    responder_id: Optional[int] = Query(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = SOSService(db)
    try:
        sos = await service.admin_override_responder(sos_id, responder_id)
        return SOSIncidentResponse.model_validate(sos)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Need to import select for admin endpoints
from sqlalchemy import select