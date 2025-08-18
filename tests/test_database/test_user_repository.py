"""
Tests for User repository functionality.

Basic tests to improve coverage for user repository operations.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.repositories.user import UserRepository


@pytest.mark.database
class TestUserRepository:
    """Test user repository operations."""

    @pytest.fixture
    def user_repository(self, test_session):
        """Create user repository instance."""
        return UserRepository(test_session)

    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing."""
        return {
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "hashed_password": "hashed_password_123"
        }

    @pytest.mark.asyncio
    async def test_create_user_success(self, user_repository, sample_user_data):
        """Test successful user creation."""
        user = await user_repository.create(sample_user_data)
        
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.hashed_password == "hashed_password_123"
        assert user.id is not None

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, user_repository, sample_user_data):
        """Test getting user by ID."""
        # Create user first
        created_user = await user_repository.create(sample_user_data)
        
        # Get user by ID
        fetched_user = await user_repository.get_by_id(created_user.id)
        
        assert fetched_user is not None
        assert fetched_user.id == created_user.id
        assert fetched_user.username == "testuser"

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, user_repository):
        """Test getting user by non-existent ID."""
        import uuid
        user = await user_repository.get_by_id(str(uuid.uuid4()))
        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_username(self, user_repository, sample_user_data):
        """Test getting user by username."""
        # Create user first
        await user_repository.create(sample_user_data)
        
        # Get user by username
        fetched_user = await user_repository.get_by_username("testuser")
        
        assert fetched_user is not None
        assert fetched_user.username == "testuser"
        assert fetched_user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_username_not_found(self, user_repository):
        """Test getting user by non-existent username."""
        user = await user_repository.get_by_username("nonexistent")
        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, user_repository, sample_user_data):
        """Test getting user by email."""
        # Create user first
        await user_repository.create(sample_user_data)
        
        # Get user by email
        fetched_user = await user_repository.get_by_email("test@example.com")
        
        assert fetched_user is not None
        assert fetched_user.email == "test@example.com"
        assert fetched_user.username == "testuser"

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, user_repository):
        """Test getting user by non-existent email."""
        user = await user_repository.get_by_email("nonexistent@example.com")
        assert user is None

    @pytest.mark.asyncio
    async def test_update_user(self, user_repository, sample_user_data):
        """Test updating user information."""
        # Create user first
        user = await user_repository.create(sample_user_data)
        
        # Update user
        updated_user = await user_repository.update(user.id, full_name="Updated Test User", email="updated@example.com")
        
        assert updated_user.full_name == "Updated Test User"
        assert updated_user.email == "updated@example.com"
        assert updated_user.username == "testuser"  # Unchanged

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, user_repository):
        """Test updating non-existent user."""
        import uuid
        updated_user = await user_repository.update(str(uuid.uuid4()), full_name="Updated Test User")
        assert updated_user is None

    @pytest.mark.asyncio
    async def test_delete_user(self, user_repository, sample_user_data):
        """Test deleting user."""
        # Create user first
        user = await user_repository.create(sample_user_data)
        user_id = user.id
        
        # Delete user
        result = await user_repository.delete(user_id)
        assert result is True
        
        # Verify user is deleted
        deleted_user = await user_repository.get_by_id(user_id)
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, user_repository):
        """Test deleting non-existent user."""
        import uuid
        result = await user_repository.delete(str(uuid.uuid4()))
        assert result is False

    @pytest.mark.asyncio
    async def test_list_users(self, user_repository):
        """Test listing users with pagination."""
        # Create multiple users
        for i in range(5):
            user_data = {
                "username": f"testuser{i}",
                "email": f"test{i}@example.com",
                "full_name": f"Test User {i}",
                "hashed_password": f"hashed_password_{i}"
            }
            await user_repository.create(user_data)
        
        # List users using get_all method
        users = await user_repository.get_all(limit=3, offset=1, order_by="username", order_desc=False)
        
        assert len(users) == 3
        # Users should be ordered by username
        assert users[0].username == "testuser1"
        assert users[1].username == "testuser2"
        assert users[2].username == "testuser3"

    @pytest.mark.asyncio
    async def test_count_users(self, user_repository, sample_user_data):
        """Test counting total users."""
        initial_count = await user_repository.count()
        
        # Create a user
        await user_repository.create(sample_user_data)
        
        # Count should increase by 1
        new_count = await user_repository.count()
        assert new_count == initial_count + 1

    @pytest.mark.asyncio
    async def test_is_email_taken(self, user_repository, sample_user_data):
        """Test checking if email is taken."""
        # Initially should not be taken
        is_taken = await user_repository.is_email_taken("test@example.com")
        assert is_taken is False
        
        # Create user
        user = await user_repository.create(sample_user_data)
        
        # Now should be taken
        is_taken = await user_repository.is_email_taken("test@example.com")
        assert is_taken is True
        
        # Should not be taken when excluding the same user
        is_taken = await user_repository.is_email_taken("test@example.com", exclude_user_id=user.id)
        assert is_taken is False

    @pytest.mark.asyncio
    async def test_is_username_taken(self, user_repository, sample_user_data):
        """Test checking if username is taken."""
        # Initially should not be taken
        is_taken = await user_repository.is_username_taken("testuser")
        assert is_taken is False
        
        # Create user
        user = await user_repository.create(sample_user_data)
        
        # Now should be taken
        is_taken = await user_repository.is_username_taken("testuser")
        assert is_taken is True
        
        # Should not be taken when excluding the same user
        is_taken = await user_repository.is_username_taken("testuser", exclude_user_id=user.id)
        assert is_taken is False

    @pytest.mark.asyncio
    async def test_user_with_all_relationships(self, user_repository, sample_user_data):
        """Test getting user with all relationships loaded."""
        user = await user_repository.create(sample_user_data)
        
        # Get user with all relationships
        user_with_rels = await user_repository.get_with_all_relationships(user.id)
        
        assert user_with_rels is not None
        assert user_with_rels.id == user.id
        assert user_with_rels.username == "testuser"
        
        # These should be accessible without error (even if empty)
        assert hasattr(user_with_rels, 'ssh_profiles')
        assert hasattr(user_with_rels, 'sessions')