"""
Real-time Synchronization Tests for DevPocket API.

Tests multi-device synchronization functionality including:
- Command history synchronization
- SSH profile synchronization
- User settings synchronization
- Conflict resolution
- Real-time updates via Redis pub/sub
- Offline/online sync scenarios
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List

import redis.asyncio as aioredis

from app.api.sync.service import SyncService
from app.api.sync.schemas import (
    SyncDataRequest,
    SyncDataResponse,
    SyncConflictResponse,
    DeviceRegistration
)
from app.models.sync import SyncData
from app.repositories.sync import SyncRepository


class TestSyncService:
    """Test synchronization service functionality."""

    @pytest.fixture
    def sync_service(self):
        """Create sync service instance."""
        return SyncService()

    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client."""
        redis_client = AsyncMock(spec=aioredis.Redis)
        return redis_client

    @pytest.fixture
    def mock_sync_repository(self):
        """Mock sync repository."""
        repository = AsyncMock(spec=SyncRepository)
        return repository

    @pytest.fixture
    def sample_sync_data(self):
        """Sample synchronization data."""
        return {
            "sync_type": "command_history",
            "sync_key": "user-123-device-456",
            "data": {
                "command": "ls -la",
                "output": "file1.txt\nfile2.txt",
                "timestamp": datetime.utcnow().isoformat()
            },
            "version": 1,
            "source_device_id": "device-456",
            "source_device_type": "mobile"
        }

    @pytest.mark.asyncio
    async def test_sync_data_create(self, sync_service, sample_sync_data):
        """Test creating new sync data."""
        # Arrange
        user_id = "user-123"
        
        with patch.object(sync_service, 'sync_repository') as mock_repo:
            mock_repo.create.return_value = SyncData(**sample_sync_data, user_id=user_id)
            
            # Act
            result = await sync_service.create_sync_data(user_id, sample_sync_data)
            
            # Assert
            assert result.sync_type == "command_history"
            assert result.user_id == user_id
            mock_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_data_conflict_detection(self, sync_service, sample_sync_data):
        """Test detecting sync conflicts."""
        # Arrange
        user_id = "user-123"
        existing_data = sample_sync_data.copy()
        existing_data["version"] = 2
        existing_data["source_device_id"] = "device-789"
        
        with patch.object(sync_service, 'sync_repository') as mock_repo:
            mock_repo.get_by_sync_key.return_value = SyncData(**existing_data, user_id=user_id)
            
            # Act
            result = await sync_service.sync_data(user_id, sample_sync_data)
            
            # Assert
            assert isinstance(result, SyncConflictResponse)
            assert result.conflict_type == "version_mismatch"

    @pytest.mark.asyncio
    async def test_sync_data_merge_strategy(self, sync_service):
        """Test different merge strategies for conflicts."""
        # Arrange
        user_id = "user-123"
        local_data = {
            "sync_type": "user_settings",
            "data": {
                "theme": "dark",
                "font_size": 14,
                "modified_at": "2025-08-16T10:00:00Z"
            }
        }
        remote_data = {
            "sync_type": "user_settings", 
            "data": {
                "theme": "light",
                "font_size": 16,
                "modified_at": "2025-08-16T11:00:00Z"
            }
        }
        
        # Act - Last-write-wins strategy
        merged = await sync_service.merge_data(local_data, remote_data, strategy="last_write_wins")
        
        # Assert
        assert merged["data"]["theme"] == "light"  # Remote wins (later timestamp)
        assert merged["data"]["font_size"] == 16

    @pytest.mark.asyncio
    async def test_real_time_sync_notification(self, sync_service, mock_redis_client):
        """Test real-time sync notifications via Redis pub/sub."""
        # Arrange
        user_id = "user-123"
        sync_data = {"sync_type": "command_history", "data": {"command": "pwd"}}
        
        with patch.object(sync_service, 'redis_client', mock_redis_client):
            # Act
            await sync_service.notify_sync_update(user_id, sync_data)
            
            # Assert
            mock_redis_client.publish.assert_called_once()
            call_args = mock_redis_client.publish.call_args
            assert call_args[0][0] == f"sync:user:{user_id}"

    @pytest.mark.asyncio
    async def test_device_registration(self, sync_service):
        """Test device registration for sync."""
        # Arrange
        user_id = "user-123"
        device_data = DeviceRegistration(
            device_id="device-456",
            device_type="mobile",
            device_name="iPhone 12",
            app_version="1.0.0"
        )
        
        # Act
        result = await sync_service.register_device(user_id, device_data)
        
        # Assert
        assert result.device_id == "device-456"
        assert result.sync_enabled is True

    @pytest.mark.asyncio
    async def test_sync_queue_processing(self, sync_service):
        """Test processing sync queue for offline devices."""
        # Arrange
        user_id = "user-123"
        device_id = "device-456"
        
        with patch.object(sync_service, 'sync_repository') as mock_repo:
            mock_repo.get_pending_sync.return_value = [
                SyncData(sync_type="command_history", data={"command": "ls"}),
                SyncData(sync_type="ssh_profile", data={"name": "server1"})
            ]
            
            # Act
            pending_sync = await sync_service.get_pending_sync(user_id, device_id)
            
            # Assert
            assert len(pending_sync) == 2
            assert pending_sync[0].sync_type == "command_history"


