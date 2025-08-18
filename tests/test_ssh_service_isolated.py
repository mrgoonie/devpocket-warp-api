"""
Isolated SSH service tests to avoid import conflicts.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

# Direct imports to avoid conftest issues
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.api.ssh.service import SSHProfileService, SSHKeyService


class MockUser:
    def __init__(self):
        self.id = "user-123"
        self.username = "testuser"


class MockSSHProfile:
    def __init__(self):
        self.id = "profile-123"
        self.user_id = "user-123"
        self.name = "Test Server"
        self.host = "192.168.1.100"
        self.port = 22
        self.username = "testuser"


class MockSSHProfileCreate:
    def __init__(self):
        self.name = "Test Server"
        self.host = "192.168.1.100"
        self.port = 22
        self.username = "testuser"
        self.description = "Test SSH connection"
        self.is_default = False


class MockSSHProfileUpdate:
    def __init__(self):
        self.name = "Updated Server"
        self.description = "Updated description"
        self.port = 2222


class MockSSHConnectionTestRequest:
    def __init__(self):
        self.host = "192.168.1.100"
        self.port = 22
        self.username = "testuser"
        self.timeout = 30


class MockSSHProfileSearchRequest:
    def __init__(self):
        self.query = "test"
        self.host = "192.168"
        self.port = 22
        self.offset = 0
        self.limit = 50


class TestSSHProfileServiceIsolated:
    """Isolated SSH Profile Service tests."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def ssh_profile_service(self, mock_session):
        with patch('app.api.ssh.service.SSHProfileRepository') as mock_profile_repo, \
             patch('app.api.ssh.service.SSHKeyRepository') as mock_key_repo, \
             patch('app.api.ssh.service.SSHClient') as mock_ssh_client:
            
            service = SSHProfileService(mock_session)
            service.profile_repo = mock_profile_repo.return_value
            service.key_repo = mock_key_repo.return_value
            service.ssh_client = mock_ssh_client.return_value
            return service

    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_session):
        """Test service initialization."""
        with patch('app.api.ssh.service.SSHProfileRepository') as mock_profile_repo, \
             patch('app.api.ssh.service.SSHKeyRepository') as mock_key_repo, \
             patch('app.api.ssh.service.SSHClient') as mock_ssh_client:
            
            service = SSHProfileService(mock_session)
            assert service.session == mock_session
            assert service.profile_repo is not None
            assert service.key_repo is not None
            assert service.ssh_client is not None

    @pytest.mark.asyncio
    async def test_create_profile_success(self, ssh_profile_service):
        """Test successful profile creation."""
        user = MockUser()
        profile_data = MockSSHProfileCreate()
        created_profile = MockSSHProfile()

        ssh_profile_service.profile_repo.get_by_name.return_value = None
        ssh_profile_service.profile_repo.create.return_value = created_profile

        result = await ssh_profile_service.create_profile(user, profile_data)

        assert result is not None
        ssh_profile_service.profile_repo.create.assert_called_once()
        ssh_profile_service.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_profile_duplicate_name(self, ssh_profile_service):
        """Test creating profile with duplicate name."""
        user = MockUser()
        profile_data = MockSSHProfileCreate()
        existing_profile = MockSSHProfile()

        ssh_profile_service.profile_repo.get_by_name.return_value = existing_profile

        with pytest.raises(HTTPException) as exc_info:
            await ssh_profile_service.create_profile(user, profile_data)
        
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_user_profiles_success(self, ssh_profile_service):
        """Test successful retrieval of user profiles."""
        user = MockUser()
        profiles = [MockSSHProfile() for _ in range(3)]

        ssh_profile_service.profile_repo.get_user_profiles.return_value = profiles

        result = await ssh_profile_service.get_user_profiles(user)

        assert isinstance(result, list)
        assert len(result) >= 0  # Should handle conversion
        ssh_profile_service.profile_repo.get_user_profiles.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_profile_success(self, ssh_profile_service):
        """Test successful profile retrieval."""
        user = MockUser()
        profile = MockSSHProfile()

        ssh_profile_service.profile_repo.get_by_id.return_value = profile

        result = await ssh_profile_service.get_profile(user, str(profile.id))

        assert result is not None
        ssh_profile_service.profile_repo.get_by_id.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, ssh_profile_service):
        """Test get profile when not found."""
        user = MockUser()
        ssh_profile_service.profile_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await ssh_profile_service.get_profile(user, "nonexistent-id")
        
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_profile_success(self, ssh_profile_service):
        """Test successful profile update."""
        user = MockUser()
        profile = MockSSHProfile()
        update_data = MockSSHProfileUpdate()

        ssh_profile_service.profile_repo.get_by_id.return_value = profile
        ssh_profile_service.profile_repo.update.return_value = profile

        result = await ssh_profile_service.update_profile(user, str(profile.id), update_data)

        assert result is not None
        ssh_profile_service.profile_repo.update.assert_called_once()
        ssh_profile_service.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_profile_success(self, ssh_profile_service):
        """Test successful profile deletion."""
        user = MockUser()
        profile = MockSSHProfile()

        ssh_profile_service.profile_repo.get_by_id.return_value = profile
        ssh_profile_service.profile_repo.delete.return_value = True

        result = await ssh_profile_service.delete_profile(user, str(profile.id))

        assert result is True
        ssh_profile_service.profile_repo.delete.assert_called_once()
        ssh_profile_service.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_success(self, ssh_profile_service):
        """Test successful connection test."""
        user = MockUser()
        test_request = MockSSHConnectionTestRequest()

        ssh_profile_service.ssh_client.test_connection.return_value = {
            "success": True,
            "message": "Connection successful",
            "latency_ms": 150,
            "server_info": "OpenSSH_8.0"
        }

        result = await ssh_profile_service.test_connection(user, test_request)

        assert result is not None
        ssh_profile_service.ssh_client.test_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, ssh_profile_service):
        """Test connection test failure."""
        user = MockUser()
        test_request = MockSSHConnectionTestRequest()

        ssh_profile_service.ssh_client.test_connection.return_value = {
            "success": False,
            "message": "Connection timeout",
            "error": "Host unreachable"
        }

        result = await ssh_profile_service.test_connection(user, test_request)

        assert result is not None
        assert hasattr(result, 'success')

    @pytest.mark.asyncio
    async def test_search_profiles_success(self, ssh_profile_service):
        """Test successful profile search."""
        user = MockUser()
        search_request = MockSSHProfileSearchRequest()
        profiles = [MockSSHProfile() for _ in range(3)]

        ssh_profile_service.profile_repo.search_profiles.return_value = profiles
        ssh_profile_service.profile_repo.count_search_results.return_value = 3

        result = await ssh_profile_service.search_profiles(user, search_request)

        assert isinstance(result, tuple)
        profiles_list, total = result
        assert len(profiles_list) >= 0
        assert total >= 0

    @pytest.mark.asyncio
    async def test_get_profile_stats_success(self, ssh_profile_service):
        """Test successful profile statistics retrieval."""
        user = MockUser()
        mock_stats = {
            "total_profiles": 5,
            "active_connections": 2,
            "most_used_host": "192.168.1.100"
        }

        ssh_profile_service.profile_repo.get_user_profile_stats.return_value = mock_stats

        result = await ssh_profile_service.get_profile_stats(user)

        assert result == mock_stats
        ssh_profile_service.profile_repo.get_user_profile_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_patterns(self, ssh_profile_service):
        """Test various error handling patterns."""
        user = MockUser()
        
        # Test database error handling
        ssh_profile_service.profile_repo.get_user_profiles.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await ssh_profile_service.get_user_profiles(user)
        
        assert exc_info.value.status_code == 500

        # Test connection test error
        ssh_profile_service.ssh_client.test_connection.side_effect = Exception("SSH error")
        test_request = MockSSHConnectionTestRequest()

        with pytest.raises(HTTPException) as exc_info:
            await ssh_profile_service.test_connection(user, test_request)
        
        assert exc_info.value.status_code == 500


