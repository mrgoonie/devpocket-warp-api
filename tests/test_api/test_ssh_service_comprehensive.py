"""
Comprehensive tests for SSH service functionality.

This module provides extensive coverage for SSH service operations,
targeting high-impact methods to achieve significant coverage gains.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status

from app.api.ssh.service import SSHProfileService, SSHKeyService
from app.api.ssh.schemas import (
    SSHProfileCreate,
    SSHProfileUpdate,
    SSHProfileResponse,
    SSHConnectionTestRequest,
    SSHConnectionTestResponse,
    SSHProfileSearchRequest,
    SSHKeyCreate,
    SSHKeyUpdate,
    SSHKeyResponse,
    SSHKeySearchRequest,
)
from app.models.ssh_profile import SSHProfile
from app.models.user import User
from tests.factories import UserFactory, SSHProfileFactory


@pytest.mark.database
@pytest.mark.api
class TestSSHProfileServiceComprehensive:
    """Comprehensive test suite for SSHProfileService."""

    @pytest_asyncio.fixture
    async def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest_asyncio.fixture
    async def mock_profile_repo(self):
        """Create a mock SSH profile repository."""
        repo = AsyncMock()
        return repo

    @pytest_asyncio.fixture
    async def mock_key_repo(self):
        """Create a mock SSH key repository."""
        repo = AsyncMock()
        return repo

    @pytest_asyncio.fixture
    async def mock_ssh_client(self):
        """Create a mock SSH client."""
        client = AsyncMock()
        return client

    @pytest_asyncio.fixture
    async def ssh_profile_service(self, mock_db_session, mock_profile_repo, mock_key_repo, mock_ssh_client):
        """Create SSH profile service instance with mocked dependencies."""
        with patch('app.api.ssh.service.SSHProfileRepository', return_value=mock_profile_repo), \
             patch('app.api.ssh.service.SSHKeyRepository', return_value=mock_key_repo), \
             patch('app.api.ssh.service.SSHClient', return_value=mock_ssh_client):
            service = SSHProfileService(mock_db_session)
            service.profile_repo = mock_profile_repo
            service.key_repo = mock_key_repo
            service.ssh_client = mock_ssh_client
            return service

    @pytest_asyncio.fixture
    async def sample_user(self):
        """Create a sample user."""
        return UserFactory()

    @pytest_asyncio.fixture
    async def sample_profile(self, sample_user):
        """Create a sample SSH profile."""
        profile = SSHProfileFactory()
        profile.user_id = sample_user.id
        profile.name = "Test Server"
        profile.host = "192.168.1.100"
        profile.port = 22
        profile.username = "testuser"
        return profile

    # Service Initialization Tests
    async def test_ssh_profile_service_initialization(self, mock_db_session):
        """Test SSHProfileService initialization with proper dependencies."""
        with patch('app.api.ssh.service.SSHProfileRepository') as mock_profile_repo, \
             patch('app.api.ssh.service.SSHKeyRepository') as mock_key_repo, \
             patch('app.api.ssh.service.SSHClient') as mock_ssh_client:
            service = SSHProfileService(mock_db_session)
            
            assert service.session == mock_db_session
            assert service.profile_repo is not None
            assert service.key_repo is not None
            assert service.ssh_client is not None

    # Create Profile Tests
    async def test_create_profile_success(self, ssh_profile_service, sample_user):
        """Test successful SSH profile creation."""
        profile_data = SSHProfileCreate(
            name="Test Server",
            host="192.168.1.100",
            port=22,
            username="testuser",
            description="Test SSH connection",
            is_default=False
        )

        created_profile = SSHProfileFactory()
        created_profile.user_id = sample_user.id
        created_profile.name = profile_data.name
        created_profile.host = profile_data.host

        ssh_profile_service.profile_repo.create.return_value = created_profile

        result = await ssh_profile_service.create_profile(sample_user, profile_data)

        assert isinstance(result, SSHProfileResponse)
        assert result.name == profile_data.name
        assert result.host == profile_data.host
        ssh_profile_service.profile_repo.create.assert_called_once()
        ssh_profile_service.session.commit.assert_called_once()

    async def test_create_profile_duplicate_name(self, ssh_profile_service, sample_user):
        """Test creating profile with duplicate name for user."""
        profile_data = SSHProfileCreate(
            name="Existing Server",
            host="192.168.1.100",
            port=22,
            username="testuser"
        )

        # Mock existing profile with same name
        existing_profile = SSHProfileFactory()
        existing_profile.name = profile_data.name
        existing_profile.user_id = sample_user.id
        ssh_profile_service.profile_repo.get_by_name.return_value = existing_profile

        with pytest.raises(HTTPException) as exc_info:
            await ssh_profile_service.create_profile(sample_user, profile_data)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in exc_info.value.detail

    async def test_create_profile_exception_handling(self, ssh_profile_service, sample_user):
        """Test create profile error handling."""
        profile_data = SSHProfileCreate(
            name="Test Server",
            host="192.168.1.100",
            port=22,
            username="testuser"
        )

        ssh_profile_service.profile_repo.get_by_name.return_value = None
        ssh_profile_service.profile_repo.create.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await ssh_profile_service.create_profile(sample_user, profile_data)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        ssh_profile_service.session.rollback.assert_called_once()

    # Get User Profiles Tests
    async def test_get_user_profiles_success(self, ssh_profile_service, sample_user):
        """Test successful retrieval of user profiles."""
        profiles = [SSHProfileFactory() for _ in range(3)]
        for profile in profiles:
            profile.user_id = sample_user.id

        ssh_profile_service.profile_repo.get_user_profiles.return_value = profiles

        result = await ssh_profile_service.get_user_profiles(sample_user)

        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(profile, SSHProfileResponse) for profile in result)

    async def test_get_user_profiles_empty(self, ssh_profile_service, sample_user):
        """Test get user profiles with no profiles."""
        ssh_profile_service.profile_repo.get_user_profiles.return_value = []

        result = await ssh_profile_service.get_user_profiles(sample_user)

        assert isinstance(result, list)
        assert len(result) == 0

    async def test_get_user_profiles_exception_handling(self, ssh_profile_service, sample_user):
        """Test get user profiles error handling."""
        ssh_profile_service.profile_repo.get_user_profiles.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await ssh_profile_service.get_user_profiles(sample_user)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # Get Profile Tests
    async def test_get_profile_success(self, ssh_profile_service, sample_user, sample_profile):
        """Test successful profile retrieval."""
        ssh_profile_service.profile_repo.get_by_id.return_value = sample_profile

        result = await ssh_profile_service.get_profile(sample_user, str(sample_profile.id))

        assert isinstance(result, SSHProfileResponse)
        assert result.id == str(sample_profile.id)

    async def test_get_profile_not_found(self, ssh_profile_service, sample_user):
        """Test get profile when profile not found."""
        ssh_profile_service.profile_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await ssh_profile_service.get_profile(sample_user, "nonexistent-id")
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_profile_wrong_user(self, ssh_profile_service, sample_profile):
        """Test get profile access by wrong user."""
        wrong_user = UserFactory()
        ssh_profile_service.profile_repo.get_by_id.return_value = sample_profile

        with pytest.raises(HTTPException) as exc_info:
            await ssh_profile_service.get_profile(wrong_user, str(sample_profile.id))
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    # Update Profile Tests
    async def test_update_profile_success(self, ssh_profile_service, sample_user, sample_profile):
        """Test successful profile update."""
        update_data = SSHProfileUpdate(
            name="Updated Server",
            description="Updated description",
            port=2222
        )

        ssh_profile_service.profile_repo.get_by_id.return_value = sample_profile
        ssh_profile_service.profile_repo.update.return_value = sample_profile

        result = await ssh_profile_service.update_profile(sample_user, str(sample_profile.id), update_data)

        assert isinstance(result, SSHProfileResponse)
        ssh_profile_service.profile_repo.update.assert_called_once()
        ssh_profile_service.session.commit.assert_called_once()

    async def test_update_profile_not_found(self, ssh_profile_service, sample_user):
        """Test update profile when profile not found."""
        update_data = SSHProfileUpdate(name="Updated Server")
        ssh_profile_service.profile_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await ssh_profile_service.update_profile(sample_user, "nonexistent-id", update_data)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_profile_exception_handling(self, ssh_profile_service, sample_user, sample_profile):
        """Test update profile error handling."""
        update_data = SSHProfileUpdate(name="Updated Server")
        ssh_profile_service.profile_repo.get_by_id.return_value = sample_profile
        ssh_profile_service.profile_repo.update.side_effect = Exception("Update error")

        with pytest.raises(HTTPException) as exc_info:
            await ssh_profile_service.update_profile(sample_user, str(sample_profile.id), update_data)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        ssh_profile_service.session.rollback.assert_called_once()

    # Delete Profile Tests
    async def test_delete_profile_success(self, ssh_profile_service, sample_user, sample_profile):
        """Test successful profile deletion."""
        ssh_profile_service.profile_repo.get_by_id.return_value = sample_profile
        ssh_profile_service.profile_repo.delete.return_value = True

        result = await ssh_profile_service.delete_profile(sample_user, str(sample_profile.id))

        assert result is True
        ssh_profile_service.profile_repo.delete.assert_called_once_with(str(sample_profile.id))
        ssh_profile_service.session.commit.assert_called_once()

    async def test_delete_profile_not_found(self, ssh_profile_service, sample_user):
        """Test delete profile when profile not found."""
        ssh_profile_service.profile_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await ssh_profile_service.delete_profile(sample_user, "nonexistent-id")
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_profile_exception_handling(self, ssh_profile_service, sample_user, sample_profile):
        """Test delete profile error handling."""
        ssh_profile_service.profile_repo.get_by_id.return_value = sample_profile
        ssh_profile_service.profile_repo.delete.side_effect = Exception("Delete error")

        with pytest.raises(HTTPException) as exc_info:
            await ssh_profile_service.delete_profile(sample_user, str(sample_profile.id))
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        ssh_profile_service.session.rollback.assert_called_once()

    # Test Connection Tests
    async def test_test_connection_success(self, ssh_profile_service, sample_user, sample_profile):
        """Test successful connection test."""
        test_request = SSHConnectionTestRequest(
            host=sample_profile.host,
            port=sample_profile.port,
            username=sample_profile.username,
            timeout=30
        )

        # Mock successful connection
        ssh_profile_service.ssh_client.test_connection.return_value = {
            "success": True,
            "message": "Connection successful",
            "latency_ms": 150,
            "server_info": "OpenSSH_8.0"
        }

        result = await ssh_profile_service.test_connection(sample_user, test_request)

        assert isinstance(result, SSHConnectionTestResponse)
        assert result.success is True
        assert result.latency_ms == 150

    async def test_test_connection_failure(self, ssh_profile_service, sample_user):
        """Test connection test failure."""
        test_request = SSHConnectionTestRequest(
            host="invalid.host.com",
            port=22,
            username="testuser",
            timeout=30
        )

        # Mock connection failure
        ssh_profile_service.ssh_client.test_connection.return_value = {
            "success": False,
            "message": "Connection timeout",
            "error": "Host unreachable"
        }

        result = await ssh_profile_service.test_connection(sample_user, test_request)

        assert isinstance(result, SSHConnectionTestResponse)
        assert result.success is False
        assert "timeout" in result.message

    async def test_test_connection_exception_handling(self, ssh_profile_service, sample_user):
        """Test connection test error handling."""
        test_request = SSHConnectionTestRequest(
            host="test.host.com",
            port=22,
            username="testuser"
        )

        ssh_profile_service.ssh_client.test_connection.side_effect = Exception("SSH error")

        with pytest.raises(HTTPException) as exc_info:
            await ssh_profile_service.test_connection(sample_user, test_request)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # Search Profiles Tests
    async def test_search_profiles_success(self, ssh_profile_service, sample_user):
        """Test successful profile search."""
        search_request = SSHProfileSearchRequest(
            query="test",
            host="192.168",
            port=22,
            offset=0,
            limit=50
        )

        profiles = [SSHProfileFactory() for _ in range(3)]
        ssh_profile_service.profile_repo.search_profiles.return_value = profiles
        ssh_profile_service.profile_repo.count_search_results.return_value = 3

        result = await ssh_profile_service.search_profiles(sample_user, search_request)

        assert isinstance(result, tuple)
        profiles_list, total = result
        assert len(profiles_list) == 3
        assert total == 3

    async def test_search_profiles_empty_result(self, ssh_profile_service, sample_user):
        """Test search profiles with no results."""
        search_request = SSHProfileSearchRequest(query="nonexistent")
        ssh_profile_service.profile_repo.search_profiles.return_value = []
        ssh_profile_service.profile_repo.count_search_results.return_value = 0

        result = await ssh_profile_service.search_profiles(sample_user, search_request)

        profiles_list, total = result
        assert len(profiles_list) == 0
        assert total == 0

    async def test_search_profiles_exception_handling(self, ssh_profile_service, sample_user):
        """Test search profiles error handling."""
        search_request = SSHProfileSearchRequest(query="test")
        ssh_profile_service.profile_repo.search_profiles.side_effect = Exception("Search error")

        with pytest.raises(HTTPException) as exc_info:
            await ssh_profile_service.search_profiles(sample_user, search_request)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # Profile Statistics Tests
    async def test_get_profile_stats_success(self, ssh_profile_service, sample_user):
        """Test successful profile statistics retrieval."""
        mock_stats = {
            "total_profiles": 5,
            "active_connections": 2,
            "most_used_host": "192.168.1.100",
            "average_connection_time": 1500,
            "success_rate": 95.5
        }
        ssh_profile_service.profile_repo.get_user_profile_stats.return_value = mock_stats

        result = await ssh_profile_service.get_profile_stats(sample_user)

        assert result == mock_stats
        ssh_profile_service.profile_repo.get_user_profile_stats.assert_called_once_with(sample_user.id)

    async def test_get_profile_stats_exception_handling(self, ssh_profile_service, sample_user):
        """Test profile statistics error handling."""
        ssh_profile_service.profile_repo.get_user_profile_stats.side_effect = Exception("Stats error")

        with pytest.raises(HTTPException) as exc_info:
            await ssh_profile_service.get_profile_stats(sample_user)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.database
@pytest.mark.api
class TestSSHKeyServiceComprehensive:
    """Comprehensive test suite for SSHKeyService."""

    @pytest_asyncio.fixture
    async def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest_asyncio.fixture
    async def mock_key_repo(self):
        """Create a mock SSH key repository."""
        repo = AsyncMock()
        return repo

    @pytest_asyncio.fixture
    async def ssh_key_service(self, mock_db_session, mock_key_repo):
        """Create SSH key service instance with mocked dependencies."""
        with patch('app.api.ssh.service.SSHKeyRepository', return_value=mock_key_repo):
            service = SSHKeyService(mock_db_session)
            service.key_repo = mock_key_repo
            return service

    @pytest_asyncio.fixture
    async def sample_user(self):
        """Create a sample user."""
        return UserFactory()

    @pytest_asyncio.fixture
    async def sample_ssh_key(self, sample_user):
        """Create a sample SSH key."""
        from tests.factories import SSHKeyFactory
        key = SSHKeyFactory()
        key.user_id = sample_user.id
        key.name = "Test Key"
        key.public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC... test@example.com"
        return key

    # Service Initialization Tests
    async def test_ssh_key_service_initialization(self, mock_db_session):
        """Test SSHKeyService initialization."""
        with patch('app.api.ssh.service.SSHKeyRepository') as mock_key_repo:
            service = SSHKeyService(mock_db_session)
            
            assert service.session == mock_db_session
            assert service.key_repo is not None

    # Create Key Tests
    async def test_create_key_success(self, ssh_key_service, sample_user):
        """Test successful SSH key creation."""
        key_data = SSHKeyCreate(
            name="Test Key",
            public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC... test@example.com",
            description="Test SSH key",
            is_default=False
        )

        created_key = MagicMock()
        created_key.id = "key-123"
        created_key.name = key_data.name
        created_key.public_key = key_data.public_key
        created_key.user_id = sample_user.id
        
        ssh_key_service.key_repo.create.return_value = created_key

        result = await ssh_key_service.create_key(sample_user, key_data)

        assert isinstance(result, SSHKeyResponse)
        assert result.name == key_data.name
        ssh_key_service.key_repo.create.assert_called_once()
        ssh_key_service.session.commit.assert_called_once()

    async def test_create_key_duplicate_name(self, ssh_key_service, sample_user):
        """Test creating key with duplicate name for user."""
        key_data = SSHKeyCreate(
            name="Existing Key",
            public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC... test@example.com"
        )

        # Mock existing key with same name
        existing_key = MagicMock()
        existing_key.name = key_data.name
        existing_key.user_id = sample_user.id
        ssh_key_service.key_repo.get_by_name.return_value = existing_key

        with pytest.raises(HTTPException) as exc_info:
            await ssh_key_service.create_key(sample_user, key_data)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    async def test_create_key_exception_handling(self, ssh_key_service, sample_user):
        """Test create key error handling."""
        key_data = SSHKeyCreate(
            name="Test Key",
            public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC... test@example.com"
        )

        ssh_key_service.key_repo.get_by_name.return_value = None
        ssh_key_service.key_repo.create.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await ssh_key_service.create_key(sample_user, key_data)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        ssh_key_service.session.rollback.assert_called_once()

    # Get User Keys Tests
    async def test_get_user_keys_success(self, ssh_key_service, sample_user):
        """Test successful retrieval of user keys."""
        keys = [MagicMock() for _ in range(3)]
        for i, key in enumerate(keys):
            key.id = f"key-{i}"
            key.name = f"Key {i}"
            key.user_id = sample_user.id

        ssh_key_service.key_repo.get_user_keys.return_value = keys

        result = await ssh_key_service.get_user_keys(sample_user)

        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(key, SSHKeyResponse) for key in result)

    async def test_get_user_keys_empty(self, ssh_key_service, sample_user):
        """Test get user keys with no keys."""
        ssh_key_service.key_repo.get_user_keys.return_value = []

        result = await ssh_key_service.get_user_keys(sample_user)

        assert isinstance(result, list)
        assert len(result) == 0

    async def test_get_user_keys_exception_handling(self, ssh_key_service, sample_user):
        """Test get user keys error handling."""
        ssh_key_service.key_repo.get_user_keys.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await ssh_key_service.get_user_keys(sample_user)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # Update and Delete Key Tests
    async def test_update_key_success(self, ssh_key_service, sample_user, sample_ssh_key):
        """Test successful key update."""
        update_data = SSHKeyUpdate(
            name="Updated Key",
            description="Updated description"
        )

        ssh_key_service.key_repo.get_by_id.return_value = sample_ssh_key
        ssh_key_service.key_repo.update.return_value = sample_ssh_key

        result = await ssh_key_service.update_key(sample_user, str(sample_ssh_key.id), update_data)

        assert isinstance(result, SSHKeyResponse)
        ssh_key_service.key_repo.update.assert_called_once()
        ssh_key_service.session.commit.assert_called_once()

    async def test_delete_key_success(self, ssh_key_service, sample_user, sample_ssh_key):
        """Test successful key deletion."""
        ssh_key_service.key_repo.get_by_id.return_value = sample_ssh_key
        ssh_key_service.key_repo.delete.return_value = True

        result = await ssh_key_service.delete_key(sample_user, str(sample_ssh_key.id))

        assert result is True
        ssh_key_service.key_repo.delete.assert_called_once()
        ssh_key_service.session.commit.assert_called_once()

    # Search Keys Tests
    async def test_search_keys_success(self, ssh_key_service, sample_user):
        """Test successful key search."""
        search_request = SSHKeySearchRequest(
            query="test",
            key_type="rsa",
            offset=0,
            limit=50
        )

        keys = [MagicMock() for _ in range(2)]
        for i, key in enumerate(keys):
            key.id = f"key-{i}"
            key.name = f"Key {i}"

        ssh_key_service.key_repo.search_keys.return_value = keys
        ssh_key_service.key_repo.count_search_results.return_value = 2

        result = await ssh_key_service.search_keys(sample_user, search_request)

        assert isinstance(result, tuple)
        keys_list, total = result
        assert len(keys_list) == 2
        assert total == 2

    async def test_search_keys_exception_handling(self, ssh_key_service, sample_user):
        """Test search keys error handling."""
        search_request = SSHKeySearchRequest(query="test")
        ssh_key_service.key_repo.search_keys.side_effect = Exception("Search error")

        with pytest.raises(HTTPException) as exc_info:
            await ssh_key_service.search_keys(sample_user, search_request)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # Key Statistics Tests
    async def test_get_key_stats_success(self, ssh_key_service, sample_user):
        """Test successful key statistics retrieval."""
        mock_stats = {
            "total_keys": 3,
            "rsa_keys": 2,
            "ed25519_keys": 1,
            "default_key": "key-1"
        }
        ssh_key_service.key_repo.get_user_key_stats.return_value = mock_stats

        result = await ssh_key_service.get_key_stats(sample_user)

        assert result == mock_stats
        ssh_key_service.key_repo.get_user_key_stats.assert_called_once_with(sample_user.id)

    async def test_get_key_stats_exception_handling(self, ssh_key_service, sample_user):
        """Test key statistics error handling."""
        ssh_key_service.key_repo.get_user_key_stats.side_effect = Exception("Stats error")

        with pytest.raises(HTTPException) as exc_info:
            await ssh_key_service.get_key_stats(sample_user)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # Edge Cases and Integration Tests
    async def test_large_key_handling(self, ssh_key_service, sample_user):
        """Test handling of large SSH keys."""
        large_key_data = SSHKeyCreate(
            name="Large Key",
            public_key="ssh-rsa " + "A" * 4000 + " test@example.com",  # Large key
            description="Very large SSH key for testing"
        )

        created_key = MagicMock()
        created_key.id = "large-key-123"
        created_key.name = large_key_data.name
        created_key.public_key = large_key_data.public_key
        
        ssh_key_service.key_repo.get_by_name.return_value = None
        ssh_key_service.key_repo.create.return_value = created_key

        result = await ssh_key_service.create_key(sample_user, large_key_data)

        assert isinstance(result, SSHKeyResponse)
        assert result.name == large_key_data.name

    async def test_concurrent_key_operations(self, ssh_key_service, sample_user):
        """Test concurrent key operations."""
        # Simulate multiple operations that could happen concurrently
        ssh_key_service.key_repo.get_user_keys.return_value = []

        result1 = await ssh_key_service.get_user_keys(sample_user)
        result2 = await ssh_key_service.get_user_keys(sample_user)

        assert isinstance(result1, list)
        assert isinstance(result2, list)
        assert len(result1) == len(result2) == 0