class TestCommandHistorySync:
    """Test command history synchronization."""

    @pytest.fixture
    def command_sync_service(self):
        """Create command sync service."""
        from app.api.sync.services.command_sync import CommandSyncService
        return CommandSyncService()

    @pytest.mark.asyncio
    async def test_command_history_sync_upload(self, command_sync_service):
        """Test uploading command history for sync."""
        # Arrange
        user_id = "user-123"
        commands = [
            {"command": "ls -la", "output": "files...", "timestamp": "2025-08-16T10:00:00Z"},
            {"command": "pwd", "output": "/home/user", "timestamp": "2025-08-16T10:01:00Z"}
        ]
        
        # Act
        result = await command_sync_service.sync_commands(user_id, commands)
        
        # Assert
        assert result.synced_count == 2
        assert result.conflicts == []

    @pytest.mark.asyncio
    async def test_command_history_sync_download(self, command_sync_service):
        """Test downloading command history for sync."""
        # Arrange
        user_id = "user-123"
        device_id = "device-456"
        last_sync = datetime.utcnow() - timedelta(hours=1)
        
        # Act
        result = await command_sync_service.get_commands_since(user_id, device_id, last_sync)
        
        # Assert
        assert isinstance(result, list)
        # Should return commands created after last_sync

    @pytest.mark.asyncio
    async def test_command_deduplication(self, command_sync_service):
        """Test command deduplication during sync."""
        # Arrange
        user_id = "user-123"
        duplicate_commands = [
            {"command": "ls -la", "timestamp": "2025-08-16T10:00:00Z"},
            {"command": "ls -la", "timestamp": "2025-08-16T10:00:00Z"}  # Duplicate
        ]
        
        # Act
        result = await command_sync_service.sync_commands(user_id, duplicate_commands)
        
        # Assert
        assert result.synced_count == 1  # Should deduplicate
        assert result.duplicates_removed == 1


