"""
Multi-Device Synchronization API router for DevPocket.
"""

from typing import Annotated, Dict, Any
from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.db.database import get_db
from app.models.user import User
from .schemas import (
    SyncDataRequest,
    SyncDataResponse,
    DeviceRegistration,
    DeviceInfo,
    SyncStats,
    MessageResponse,
)
from .service import SyncService


router = APIRouter(
    prefix="/api/sync",
    tags=["Multi-Device Sync"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Access forbidden"},
        500: {"description": "Internal server error"},
    },
)


@router.get("/data", response_model=SyncDataResponse, summary="Get Sync Data")
async def get_sync_data(
    request: SyncDataRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SyncDataResponse:
    """Retrieve synchronization data for device."""
    service = SyncService(db)
    return await service.sync_data(current_user, request)


@router.post("/data", response_model=MessageResponse, summary="Upload Sync Data")
async def upload_sync_data(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    data: Dict[str, Any] = Body(..., description="Synchronization data"),
) -> MessageResponse:
    """Upload device synchronization data."""
    service = SyncService(db)
    await service.upload_sync_data(current_user, data)
    return MessageResponse(message="Sync data uploaded successfully")


@router.get("/stats", response_model=SyncStats, summary="Get Sync Statistics")
async def get_sync_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SyncStats:
    """Get synchronization statistics."""
    service = SyncService(db)
    return await service.get_sync_stats(current_user)
