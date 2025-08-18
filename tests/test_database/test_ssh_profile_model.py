"""
Basic tests for SSH Profile model functionality.
"""

import pytest

from app.models.ssh_profile import SSHProfile
from app.repositories.user import UserRepository


@pytest.mark.database
class TestSSHProfileModel:
    """Test SSH profile model basic functionality."""

    @pytest.fixture
    def user_repository(self, test_session):
        """Create user repository instance."""
        return UserRepository(test_session)

    @pytest.fixture
    async def sample_user(self, user_repository):
        """Create a sample user for testing."""
        user_data = {
            "username": "testuser",
            "email": "test@example.com", 
            "full_name": "Test User",
            "hashed_password": "hashed_password_123"
        }
        return await user_repository.create(user_data)

    @pytest.mark.asyncio
    async def test_ssh_profile_creation(self, test_session, sample_user):
        """Test SSH profile creation with basic attributes."""
        user = sample_user
        profile = SSHProfile(
            user_id=user.id,
            name="Test Server",
            host="example.com",
            port=22,
            username="testuser"
        )
        
        test_session.add(profile)
        await test_session.commit()
        await test_session.refresh(profile)
        
        assert profile.id is not None
        assert profile.name == "Test Server"
        assert profile.host == "example.com"
        assert profile.port == 22
        assert profile.username == "testuser"
        assert profile.user_id == user.id

    @pytest.mark.asyncio
    async def test_ssh_profile_model_attributes(self, test_session, sample_user):
        """Test that SSH profile model has expected attributes."""
        user = sample_user
        profile = SSHProfile(
            user_id=user.id,
            name="Test Server",
            host="example.com",
            port=22,
            username="testuser"
        )
        
        # Test required attributes exist
        assert hasattr(profile, 'id')
        assert hasattr(profile, 'user_id')
        assert hasattr(profile, 'name')
        assert hasattr(profile, 'host') 
        assert hasattr(profile, 'port')
        assert hasattr(profile, 'username')
        assert hasattr(profile, 'created_at')
        assert hasattr(profile, 'updated_at')
        
        # Test connection attributes exist
        assert hasattr(profile, 'description')
        assert hasattr(profile, 'auth_method')
        assert hasattr(profile, 'compression')
        assert hasattr(profile, 'is_active')
        assert hasattr(profile, 'connection_timeout')

    @pytest.mark.asyncio
    async def test_ssh_profile_defaults(self, test_session, sample_user):
        """Test SSH profile default values."""
        user = sample_user
        profile = SSHProfile(
            user_id=user.id,
            name="Test Server",
            host="example.com",
            username="testuser"
        )
        
        test_session.add(profile)
        await test_session.commit()
        await test_session.refresh(profile)
        
        # Default port should be 22
        assert profile.port == 22
        # Default active status should be True
        assert profile.is_active is True
        # Default auth method should be 'key'
        assert profile.auth_method == "key"
        # Default compression should be True
        assert profile.compression is True

    @pytest.mark.asyncio
    async def test_ssh_profile_string_representation(self, test_session, sample_user):
        """Test SSH profile string representation."""
        user = sample_user
        profile = SSHProfile(
            user_id=user.id,
            name="Test Server",
            host="example.com",
            port=22,
            username="testuser"
        )
        
        # Test that string representation exists and contains key info
        str_repr = str(profile)
        assert "Test Server" in str_repr or "example.com" in str_repr

    @pytest.mark.asyncio
    async def test_ssh_profile_methods(self, test_session, sample_user):
        """Test SSH profile methods."""
        user = sample_user
        profile = SSHProfile(
            user_id=user.id,
            name="Test Server",
            host="example.com",
            port=22,
            username="testuser"
        )
        
        test_session.add(profile)
        await test_session.commit()
        await test_session.refresh(profile)
        
        # Test success_rate property
        assert profile.success_rate == 0.0
        
        # Test record_connection_attempt method
        profile.record_connection_attempt(True)
        assert profile.connection_count == 1
        assert profile.successful_connections == 1
        assert profile.success_rate == 100.0
        
        # Test to_ssh_config method
        config = profile.to_ssh_config()
        assert "Host Test Server" in config
        assert "HostName example.com" in config
        assert "Port 22" in config
        assert "User testuser" in config