class TestSSHProfileSync:
    """Test SSH profile synchronization."""

    @pytest.fixture
    def ssh_sync_service(self):
        """Create SSH profile sync service."""
        from app.api.sync.services.ssh_sync import SSHProfileSyncService
        return SSHProfileSyncService()

    @pytest.mark.asyncio
    async def test_ssh_profile_sync(self, ssh_sync_service):
        """Test SSH profile synchronization."""
        # Arrange
        user_id = "user-123"
        profiles = [
            {
                "name": "production-server",
                "host": "prod.example.com",
                "port": 22,
                "username": "deploy"
            }
        ]
        
        # Act
        result = await ssh_sync_service.sync_profiles(user_id, profiles)
        
        # Assert
        assert result.synced_count == 1

    @pytest.mark.asyncio
    async def test_ssh_profile_conflict_resolution(self, ssh_sync_service):
        """Test SSH profile conflict resolution."""
        # Arrange - Same profile modified on different devices
        user_id = "user-123"
        local_profile = {
            "name": "server1",
            "host": "old.example.com",
            "modified_at": "2025-08-16T10:00:00Z"
        }
        remote_profile = {
            "name": "server1", 
            "host": "new.example.com",
            "modified_at": "2025-08-16T11:00:00Z"
        }
        
        # Act
        result = await ssh_sync_service.resolve_profile_conflict(
            local_profile, remote_profile
        )
        
        # Assert
        assert result["host"] == "new.example.com"  # Remote wins (later timestamp)

    @pytest.mark.asyncio
    async def test_ssh_key_sync_security(self, ssh_sync_service):
        """Test SSH key synchronization security."""
        # SSH keys should be handled carefully during sync
        # Private keys should not be synced, only public keys and metadata
        
        # Arrange
        user_id = "user-123"
        ssh_key_data = {
            "name": "my-key",
            "public_key": "ssh-rsa AAAAB3...",
            "fingerprint": "SHA256:abc123...",
            # private_key should NOT be included in sync
        }
        
        # Act
        result = await ssh_sync_service.sync_ssh_keys(user_id, [ssh_key_data])
        
        # Assert
        assert "private_key" not in result.synced_data[0]
        assert result.synced_data[0]["public_key"] == ssh_key_data["public_key"]


class TestUserSettingsSync:
    """Test user settings synchronization."""

    @pytest.fixture
    def settings_sync_service(self):
        """Create user settings sync service."""
        from app.api.sync.services.settings_sync import SettingsSyncService
        return SettingsSyncService()

    @pytest.mark.asyncio
    async def test_settings_sync_granular(self, settings_sync_service):
        """Test granular settings synchronization."""
        # Arrange
        user_id = "user-123"
        settings_update = {
            "terminal_theme": "dark",
            "terminal_font_size": 16,
            "ai_suggestions_enabled": True
        }
        
        # Act
        result = await settings_sync_service.sync_settings(user_id, settings_update)
        
        # Assert
        assert result.updated_settings == ["terminal_theme", "terminal_font_size", "ai_suggestions_enabled"]

    @pytest.mark.asyncio
    async def test_settings_partial_sync(self, settings_sync_service):
        """Test partial settings synchronization."""
        # Only sync changed settings, not entire settings object
        
        # Arrange
        user_id = "user-123"
        current_settings = {
            "terminal_theme": "light",
            "terminal_font_size": 14,
            "ai_suggestions_enabled": True
        }
        new_settings = {
            "terminal_theme": "dark",  # Changed
            "terminal_font_size": 14,  # Unchanged
            "ai_suggestions_enabled": True  # Unchanged
        }
        
        # Act
        diff = await settings_sync_service.calculate_settings_diff(
            current_settings, new_settings
        )
        
        # Assert
        assert diff == {"terminal_theme": "dark"}


