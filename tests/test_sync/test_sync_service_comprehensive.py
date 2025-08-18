"""
Comprehensive tests for SyncService to improve coverage.

This test suite focuses on improving test coverage for the SyncService class
by testing all major methods and code paths with proper mocking.
"""

import hashlib
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest
import redis.asyncio as aioredis
from fastapi import HTTPException

from app.api.sync.schemas import (
    DeviceRegistration,
    SyncDataRequest,
    SyncDataResponse,
    SyncStats,
)
from app.api.sync.service import SyncService
from app.models.sync import SyncData
from app.models.user import User


class TestSyncServiceComprehensive:
    """Comprehensive test coverage for SyncService."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client."""
        return AsyncMock(spec=aioredis.Redis)

    @pytest.fixture
    def mock_sync_repo(self):
        """Create mock sync repository."""
        repo = AsyncMock()
        repo.get_by_sync_key = AsyncMock()
        repo.get_sync_changes_since = AsyncMock()
        repo.count_user_devices = AsyncMock()
        repo.create = AsyncMock()
        repo.get_sync_stats = AsyncMock()
        return repo

    @pytest.fixture
    def sync_service(self, mock_session, mock_redis_client):
        """Create SyncService instance with mocked dependencies."""
        service = SyncService(session=mock_session, redis_client=mock_redis_client)
        return service

    @pytest.fixture
    def test_user(self):
        """Create test user."""
        return User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            created_at=datetime.now(UTC),
        )

    def test_init(self, mock_session, mock_redis_client):
        """Test SyncService initialization."""
        service = SyncService(session=mock_session, redis_client=mock_redis_client)
        
        assert service.session == mock_session
        assert service.redis_client == mock_redis_client
        assert service.sync_repo is not None
        assert service.sync_repository == service.sync_repo  # Test alias
        assert service.pubsub_manager is not None
        assert service.conflict_resolver is not None

    def test_init_without_redis(self, mock_session):
        """Test SyncService initialization without Redis client."""
        service = SyncService(session=mock_session, redis_client=None)
        
        assert service.session == mock_session
        assert service.redis_client is None
        assert service.sync_repo is not None

    def test_normalize_user_id_with_uuid(self, sync_service):
        """Test normalizing user ID when it's already a UUID."""
        test_uuid = uuid4()
        result = sync_service._normalize_user_id(test_uuid)
        assert result == test_uuid

    def test_normalize_user_id_with_valid_string(self, sync_service):
        """Test normalizing user ID from valid UUID string."""
        test_uuid = uuid4()
        test_string = str(test_uuid)
        result = sync_service._normalize_user_id(test_string)
        assert result == test_uuid

    def test_normalize_user_id_with_invalid_string(self, sync_service):
        """Test normalizing user ID from invalid UUID string."""
        test_string = "invalid-uuid-string"
        result = sync_service._normalize_user_id(test_string)
        
        # Should return MD5 hash as UUID
        expected_hash = hashlib.md5(test_string.encode()).hexdigest()
        expected_uuid = UUID(expected_hash)
        assert result == expected_uuid

    @pytest.mark.asyncio
    async def test_sync_data_with_string_user_id_no_conflict(self, sync_service, mock_sync_repo):
        """Test sync_data with string user_id (test interface) - no conflict."""
        sync_service.sync_repository = mock_sync_repo
        mock_sync_repo.get_by_sync_key.return_value = None
        
        user_id = "test-user-123"
        sync_data = {
            "sync_key": "test-key",
            "version": 1,
            "data": {"test": "data"}
        }
        
        result = await sync_service.sync_data(user_id, sync_data)
        
        assert isinstance(result, SyncDataResponse)
        assert result.total_items == 1
        assert result.device_count == 1
        assert len(result.conflicts) == 0

    @pytest.mark.asyncio
    async def test_sync_data_with_string_user_id_with_conflict(self, sync_service, mock_sync_repo):
        """Test sync_data with string user_id (test interface) - with conflict."""
        sync_service.sync_repository = mock_sync_repo
        
        # Mock existing sync data with different version
        existing_sync = Mock()
        existing_sync.version = 2
        mock_sync_repo.get_by_sync_key.return_value = existing_sync
        
        user_id = "test-user-123"
        sync_data = {
            "sync_key": "test-key",
            "version": 1,
            "data": {"test": "data"}
        }
        
        result = await sync_service.sync_data(user_id, sync_data)
        
        assert isinstance(result, SyncDataResponse)
        assert result.total_items == 0
        assert result.conflict_type == "version_mismatch"

    @pytest.mark.asyncio
    async def test_sync_data_with_string_user_id_sync_repo_mock_error(self, sync_service, mock_sync_repo):
        """Test sync_data with mock repository that raises TypeError."""
        sync_service.sync_repository = mock_sync_repo
        
        # Mock async method to raise TypeError, then sync method to return value
        mock_sync_repo.get_by_sync_key.side_effect = [TypeError(), None]
        
        user_id = "test-user-123"
        sync_data = {
            "sync_key": "test-key",
            "version": 1,
            "data": {"test": "data"}
        }
        
        result = await sync_service.sync_data(user_id, sync_data)
        
        assert isinstance(result, SyncDataResponse)
        assert result.total_items == 1

    @pytest.mark.asyncio
    async def test_sync_data_with_user_object(self, sync_service, test_user, mock_sync_repo):
        """Test sync_data with User object (production interface)."""
        sync_service.sync_repo = mock_sync_repo
        
        # Mock repository responses
        mock_sync_repo.get_sync_changes_since.return_value = [
            {"id": 1, "data": "test1"},
            {"id": 2, "data": "test2"}
        ]
        mock_sync_repo.count_user_devices.return_value = 3
        
        from app.api.sync.schemas import SyncDataType
        request = SyncDataRequest(
            data_types=[SyncDataType.COMMANDS, SyncDataType.SSH_PROFILES],
            last_sync_timestamp=datetime.now(UTC) - timedelta(hours=1)
        )
        
        result = await sync_service.sync_data(test_user, request)
        
        assert isinstance(result, SyncDataResponse)
        assert result.total_items == 2
        assert result.device_count == 3
        assert len(result.conflicts) == 0
        assert "commands" in result.data
        assert "ssh_profiles" in result.data

    @pytest.mark.asyncio
    async def test_sync_data_with_user_object_no_last_sync(self, sync_service, test_user, mock_sync_repo):
        """Test sync_data with User object and no last sync timestamp."""
        sync_service.sync_repo = mock_sync_repo
        
        mock_sync_repo.get_sync_changes_since.return_value = []
        mock_sync_repo.count_user_devices.return_value = 1
        
        from app.api.sync.schemas import SyncDataType
        request = SyncDataRequest(
            data_types=[SyncDataType.COMMANDS],
            last_sync_timestamp=None
        )
        
        result = await sync_service.sync_data(test_user, request)
        
        assert isinstance(result, SyncDataResponse)
        assert result.total_items == 0
        assert result.device_count == 1

    @pytest.mark.asyncio
    async def test_sync_data_exception_handling(self, sync_service, test_user, mock_sync_repo):
        """Test sync_data exception handling."""
        sync_service.sync_repo = mock_sync_repo
        mock_sync_repo.get_sync_changes_since.side_effect = Exception("Database error")
        
        from app.api.sync.schemas import SyncDataType
        request = SyncDataRequest(
            data_types=[SyncDataType.COMMANDS],
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await sync_service.sync_data(test_user, request)
        
        assert exc_info.value.status_code == 500
        assert "Failed to synchronize data" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_sync_data_success(self, sync_service, test_user, mock_sync_repo):
        """Test successful upload_sync_data."""
        sync_service.sync_repo = mock_sync_repo
        mock_sync_repo.create.return_value = None
        
        data = {"test": "upload_data", "timestamp": datetime.now(UTC).isoformat()}
        
        result = await sync_service.upload_sync_data(test_user, data)
        
        assert result is True
        mock_sync_repo.create.assert_called_once()
        sync_service.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_sync_data_exception(self, sync_service, test_user, mock_sync_repo):
        """Test upload_sync_data exception handling."""
        sync_service.sync_repo = mock_sync_repo
        mock_sync_repo.create.side_effect = Exception("Database error")
        
        data = {"test": "upload_data"}
        
        with pytest.raises(HTTPException) as exc_info:
            await sync_service.upload_sync_data(test_user, data)
        
        assert exc_info.value.status_code == 500
        assert "Failed to upload sync data" in str(exc_info.value.detail)
        sync_service.session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_sync_stats_success(self, sync_service, test_user, mock_sync_repo):
        """Test successful get_sync_stats."""
        sync_service.sync_repo = mock_sync_repo
        
        mock_stats = {
            "total_syncs": 100,
            "successful_syncs": 95,
            "failed_syncs": 5,
            "last_sync": datetime.now(UTC),
            "active_devices": 3,
            "total_conflicts": 10,
            "resolved_conflicts": 8,
        }
        mock_sync_repo.get_sync_stats.return_value = mock_stats
        
        result = await sync_service.get_sync_stats(test_user)
        
        assert isinstance(result, SyncStats)
        assert result.total_syncs == 100
        assert result.successful_syncs == 95
        assert result.failed_syncs == 5
        assert result.active_devices == 3
        assert result.total_conflicts == 10
        assert result.resolved_conflicts == 8

    @pytest.mark.asyncio
    async def test_get_sync_stats_with_defaults(self, sync_service, test_user, mock_sync_repo):
        """Test get_sync_stats with missing data (defaults)."""
        sync_service.sync_repo = mock_sync_repo
        mock_sync_repo.get_sync_stats.return_value = {}
        
        result = await sync_service.get_sync_stats(test_user)
        
        assert isinstance(result, SyncStats)
        assert result.total_syncs == 0
        assert result.successful_syncs == 0
        assert result.failed_syncs == 0
        assert result.active_devices == 0
        assert result.total_conflicts == 0
        assert result.resolved_conflicts == 0
        assert result.last_sync is None

    @pytest.mark.asyncio
    async def test_get_sync_stats_exception(self, sync_service, test_user, mock_sync_repo):
        """Test get_sync_stats exception handling."""
        sync_service.sync_repo = mock_sync_repo
        mock_sync_repo.get_sync_stats.side_effect = Exception("Database error")
        
        with pytest.raises(HTTPException) as exc_info:
            await sync_service.get_sync_stats(test_user)
        
        assert exc_info.value.status_code == 500
        assert "Failed to get sync statistics" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_sync_data_with_string_user_id(self, sync_service, mock_sync_repo):
        """Test create_sync_data with string user ID."""
        sync_service.sync_repo = mock_sync_repo
        
        # Mock SyncData.create_sync_item
        mock_sync_item = Mock(spec=SyncData)
        with patch.object(SyncData, 'create_sync_item', return_value=mock_sync_item):
            mock_sync_repo.create.return_value = mock_sync_item
            
            user_id = "test-user-123"
            sync_data = {
                "sync_type": "commands",
                "sync_key": "test-key",
                "data": {"test": "data"},
                "source_device_id": "device-123",
                "source_device_type": "mobile",
            }
            
            result = await sync_service.create_sync_data(user_id, sync_data)
            
            assert result == mock_sync_item
            mock_sync_repo.create.assert_called_once_with(mock_sync_item)
            sync_service.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_sync_data_with_uuid_user_id(self, sync_service, mock_sync_repo):
        """Test create_sync_data with UUID user ID."""
        sync_service.sync_repo = mock_sync_repo
        
        mock_sync_item = Mock(spec=SyncData)
        with patch.object(SyncData, 'create_sync_item', return_value=mock_sync_item):
            mock_sync_repo.create.return_value = mock_sync_item
            
            user_id = uuid4()
            sync_data = {
                "sync_type": "ssh_profiles",
                "sync_key": "profile-key",
                "data": {"profile": "data"},
            }
            
            result = await sync_service.create_sync_data(user_id, sync_data)
            
            assert result == mock_sync_item
            mock_sync_repo.create.assert_called_once_with(mock_sync_item)

    @pytest.mark.asyncio
    async def test_create_sync_data_exception(self, sync_service, mock_sync_repo):
        """Test create_sync_data exception handling."""
        sync_service.sync_repo = mock_sync_repo
        
        with patch.object(SyncData, 'create_sync_item', side_effect=Exception("Creation error")):
            user_id = uuid4()
            sync_data = {"sync_type": "commands", "data": {}}
            
            with pytest.raises(HTTPException) as exc_info:
                await sync_service.create_sync_data(user_id, sync_data)
            
            assert exc_info.value.status_code == 500
            assert "Failed to create sync data" in str(exc_info.value.detail)
            sync_service.session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_sync_data_with_minimal_data(self, sync_service, mock_sync_repo):
        """Test create_sync_data with minimal sync data."""
        sync_service.sync_repo = mock_sync_repo
        
        mock_sync_item = Mock(spec=SyncData)
        with patch.object(SyncData, 'create_sync_item', return_value=mock_sync_item):
            mock_sync_repo.create.return_value = mock_sync_item
            
            user_id = uuid4()
            sync_data = {}  # Minimal data, should use defaults
            
            result = await sync_service.create_sync_data(user_id, sync_data)
            
            assert result == mock_sync_item
            # Verify defaults were used
            SyncData.create_sync_item.assert_called_once()
            call_args = SyncData.create_sync_item.call_args
            assert call_args[1]["sync_type"] == "unknown"
            assert call_args[1]["sync_key"] == ""
            assert call_args[1]["data"] == {}
            assert call_args[1]["device_id"] == "unknown"
            assert call_args[1]["device_type"] == "unknown"

    @pytest.mark.asyncio
    async def test_merge_data(self, sync_service):
        """Test merge_data delegates to conflict resolver."""
        local_data = {"key1": "local_value", "key2": "shared"}
        remote_data = {"key1": "remote_value", "key3": "remote_only"}
        
        # Mock the conflict resolver
        sync_service.conflict_resolver.resolve = AsyncMock(
            return_value={"key1": "remote_value", "key2": "shared", "key3": "remote_only"}
        )
        
        result = await sync_service.merge_data(local_data, remote_data, "last_write_wins")
        
        sync_service.conflict_resolver.resolve.assert_called_once_with(
            local_data, remote_data, "last_write_wins"
        )
        assert result == {"key1": "remote_value", "key2": "shared", "key3": "remote_only"}

    @pytest.mark.asyncio
    async def test_notify_sync_update_with_redis(self, sync_service):
        """Test notify_sync_update with Redis client."""
        sync_service.pubsub_manager.publish_sync_update = AsyncMock()
        
        user_id = uuid4()
        sync_data = {"test": "notification_data"}
        
        await sync_service.notify_sync_update(user_id, sync_data)
        
        sync_service.pubsub_manager.publish_sync_update.assert_called_once_with(
            user_id, sync_data
        )

    @pytest.mark.asyncio
    async def test_notify_sync_update_without_redis_client(self, sync_service):
        """Test notify_sync_update when pubsub manager has no Redis client."""
        sync_service.pubsub_manager.redis_client = None
        sync_service.pubsub_manager.publish_sync_update = AsyncMock()
        
        user_id = "test-user"
        sync_data = {"test": "data"}
        
        await sync_service.notify_sync_update(user_id, sync_data)
        
        # Should set redis_client on pubsub_manager
        assert sync_service.pubsub_manager.redis_client == sync_service.redis_client
        sync_service.pubsub_manager.publish_sync_update.assert_called_once_with(
            user_id, sync_data
        )

    @pytest.mark.asyncio
    async def test_notify_sync_update_exception_handling(self, sync_service):
        """Test notify_sync_update exception handling."""
        sync_service.pubsub_manager.publish_sync_update = AsyncMock(
            side_effect=Exception("Redis error")
        )
        
        user_id = uuid4()
        sync_data = {"test": "data"}
        
        # Should not raise exception, just log error
        await sync_service.notify_sync_update(user_id, sync_data)

    @pytest.mark.asyncio
    async def test_register_device_with_device_id(self, sync_service):
        """Test register_device with existing device ID."""
        sync_service.pubsub_manager.register_device_activity = AsyncMock()
        
        user_id = uuid4()
        device_data = DeviceRegistration(
            device_id="existing-device-123",
            device_name="Test Device",
            device_type="mobile",
            os_info="iOS 15.0",
            app_version="1.0.0",
            sync_enabled=False,
        )
        
        result = await sync_service.register_device(user_id, device_data)
        
        assert isinstance(result, DeviceRegistration)
        assert result.device_id == "existing-device-123"
        assert result.device_name == "Test Device"
        assert result.sync_enabled is True  # Should be enabled after registration
        sync_service.pubsub_manager.register_device_activity.assert_called_once_with(
            user_id, "existing-device-123"
        )

    @pytest.mark.asyncio
    async def test_register_device_without_device_id(self, sync_service):
        """Test register_device without device ID (should generate one)."""
        sync_service.pubsub_manager.register_device_activity = AsyncMock()
        
        user_id = "test-user"
        device_data = DeviceRegistration(
            device_name="Test Device",
            device_type="desktop",
            os_info="Windows 11",
            app_version="2.0.0",
        )
        
        with patch('app.api.sync.service.datetime') as mock_datetime:
            mock_datetime.now.return_value.timestamp.return_value = 1234567890.0
            
            result = await sync_service.register_device(user_id, device_data)
        
        assert isinstance(result, DeviceRegistration)
        assert result.device_id == "device_1234567890.0"
        assert result.device_name == "Test Device"
        assert result.sync_enabled is True

    @pytest.mark.asyncio
    async def test_register_device_without_redis(self, sync_service):
        """Test register_device without Redis client."""
        sync_service.redis_client = None
        
        user_id = uuid4()
        device_data = DeviceRegistration(
            device_id="test-device",
            device_name="Test Device",
            device_type="mobile",
        )
        
        result = await sync_service.register_device(user_id, device_data)
        
        assert isinstance(result, DeviceRegistration)
        assert result.device_id == "test-device"

    @pytest.mark.asyncio
    async def test_register_device_exception(self, sync_service):
        """Test register_device exception handling."""
        sync_service.pubsub_manager.register_device_activity = AsyncMock(
            side_effect=Exception("Redis error")
        )
        
        user_id = uuid4()
        device_data = DeviceRegistration(
            device_id="test-device",
            device_name="Test Device",
            device_type="mobile",
        )
        
        with pytest.raises(Exception, match="Redis error"):
            await sync_service.register_device(user_id, device_data)

    @pytest.mark.asyncio
    async def test_get_pending_sync_with_uuid(self, sync_service, mock_sync_repo):
        """Test get_pending_sync with UUID user_id."""
        sync_service.sync_repo = mock_sync_repo
        
        mock_sync_data = [
            Mock(spec=SyncData),
            Mock(spec=SyncData),
        ]
        mock_sync_repo.get_sync_changes_since.return_value = mock_sync_data
        
        user_id = uuid4()
        device_id = "device-123"
        
        result = await sync_service.get_pending_sync(user_id, device_id)
        
        assert result == mock_sync_data
        mock_sync_repo.get_sync_changes_since.assert_called_once()
        call_args = mock_sync_repo.get_sync_changes_since.call_args
        assert call_args[0][0] == user_id
        assert call_args[1]["device_id"] == device_id

    @pytest.mark.asyncio
    async def test_get_pending_sync_with_string_user_id(self, sync_service, mock_sync_repo):
        """Test get_pending_sync with string user_id."""
        sync_service.sync_repo = mock_sync_repo
        mock_sync_repo.get_sync_changes_since.return_value = []
        
        user_id = str(uuid4())
        device_id = "device-456"
        
        result = await sync_service.get_pending_sync(user_id, device_id)
        
        assert result == []
        mock_sync_repo.get_sync_changes_since.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pending_sync_exception(self, sync_service, mock_sync_repo):
        """Test get_pending_sync exception handling."""
        sync_service.sync_repo = mock_sync_repo
        mock_sync_repo.get_sync_changes_since.side_effect = Exception("Database error")
        
        user_id = uuid4()
        device_id = "device-789"
        
        with pytest.raises(Exception, match="Database error"):
            await sync_service.get_pending_sync(user_id, device_id)

    @pytest.mark.asyncio
    async def test_resolve_conflict_merge_resolution(self, sync_service, mock_sync_repo):
        """Test resolve_conflict with merge resolution."""
        sync_service.sync_repo = mock_sync_repo
        
        # Mock sync item with conflict
        mock_sync_item = Mock(spec=SyncData)
        mock_sync_item.has_conflict = True
        mock_sync_item.data = {"original": "data"}
        mock_sync_item.resolve_conflict = Mock()
        mock_sync_repo.get_by_sync_key.return_value = mock_sync_item
        mock_sync_repo.update = AsyncMock()
        
        from app.api.sync.schemas import SyncConflictResolution
        user_id = uuid4()
        conflict_resolution = SyncConflictResolution(
            conflict_id="conflict-123",
            resolution="merge",
            resolved_data={"merged": "data"},
        )
        
        result = await sync_service.resolve_conflict(user_id, conflict_resolution)
        
        assert result == mock_sync_item
        mock_sync_item.resolve_conflict.assert_called_once_with(
            {"merged": "data"}, "system", "api"
        )
        mock_sync_repo.update.assert_called_once_with(mock_sync_item)
        sync_service.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_resolve_conflict_local_resolution(self, sync_service, mock_sync_repo):
        """Test resolve_conflict with local resolution."""
        sync_service.sync_repo = mock_sync_repo
        
        mock_sync_item = Mock(spec=SyncData)
        mock_sync_item.has_conflict = True
        mock_sync_item.data = {"local": "data"}
        mock_sync_item.resolve_conflict = Mock()
        mock_sync_repo.get_by_sync_key.return_value = mock_sync_item
        mock_sync_repo.update = AsyncMock()
        
        from app.api.sync.schemas import SyncConflictResolution
        user_id = "test-user"
        conflict_resolution = SyncConflictResolution(
            conflict_id="conflict-456",
            resolution="local",
        )
        
        result = await sync_service.resolve_conflict(user_id, conflict_resolution)
        
        assert result == mock_sync_item
        mock_sync_item.resolve_conflict.assert_called_once_with(
            {"local": "data"}, "system", "api"
        )

    @pytest.mark.asyncio
    async def test_resolve_conflict_remote_resolution(self, sync_service, mock_sync_repo):
        """Test resolve_conflict with remote resolution."""
        sync_service.sync_repo = mock_sync_repo
        
        mock_sync_item = Mock(spec=SyncData)
        mock_sync_item.has_conflict = True
        mock_sync_item.data = {"local": "data"}
        mock_sync_item.conflict_data = {"conflicting_data": {"remote": "data"}}
        mock_sync_item.resolve_conflict = Mock()
        mock_sync_repo.get_by_sync_key.return_value = mock_sync_item
        mock_sync_repo.update = AsyncMock()
        
        from app.api.sync.schemas import SyncConflictResolution
        user_id = uuid4()
        conflict_resolution = SyncConflictResolution(
            conflict_id="conflict-789",
            resolution="remote",
        )
        
        result = await sync_service.resolve_conflict(user_id, conflict_resolution)
        
        mock_sync_item.resolve_conflict.assert_called_once_with(
            {"remote": "data"}, "system", "api"
        )

    @pytest.mark.asyncio
    async def test_resolve_conflict_default_resolution(self, sync_service, mock_sync_repo):
        """Test resolve_conflict with unknown resolution type."""
        sync_service.sync_repo = mock_sync_repo
        
        mock_sync_item = Mock(spec=SyncData)
        mock_sync_item.has_conflict = True
        mock_sync_item.data = {"default": "data"}
        mock_sync_item.resolve_conflict = Mock()
        mock_sync_repo.get_by_sync_key.return_value = mock_sync_item
        mock_sync_repo.update = AsyncMock()
        
        from app.api.sync.schemas import SyncConflictResolution
        user_id = uuid4()
        conflict_resolution = SyncConflictResolution(
            conflict_id="conflict-default",
            resolution="unknown_type",
        )
        
        result = await sync_service.resolve_conflict(user_id, conflict_resolution)
        
        mock_sync_item.resolve_conflict.assert_called_once_with(
            {"default": "data"}, "system", "api"
        )

    @pytest.mark.asyncio
    async def test_resolve_conflict_no_conflict(self, sync_service, mock_sync_repo):
        """Test resolve_conflict when sync item has no conflict."""
        sync_service.sync_repo = mock_sync_repo
        
        mock_sync_item = Mock(spec=SyncData)
        mock_sync_item.has_conflict = False
        mock_sync_repo.get_by_sync_key.return_value = mock_sync_item
        
        from app.api.sync.schemas import SyncConflictResolution
        user_id = uuid4()
        conflict_resolution = SyncConflictResolution(
            conflict_id="no-conflict",
            resolution="merge",
        )
        
        result = await sync_service.resolve_conflict(user_id, conflict_resolution)
        
        assert result == mock_sync_item
        # Should not call resolve_conflict or update
        assert not hasattr(mock_sync_item, 'resolve_conflict') or not mock_sync_item.resolve_conflict.called

    @pytest.mark.asyncio
    async def test_resolve_conflict_not_found(self, sync_service, mock_sync_repo):
        """Test resolve_conflict when sync item is not found."""
        sync_service.sync_repo = mock_sync_repo
        mock_sync_repo.get_by_sync_key.return_value = None
        
        from app.api.sync.schemas import SyncConflictResolution
        user_id = uuid4()
        conflict_resolution = SyncConflictResolution(
            conflict_id="not-found",
            resolution="merge",
        )
        
        result = await sync_service.resolve_conflict(user_id, conflict_resolution)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_conflict_exception(self, sync_service, mock_sync_repo):
        """Test resolve_conflict exception handling."""
        sync_service.sync_repo = mock_sync_repo
        mock_sync_repo.get_by_sync_key.side_effect = Exception("Database error")
        
        from app.api.sync.schemas import SyncConflictResolution
        user_id = uuid4()
        conflict_resolution = SyncConflictResolution(
            conflict_id="error-case",
            resolution="merge",
        )
        
        with pytest.raises(Exception, match="Database error"):
            await sync_service.resolve_conflict(user_id, conflict_resolution)
        
        sync_service.session.rollback.assert_called_once()