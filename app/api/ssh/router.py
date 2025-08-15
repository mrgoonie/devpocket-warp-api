"""
SSH Management API router for DevPocket.

Handles all SSH-related endpoints including profiles, keys, and connection testing.
"""

from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.logging import logger
from app.db.database import get_db
from app.models.user import User
from .schemas import (
    # SSH Profile schemas
    SSHProfileCreate,
    SSHProfileUpdate,
    SSHProfileResponse,
    SSHProfileListResponse,
    SSHProfileSearchRequest,
    SSHProfileStats,
    # SSH Key schemas
    SSHKeyCreate,
    SSHKeyUpdate,
    SSHKeyResponse,
    SSHKeyListResponse,
    SSHKeySearchRequest,
    SSHKeyStats,
    # Connection testing schemas
    SSHConnectionTestRequest,
    SSHConnectionTestResponse,
    # Common schemas
    MessageResponse,
    BulkOperationResponse,
)
from .service import SSHProfileService, SSHKeyService


# Create router instance
router = APIRouter(
    prefix="/api/ssh",
    tags=["SSH Management"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Access forbidden"},
        404: {"description": "Resource not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)


# SSH Profile Endpoints


@router.post(
    "/profiles",
    response_model=SSHProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create SSH Profile",
    description="Create a new SSH connection profile",
)
async def create_ssh_profile(
    profile_data: SSHProfileCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SSHProfileResponse:
    """Create a new SSH profile."""
    service = SSHProfileService(db)
    return await service.create_profile(current_user, profile_data)


@router.get(
    "/profiles",
    response_model=SSHProfileListResponse,
    summary="List SSH Profiles",
    description="Get user's SSH profiles with pagination",
)
async def list_ssh_profiles(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    active_only: bool = Query(default=True, description="Show only active profiles"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    limit: int = Query(default=50, ge=1, le=100, description="Pagination limit"),
) -> SSHProfileListResponse:
    """Get user's SSH profiles with pagination."""
    service = SSHProfileService(db)
    profiles, total = await service.get_user_profiles(
        current_user, active_only=active_only, offset=offset, limit=limit
    )

    return SSHProfileListResponse(
        profiles=profiles, total=total, offset=offset, limit=limit
    )


@router.get(
    "/profiles/{profile_id}",
    response_model=SSHProfileResponse,
    summary="Get SSH Profile",
    description="Get specific SSH profile details",
)
async def get_ssh_profile(
    profile_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SSHProfileResponse:
    """Get specific SSH profile details."""
    service = SSHProfileService(db)
    return await service.get_profile(current_user, profile_id)


@router.put(
    "/profiles/{profile_id}",
    response_model=SSHProfileResponse,
    summary="Update SSH Profile",
    description="Update SSH profile configuration",
)
async def update_ssh_profile(
    profile_id: str,
    update_data: SSHProfileUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SSHProfileResponse:
    """Update SSH profile configuration."""
    service = SSHProfileService(db)
    return await service.update_profile(current_user, profile_id, update_data)


@router.delete(
    "/profiles/{profile_id}",
    response_model=MessageResponse,
    summary="Delete SSH Profile",
    description="Delete SSH profile and cleanup associated data",
)
async def delete_ssh_profile(
    profile_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Delete SSH profile and cleanup associated data."""
    service = SSHProfileService(db)
    await service.delete_profile(current_user, profile_id)

    return MessageResponse(message="SSH profile deleted successfully")


@router.post(
    "/profiles/search",
    response_model=SSHProfileListResponse,
    summary="Search SSH Profiles",
    description="Search SSH profiles with filters and pagination",
)
async def search_ssh_profiles(
    search_request: SSHProfileSearchRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SSHProfileListResponse:
    """Search SSH profiles with filters and pagination."""
    service = SSHProfileService(db)
    profiles, total = await service.search_profiles(current_user, search_request)

    return SSHProfileListResponse(
        profiles=profiles,
        total=total,
        offset=search_request.offset,
        limit=search_request.limit,
    )


@router.get(
    "/profiles/stats",
    response_model=SSHProfileStats,
    summary="Get Profile Statistics",
    description="Get SSH profile usage statistics and analytics",
)
async def get_ssh_profile_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SSHProfileStats:
    """Get SSH profile usage statistics and analytics."""
    service = SSHProfileService(db)
    return await service.get_profile_stats(current_user)


# SSH Key Management Endpoints


@router.post(
    "/keys",
    response_model=SSHKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create SSH Key",
    description="Add SSH key to user's key collection",
)
async def create_ssh_key(
    key_data: SSHKeyCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SSHKeyResponse:
    """Add SSH key to user's key collection."""
    service = SSHKeyService(db)
    return await service.create_key(current_user, key_data)


@router.get(
    "/keys",
    response_model=SSHKeyListResponse,
    summary="List SSH Keys",
    description="Get user's SSH keys with pagination",
)
async def list_ssh_keys(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    active_only: bool = Query(default=True, description="Show only active keys"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    limit: int = Query(default=50, ge=1, le=100, description="Pagination limit"),
) -> SSHKeyListResponse:
    """Get user's SSH keys with pagination."""
    service = SSHKeyService(db)
    keys, total = await service.get_user_keys(
        current_user, active_only=active_only, offset=offset, limit=limit
    )

    return SSHKeyListResponse(keys=keys, total=total, offset=offset, limit=limit)


@router.get(
    "/keys/{key_id}",
    response_model=SSHKeyResponse,
    summary="Get SSH Key",
    description="Get specific SSH key details",
)
async def get_ssh_key(
    key_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SSHKeyResponse:
    """Get specific SSH key details."""
    service = SSHKeyService(db)
    return await service.get_key(current_user, key_id)


@router.put(
    "/keys/{key_id}",
    response_model=SSHKeyResponse,
    summary="Update SSH Key",
    description="Update SSH key metadata",
)
async def update_ssh_key(
    key_id: str,
    update_data: SSHKeyUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SSHKeyResponse:
    """Update SSH key metadata."""
    service = SSHKeyService(db)
    return await service.update_key(current_user, key_id, update_data)


@router.delete(
    "/keys/{key_id}",
    response_model=MessageResponse,
    summary="Delete SSH Key",
    description="Remove SSH key from collection",
)
async def delete_ssh_key(
    key_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Remove SSH key from collection."""
    service = SSHKeyService(db)
    await service.delete_key(current_user, key_id)

    return MessageResponse(message="SSH key deleted successfully")


@router.post(
    "/keys/search",
    response_model=SSHKeyListResponse,
    summary="Search SSH Keys",
    description="Search SSH keys with filters and pagination",
)
async def search_ssh_keys(
    search_request: SSHKeySearchRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SSHKeyListResponse:
    """Search SSH keys with filters and pagination."""
    service = SSHKeyService(db)
    keys, total = await service.search_keys(current_user, search_request)

    return SSHKeyListResponse(
        keys=keys, total=total, offset=search_request.offset, limit=search_request.limit
    )


@router.get(
    "/keys/stats",
    response_model=SSHKeyStats,
    summary="Get Key Statistics",
    description="Get SSH key usage statistics and analytics",
)
async def get_ssh_key_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SSHKeyStats:
    """Get SSH key usage statistics and analytics."""
    service = SSHKeyService(db)
    return await service.get_key_stats(current_user)


# Connection Testing Endpoints


@router.post(
    "/test-connection",
    response_model=SSHConnectionTestResponse,
    summary="Test SSH Connection",
    description="Test SSH connection to validate profile or connection parameters",
)
async def test_ssh_connection(
    test_request: SSHConnectionTestRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SSHConnectionTestResponse:
    """Test SSH connection to validate profile or connection parameters."""
    service = SSHProfileService(db)
    return await service.test_connection(current_user, test_request)


@router.post(
    "/profiles/{profile_id}/test",
    response_model=SSHConnectionTestResponse,
    summary="Test Profile Connection",
    description="Test SSH connection for a specific profile",
)
async def test_profile_connection(
    profile_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    ssh_key_id: str = Query(None, description="SSH key ID for authentication"),
    password: str = Body(None, description="Password for authentication"),
    timeout: int = Query(default=30, ge=5, le=60, description="Connection timeout"),
) -> SSHConnectionTestResponse:
    """Test SSH connection for a specific profile."""
    # Create test request for the profile
    test_request = SSHConnectionTestRequest(
        profile_id=profile_id,
        ssh_key_id=ssh_key_id,
        password=password,
        connect_timeout=timeout,
        auth_method="key" if ssh_key_id else "password",
    )

    service = SSHProfileService(db)
    return await service.test_connection(current_user, test_request)


# Bulk Operations Endpoints


@router.delete(
    "/profiles/bulk",
    response_model=BulkOperationResponse,
    summary="Bulk Delete Profiles",
    description="Delete multiple SSH profiles in a single operation",
)
async def bulk_delete_profiles(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    profile_ids: List[str] = Body(..., description="List of profile IDs to delete"),
) -> BulkOperationResponse:
    """Delete multiple SSH profiles in a single operation."""
    service = SSHProfileService(db)
    success_count = 0
    error_count = 0
    errors = []

    for profile_id in profile_ids:
        try:
            await service.delete_profile(current_user, profile_id)
            success_count += 1
        except HTTPException as e:
            error_count += 1
            errors.append({"profile_id": profile_id, "error": e.detail})
        except Exception as e:
            error_count += 1
            errors.append({"profile_id": profile_id, "error": str(e)})

    message = f"Bulk delete completed: {success_count} successful, {error_count} failed"

    return BulkOperationResponse(
        success_count=success_count,
        error_count=error_count,
        errors=errors if errors else None,
        message=message,
    )


@router.delete(
    "/keys/bulk",
    response_model=BulkOperationResponse,
    summary="Bulk Delete Keys",
    description="Delete multiple SSH keys in a single operation",
)
async def bulk_delete_keys(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    key_ids: List[str] = Body(..., description="List of key IDs to delete"),
) -> BulkOperationResponse:
    """Delete multiple SSH keys in a single operation."""
    service = SSHKeyService(db)
    success_count = 0
    error_count = 0
    errors = []

    for key_id in key_ids:
        try:
            await service.delete_key(current_user, key_id)
            success_count += 1
        except HTTPException as e:
            error_count += 1
            errors.append({"key_id": key_id, "error": e.detail})
        except Exception as e:
            error_count += 1
            errors.append({"key_id": key_id, "error": str(e)})

    message = f"Bulk delete completed: {success_count} successful, {error_count} failed"

    return BulkOperationResponse(
        success_count=success_count,
        error_count=error_count,
        errors=errors if errors else None,
        message=message,
    )


# Health Check Endpoint for SSH Service


@router.get(
    "/health",
    response_model=dict,
    summary="SSH Service Health",
    description="Check SSH service health and connectivity",
)
async def ssh_service_health(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Check SSH service health and connectivity."""
    try:
        # Test basic service functionality
        service = SSHProfileService(db)
        profiles, total = await service.get_user_profiles(
            current_user, active_only=True, offset=0, limit=1
        )

        return {
            "status": "healthy",
            "service": "ssh_management",
            "database": "connected",
            "user_profiles": total,
            "timestamp": logger.get_current_time(),
        }

    except Exception as e:
        logger.error(f"SSH service health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "ssh_management",
            "error": str(e),
            "timestamp": logger.get_current_time(),
        }