class TestSyncConflictResolution:
    """Test sync conflict resolution strategies."""

    @pytest.fixture
    def conflict_resolver(self):
        """Create conflict resolver."""
        from app.api.sync.services.conflict_resolver import ConflictResolver
        return ConflictResolver()

    @pytest.mark.asyncio
    async def test_last_write_wins_strategy(self, conflict_resolver):
        """Test last-write-wins conflict resolution."""
        # Arrange
        local_data = {"value": "A", "timestamp": "2025-08-16T10:00:00Z"}
        remote_data = {"value": "B", "timestamp": "2025-08-16T11:00:00Z"}
        
        # Act
        result = await conflict_resolver.resolve(
            local_data, remote_data, strategy="last_write_wins"
        )
        
        # Assert
        assert result["value"] == "B"  # Remote is newer

    @pytest.mark.asyncio
    async def test_user_choice_strategy(self, conflict_resolver):
        """Test user choice conflict resolution."""
        # Arrange
        local_data = {"ssh_profiles": [{"name": "server1", "host": "old.com"}]}
        remote_data = {"ssh_profiles": [{"name": "server1", "host": "new.com"}]}
        user_choice = "local"
        
        # Act
        result = await conflict_resolver.resolve(
            local_data, remote_data, 
            strategy="user_choice", 
            user_preference=user_choice
        )
        
        # Assert
        assert result["ssh_profiles"][0]["host"] == "old.com"

    @pytest.mark.asyncio
    async def test_merge_strategy(self, conflict_resolver):
        """Test merge conflict resolution strategy."""
        # Arrange
        local_data = {"commands": ["ls", "pwd"]}
        remote_data = {"commands": ["cd", "grep"]}
        
        # Act
        result = await conflict_resolver.resolve(
            local_data, remote_data, strategy="merge"
        )
        
        # Assert
        assert set(result["commands"]) == {"ls", "pwd", "cd", "grep"}


class TestOfflineOnlineSync:
    """Test offline/online synchronization scenarios."""

    @pytest.mark.asyncio
    async def test_offline_queue_accumulation(self):
        """Test accumulating sync data while offline."""
        # Test that changes are queued when device is offline
        pass

    @pytest.mark.asyncio
    async def test_online_sync_batch_processing(self):
        """Test batch processing of accumulated changes when coming online."""
        # Test efficient sync of accumulated offline changes
        pass

    @pytest.mark.asyncio
    async def test_partial_sync_recovery(self):
        """Test recovery from partial sync failures."""
        # Test handling interrupted sync operations
        pass


class TestSyncPerformance:
    """Test synchronization performance."""

    @pytest.mark.asyncio
    async def test_large_dataset_sync(self):
        """Test syncing large datasets efficiently."""
        # Test performance with large command histories
        pass

    @pytest.mark.asyncio
    async def test_incremental_sync(self):
        """Test incremental synchronization."""
        # Test syncing only changes since last sync
        pass

    @pytest.mark.asyncio
    async def test_concurrent_device_sync(self):
        """Test synchronization from multiple devices simultaneously."""
        # Test handling multiple devices syncing at once
        pass


class TestSyncSecurity:
    """Test synchronization security."""

    @pytest.mark.asyncio
    async def test_sync_data_encryption(self):
        """Test encryption of sensitive sync data."""
        # Test that sensitive data is encrypted during sync
        pass

    @pytest.mark.asyncio
    async def test_sync_access_control(self):
        """Test sync access control and authorization."""
        # Test that users can only sync their own data
        pass

    @pytest.mark.asyncio
    async def test_sync_audit_logging(self):
        """Test audit logging of sync operations."""
        # Test that sync operations are properly logged
        pass


class TestRedisPubSub:
    """Test Redis pub/sub for real-time notifications."""

    @pytest.fixture
    def redis_pubsub_manager(self):
        """Create Redis pub/sub manager."""
        from app.api.sync.services.pubsub_manager import PubSubManager
        return PubSubManager()

    @pytest.mark.asyncio
    async def test_subscribe_to_user_sync(self, redis_pubsub_manager):
        """Test subscribing to user sync notifications."""
        # Arrange
        user_id = "user-123"
        
        # Act
        await redis_pubsub_manager.subscribe_user_sync(user_id)
        
        # Assert
        # Should be subscribed to user's sync channel

    @pytest.mark.asyncio
    async def test_publish_sync_notification(self, redis_pubsub_manager):
        """Test publishing sync notifications."""
        # Arrange
        user_id = "user-123"
        sync_data = {"sync_type": "command_history", "data": {"command": "ls"}}
        
        # Act
        await redis_pubsub_manager.publish_sync_update(user_id, sync_data)
        
        # Assert
        # Should publish to user's sync channel

    @pytest.mark.asyncio
    async def test_multi_device_notifications(self, redis_pubsub_manager):
        """Test notifications to multiple devices."""
        # Test that sync updates are sent to all user's devices
        pass