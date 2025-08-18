"""
Enhanced comprehensive tests for User repository functionality to achieve 80% coverage.

This module provides targeted test coverage for all User repository operations,
focusing on the missing statements to reach our coverage goal.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, UTC
from uuid import uuid4

from app.models.user import User, UserSettings, UserRole
from app.repositories.user import UserRepository


@pytest.mark.database
class TestUserRepositoryEnhanced:
    """Enhanced test suite for UserRepository to achieve 80% coverage."""

    @pytest_asyncio.fixture
    async def user_repository(self, test_session):
        """Create user repository instance."""
        return UserRepository(test_session)

    @pytest_asyncio.fixture
    async def sample_users(self, user_repository):
        """Create multiple sample users for testing."""
        users = []
        user_specs = [
            {
                "username": "user1", 
                "email": "user1@example.com", 
                "full_name": "User One",
                "subscription_tier": "free",
                "is_active": True
            },
            {
                "username": "user2", 
                "email": "user2@example.com", 
                "full_name": "User Two",
                "subscription_tier": "premium",
                "is_active": True
            },
            {
                "username": "user3", 
                "email": "user3@example.com", 
                "full_name": "User Three",
                "subscription_tier": "free",
                "is_active": False
            },
            {
                "username": "premium1", 
                "email": "premium1@example.com", 
                "full_name": "Premium User",
                "subscription_tier": "premium",
                "is_active": True,
                "openrouter_api_key": "api_key_123"
            }
        ]

        for spec in user_specs:
            user = await user_repository.create(**spec, hashed_password="hashed123")
            users.append(user)

        return users

    @pytest.mark.asyncio
    async def test_get_by_email(self, user_repository, sample_users):
        """Test retrieving user by email address."""
        users = sample_users
        
        user = await user_repository.get_by_email("user1@example.com")
        assert user is not None
        assert user.email == "user1@example.com"
        assert user.username == "user1"
        
        # Test non-existent email
        user = await user_repository.get_by_email("nonexistent@example.com")
        assert user is None

    @pytest.mark.asyncio
    async def test_get_by_username(self, user_repository, sample_users):
        """Test retrieving user by username."""
        users = sample_users
        
        user = await user_repository.get_by_username("user1")
        assert user is not None
        assert user.username == "user1"
        assert user.email == "user1@example.com"
        
        # Test non-existent username
        user = await user_repository.get_by_username("nonexistent")
        assert user is None

    @pytest.mark.asyncio
    async def test_get_by_email_or_username(self, user_repository, sample_users):
        """Test retrieving user by email or username."""
        users = sample_users
        
        # Test with email
        user = await user_repository.get_by_email_or_username("user1@example.com")
        assert user is not None
        assert user.email == "user1@example.com"
        
        # Test with username
        user = await user_repository.get_by_email_or_username("user2")
        assert user is not None
        assert user.username == "user2"
        
        # Test non-existent
        user = await user_repository.get_by_email_or_username("nonexistent")
        assert user is None

    @pytest.mark.asyncio
    async def test_get_with_settings(self, user_repository, sample_users):
        """Test retrieving user with settings loaded."""
        users = sample_users
        user_id = str(users[0].id)
        
        user = await user_repository.get_with_settings(user_id)
        assert user is not None
        assert hasattr(user, 'settings')

    @pytest.mark.asyncio
    async def test_get_with_all_relationships(self, user_repository, sample_users):
        """Test retrieving user with all relationships loaded."""
        users = sample_users
        user_id = str(users[0].id)
        
        user = await user_repository.get_with_all_relationships(user_id)
        assert user is not None
        assert hasattr(user, 'settings')
        assert hasattr(user, 'sessions')
        assert hasattr(user, 'ssh_profiles')
        assert hasattr(user, 'ssh_keys')

    @pytest.mark.asyncio
    async def test_create_user_with_settings(self, user_repository):
        """Test creating user with default settings."""
        user = await user_repository.create_user_with_settings(
            email="newuser@example.com",
            username="newuser",
            password_hash="hashed123",
            full_name="New User"
        )
        
        assert user.email == "newuser@example.com"
        assert user.username == "newuser"
        assert user.settings is not None
        assert user.settings.user_id == user.id

    @pytest.mark.asyncio
    async def test_is_email_taken(self, user_repository, sample_users):
        """Test checking if email is already taken."""
        users = sample_users
        
        # Test existing email
        is_taken = await user_repository.is_email_taken("user1@example.com")
        assert is_taken is True
        
        # Test non-existing email
        is_taken = await user_repository.is_email_taken("available@example.com")
        assert is_taken is False
        
        # Test with exclusion
        user_id = str(users[0].id)
        is_taken = await user_repository.is_email_taken("user1@example.com", exclude_user_id=user_id)
        assert is_taken is False

    @pytest.mark.asyncio
    async def test_is_username_taken(self, user_repository, sample_users):
        """Test checking if username is already taken."""
        users = sample_users
        
        # Test existing username
        is_taken = await user_repository.is_username_taken("user1")
        assert is_taken is True
        
        # Test non-existing username
        is_taken = await user_repository.is_username_taken("available")
        assert is_taken is False
        
        # Test with exclusion
        user_id = str(users[0].id)
        is_taken = await user_repository.is_username_taken("user1", exclude_user_id=user_id)
        assert is_taken is False

    @pytest.mark.asyncio
    async def test_get_active_users(self, user_repository, sample_users):
        """Test retrieving active users."""
        users = sample_users
        
        active_users = await user_repository.get_active_users()
        assert len(active_users) >= 3  # user1, user2, premium1 are active
        
        for user in active_users:
            assert user.is_active is True
        
        # Test pagination
        page1 = await user_repository.get_active_users(offset=0, limit=2)
        page2 = await user_repository.get_active_users(offset=2, limit=2)
        assert len(page1) == 2
        assert len(page2) >= 1

    @pytest.mark.asyncio
    async def test_get_users_by_subscription(self, user_repository, sample_users):
        """Test retrieving users by subscription tier."""
        users = sample_users
        
        # Test free tier users
        free_users = await user_repository.get_users_by_subscription("free")
        assert len(free_users) >= 2  # user1 and user3
        
        for user in free_users:
            assert user.subscription_tier == "free"
        
        # Test premium tier users
        premium_users = await user_repository.get_users_by_subscription("premium")
        assert len(premium_users) >= 2  # user2 and premium1
        
        for user in premium_users:
            assert user.subscription_tier == "premium"

    @pytest.mark.asyncio
    async def test_get_locked_users(self, user_repository, sample_users):
        """Test retrieving locked users."""
        users = sample_users
        
        # Initially no locked users
        locked_users = await user_repository.get_locked_users()
        assert len(locked_users) == 0
        
        # Lock a user manually
        user = users[0]
        user.locked_until = datetime.now(UTC) + timedelta(hours=1)
        await user_repository.session.flush()
        
        # Now should find the locked user
        locked_users = await user_repository.get_locked_users()
        assert len(locked_users) >= 1
        assert user.id in [u.id for u in locked_users]

    @pytest.mark.asyncio
    async def test_unlock_expired_users(self, user_repository, sample_users, test_session):
        """Test unlocking users whose lock time has expired."""
        users = sample_users
        
        # Lock two users: one expired, one still locked
        expired_user = users[0]
        expired_user.locked_until = datetime.now(UTC) - timedelta(hours=1)  # Expired
        expired_user.failed_login_attempts = 3
        
        still_locked_user = users[1]
        still_locked_user.locked_until = datetime.now(UTC) + timedelta(hours=1)  # Still locked
        still_locked_user.failed_login_attempts = 2
        
        await test_session.flush()
        
        # Unlock expired users
        unlocked_count = await user_repository.unlock_expired_users()
        assert unlocked_count >= 1
        
        # Check the expired user was unlocked
        await test_session.refresh(expired_user)
        assert expired_user.locked_until is None
        assert expired_user.failed_login_attempts == 0
        
        # Check the still locked user remains locked
        await test_session.refresh(still_locked_user)
        assert still_locked_user.locked_until is not None

    @pytest.mark.asyncio
    async def test_get_users_with_api_keys(self, user_repository, sample_users):
        """Test retrieving users who have API keys."""
        users = sample_users
        
        users_with_keys = await user_repository.get_users_with_api_keys()
        assert len(users_with_keys) >= 1  # premium1 has an API key
        
        for user in users_with_keys:
            assert user.openrouter_api_key is not None

    @pytest.mark.asyncio
    async def test_search_users(self, user_repository, sample_users):
        """Test searching users by various criteria."""
        users = sample_users
        
        # Search by username
        results = await user_repository.search_users("user")
        assert len(results) >= 3  # user1, user2, user3
        
        # Search by email
        results = await user_repository.search_users("@example.com")
        assert len(results) >= 4
        
        # Search by full name
        results = await user_repository.search_users("Premium")
        assert len(results) >= 1
        
        # Search with no matches
        results = await user_repository.search_users("nonexistent")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_get_user_stats(self, user_repository, sample_users):
        """Test getting comprehensive user statistics."""
        users = sample_users
        user_id = str(users[0].id)
        
        stats = await user_repository.get_user_stats(user_id)
        
        assert "user_id" in stats
        assert "account_created" in stats
        assert "subscription_tier" in stats
        assert "total_sessions" in stats
        assert "active_sessions" in stats
        assert "ssh_profiles_count" in stats
        assert "ssh_keys_count" in stats
        assert "has_api_key" in stats
        
        assert stats["user_id"] == user_id
        assert isinstance(stats["total_sessions"], int)
        assert isinstance(stats["has_api_key"], bool)
        
        # Test non-existent user
        stats = await user_repository.get_user_stats("non-existent-id")
        assert stats == {}

    @pytest.mark.asyncio
    async def test_update_last_login(self, user_repository, sample_users):
        """Test updating user's last login timestamp."""
        users = sample_users
        user = users[0]
        user_id = str(user.id)
        
        # Set some failed attempts initially
        user.failed_login_attempts = 3
        user.locked_until = datetime.now(UTC) + timedelta(hours=1)
        await user_repository.session.flush()
        
        await user_repository.update_last_login(user_id)
        
        # Refresh to get updated data
        await user_repository.session.refresh(user)
        
        assert user.last_login_at is not None
        assert user.failed_login_attempts == 0
        assert user.locked_until is None

    @pytest.mark.asyncio
    async def test_increment_failed_login(self, user_repository, sample_users):
        """Test incrementing failed login attempts."""
        users = sample_users
        user = users[0]
        user_id = str(user.id)
        
        initial_attempts = user.failed_login_attempts or 0
        
        updated_user = await user_repository.increment_failed_login(user_id)
        
        assert updated_user is not None
        assert updated_user.failed_login_attempts == initial_attempts + 1
        
        # Test non-existent user
        result = await user_repository.increment_failed_login("non-existent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_deactivate_user(self, user_repository, sample_users):
        """Test deactivating a user account."""
        users = sample_users
        user = users[0]
        user_id = str(user.id)
        
        # Ensure user is initially active
        assert user.is_active is True
        
        success = await user_repository.deactivate_user(user_id)
        assert success is True
        
        # Refresh to get updated data
        await user_repository.session.refresh(user)
        assert user.is_active is False
        
        # Test non-existent user
        success = await user_repository.deactivate_user("non-existent-id")
        assert success is False

    @pytest.mark.asyncio
    async def test_reactivate_user(self, user_repository, sample_users):
        """Test reactivating a user account."""
        users = sample_users
        user = users[2]  # user3 is initially inactive
        user_id = str(user.id)
        
        # Ensure user is initially inactive
        assert user.is_active is False
        
        success = await user_repository.reactivate_user(user_id)
        assert success is True
        
        # Refresh to get updated data
        await user_repository.session.refresh(user)
        assert user.is_active is True
        
        # Test non-existent user
        success = await user_repository.reactivate_user("non-existent-id")
        assert success is False

    @pytest.mark.asyncio
    async def test_repository_inheritance(self, user_repository):
        """Test that UserRepository properly inherits from BaseRepository."""
        # Test inherited methods work
        assert hasattr(user_repository, 'create')
        assert hasattr(user_repository, 'get_by_id')
        assert hasattr(user_repository, 'update')
        assert hasattr(user_repository, 'delete')
        assert hasattr(user_repository, 'list')
        assert hasattr(user_repository, 'count')

    @pytest.mark.asyncio
    async def test_edge_cases_empty_results(self, user_repository):
        """Test edge cases with empty results."""
        # Search with impossible criteria
        users = await user_repository.search_users("impossible_user_that_does_not_exist")
        assert users == []
        
        # Get users for non-existent subscription
        users = await user_repository.get_users_by_subscription("non-existent-tier")
        assert users == []
        
        # Get stats for non-existent user
        stats = await user_repository.get_user_stats("non-existent-user-id")
        assert stats == {}

    @pytest.mark.asyncio
    async def test_pagination_edge_cases(self, user_repository, sample_users):
        """Test pagination with edge cases."""
        users = sample_users
        
        # Test large offset
        results = await user_repository.get_active_users(offset=1000, limit=10)
        assert len(results) == 0
        
        # Test zero limit
        results = await user_repository.get_active_users(offset=0, limit=0)
        assert len(results) == 0
        
        # Test large limit
        results = await user_repository.get_active_users(offset=0, limit=1000)
        assert len(results) >= 3  # At least our test users

    @pytest.mark.asyncio
    async def test_case_sensitivity(self, user_repository, sample_users):
        """Test case sensitivity in searches."""
        users = sample_users
        
        # Search should be case-insensitive
        results = await user_repository.search_users("USER")
        assert len(results) >= 3
        
        results = await user_repository.search_users("EXAMPLE.COM")
        assert len(results) >= 4

    @pytest.mark.asyncio
    async def test_performance_with_large_data(self, user_repository, test_session):
        """Test performance with multiple users."""
        # Create additional users for performance testing
        additional_users = []
        for i in range(20):
            user = User(
                username=f"perftest_{i}",
                email=f"perftest_{i}@example.com",
                full_name=f"Performance Test User {i}",
                hashed_password="hashed123",
                subscription_tier="free" if i % 2 == 0 else "premium",
                is_active=True
            )
            additional_users.append(user)
        
        test_session.add_all(additional_users)
        await test_session.commit()
        
        # Test search performance
        start_time = datetime.now(UTC)
        results = await user_repository.search_users("perftest")
        end_time = datetime.now(UTC)
        
        assert len(results) >= 20
        # Should complete within reasonable time
        assert (end_time - start_time).total_seconds() < 1.0

    @pytest.mark.asyncio
    async def test_complex_search_scenarios(self, user_repository, sample_users):
        """Test complex search scenarios."""
        users = sample_users
        
        # Search with partial match
        results = await user_repository.search_users("use")
        assert len(results) >= 3
        
        # Search with special characters
        results = await user_repository.search_users("@")
        assert len(results) >= 4
        
        # Search with numbers
        results = await user_repository.search_users("1")
        assert len(results) >= 2  # user1 and premium1

    @pytest.mark.asyncio
    async def test_subscription_tier_filtering(self, user_repository, sample_users):
        """Test comprehensive subscription tier filtering."""
        users = sample_users
        
        # Test with pagination
        free_page1 = await user_repository.get_users_by_subscription("free", offset=0, limit=1)
        free_page2 = await user_repository.get_users_by_subscription("free", offset=1, limit=1)
        
        assert len(free_page1) == 1
        assert len(free_page2) >= 1
        
        # Ensure different users in different pages
        if len(free_page2) > 0:
            assert free_page1[0].id != free_page2[0].id

    @pytest.mark.asyncio
    async def test_api_key_filtering(self, user_repository, sample_users):
        """Test API key filtering with pagination."""
        users = sample_users
        
        # Test pagination for users with API keys
        page1 = await user_repository.get_users_with_api_keys(offset=0, limit=1)
        assert len(page1) <= 1
        
        if len(page1) > 0:
            assert page1[0].openrouter_api_key is not None