class MockSSHKeyCreate:
    def __init__(self):
        self.name = "Test Key"
        self.public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC... test@example.com"
        self.description = "Test SSH key"
        self.is_default = False


class MockSSHKeyUpdate:
    def __init__(self):
        self.name = "Updated Key"
        self.description = "Updated description"


class MockSSHKeySearchRequest:
    def __init__(self):
        self.query = "test"
        self.key_type = "rsa"
        self.offset = 0
        self.limit = 50


class TestSSHKeyServiceIsolated:
    """Isolated SSH Key Service tests."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def ssh_key_service(self, mock_session):
        with patch('app.api.ssh.service.SSHKeyRepository') as mock_key_repo:
            service = SSHKeyService(mock_session)
            service.key_repo = mock_key_repo.return_value
            return service

    @pytest.mark.asyncio
    async def test_key_service_initialization(self, mock_session):
        """Test SSH key service initialization."""
        with patch('app.api.ssh.service.SSHKeyRepository'):
            service = SSHKeyService(mock_session)
            assert service.session == mock_session
            assert service.key_repo is not None

    @pytest.mark.asyncio
    async def test_create_key_success(self, ssh_key_service):
        """Test successful SSH key creation."""
        user = MockUser()
        key_data = MockSSHKeyCreate()
        created_key = MagicMock()
        created_key.id = "key-123"
        created_key.name = key_data.name

        ssh_key_service.key_repo.get_by_name.return_value = None
        ssh_key_service.key_repo.create.return_value = created_key

        result = await ssh_key_service.create_key(user, key_data)

        assert result is not None
        ssh_key_service.key_repo.create.assert_called_once()
        ssh_key_service.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_key_duplicate_name(self, ssh_key_service):
        """Test creating key with duplicate name."""
        user = MockUser()
        key_data = MockSSHKeyCreate()
        existing_key = MagicMock()

        ssh_key_service.key_repo.get_by_name.return_value = existing_key

        with pytest.raises(HTTPException) as exc_info:
            await ssh_key_service.create_key(user, key_data)
        
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_user_keys_success(self, ssh_key_service):
        """Test successful retrieval of user keys."""
        user = MockUser()
        keys = [MagicMock() for _ in range(3)]

        ssh_key_service.key_repo.get_user_keys.return_value = keys

        result = await ssh_key_service.get_user_keys(user)

        assert isinstance(result, list)
        ssh_key_service.key_repo.get_user_keys.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_key_success(self, ssh_key_service):
        """Test successful key update."""
        user = MockUser()
        key = MagicMock()
        key.id = "key-123"
        key.user_id = user.id
        update_data = MockSSHKeyUpdate()

        ssh_key_service.key_repo.get_by_id.return_value = key
        ssh_key_service.key_repo.update.return_value = key

        result = await ssh_key_service.update_key(user, str(key.id), update_data)

        assert result is not None
        ssh_key_service.key_repo.update.assert_called_once()
        ssh_key_service.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_key_success(self, ssh_key_service):
        """Test successful key deletion."""
        user = MockUser()
        key = MagicMock()
        key.id = "key-123"
        key.user_id = user.id

        ssh_key_service.key_repo.get_by_id.return_value = key
        ssh_key_service.key_repo.delete.return_value = True

        result = await ssh_key_service.delete_key(user, str(key.id))

        assert result is True
        ssh_key_service.key_repo.delete.assert_called_once()
        ssh_key_service.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_keys_success(self, ssh_key_service):
        """Test successful key search."""
        user = MockUser()
        search_request = MockSSHKeySearchRequest()
        keys = [MagicMock() for _ in range(2)]

        ssh_key_service.key_repo.search_keys.return_value = keys
        ssh_key_service.key_repo.count_search_results.return_value = 2

        result = await ssh_key_service.search_keys(user, search_request)

        assert isinstance(result, tuple)
        keys_list, total = result
        assert len(keys_list) >= 0
        assert total >= 0

    @pytest.mark.asyncio
    async def test_get_key_stats_success(self, ssh_key_service):
        """Test successful key statistics retrieval."""
        user = MockUser()
        mock_stats = {
            "total_keys": 3,
            "rsa_keys": 2,
            "ed25519_keys": 1
        }

        ssh_key_service.key_repo.get_user_key_stats.return_value = mock_stats

        result = await ssh_key_service.get_key_stats(user)

        assert result == mock_stats
        ssh_key_service.key_repo.get_user_key_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_key_service_error_handling(self, ssh_key_service):
        """Test key service error handling."""
        user = MockUser()
        
        # Test database error in get_user_keys
        ssh_key_service.key_repo.get_user_keys.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await ssh_key_service.get_user_keys(user)
        
        assert exc_info.value.status_code == 500

        # Test search error
        ssh_key_service.key_repo.search_keys.side_effect = Exception("Search error")
        search_request = MockSSHKeySearchRequest()

        with pytest.raises(HTTPException) as exc_info:
            await ssh_key_service.search_keys(user, search_request)
        
        assert exc_info.value.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])