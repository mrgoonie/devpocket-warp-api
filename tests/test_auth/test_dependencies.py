"""
Test authentication dependencies and middleware.
"""

import pytest
from fastapi import Request, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from unittest.mock import Mock, AsyncMock

from app.auth.dependencies import (
    get_token_from_request, get_current_user, get_current_active_user,
    get_optional_current_user, require_subscription_tier,
    get_user_from_token, AuthenticationError, InactiveUserError
)
from app.auth.security import create_access_token, set_redis_client
from app.models.user import User
from tests.factories import UserFactory, VerifiedUserFactory, PremiumUserFactory


@pytest.mark.auth
@pytest.mark.unit
class TestTokenExtraction:
    """Test token extraction from requests."""
    
    async def test_get_token_from_bearer_header(self):
        """Test extracting token from Bearer header."""
        request = Mock(spec=Request)
        request.cookies = {}
        
        bearer_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="test_token_123"
        )
        
        token = await get_token_from_request(
            request=request,
            oauth2_token=None,
            bearer_token=bearer_credentials
        )
        
        assert token == "test_token_123"
    
    async def test_get_token_from_oauth2_scheme(self):
        """Test extracting token from OAuth2 scheme."""
        request = Mock(spec=Request)
        request.cookies = {}
        
        token = await get_token_from_request(
            request=request,
            oauth2_token="oauth2_token_456",
            bearer_token=None
        )
        
        assert token == "oauth2_token_456"
    
    async def test_get_token_from_cookie(self):
        """Test extracting token from cookie."""
        request = Mock(spec=Request)
        request.cookies = {"access_token": "cookie_token_789"}
        
        token = await get_token_from_request(
            request=request,
            oauth2_token=None,
            bearer_token=None
        )
        
        assert token == "cookie_token_789"
    
    async def test_get_token_priority_order(self):
        """Test token extraction priority (Bearer > OAuth2 > Cookie)."""
        request = Mock(spec=Request)
        request.cookies = {"access_token": "cookie_token"}
        
        bearer_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="bearer_token"
        )
        
        token = await get_token_from_request(
            request=request,
            oauth2_token="oauth2_token",
            bearer_token=bearer_credentials
        )
        
        # Bearer should have highest priority
        assert token == "bearer_token"
    
    async def test_get_token_no_token_found(self):
        """Test when no token is found."""
        request = Mock(spec=Request)
        request.cookies = {}
        
        token = await get_token_from_request(
            request=request,
            oauth2_token=None,
            bearer_token=None
        )
        
        assert token is None


@pytest.mark.auth
@pytest.mark.unit
class TestCurrentUser:
    """Test current user extraction and validation."""
    
    async def test_get_current_user_success(self, test_session, mock_redis):
        """Test successful user authentication."""
        set_redis_client(mock_redis)
        
        # Create user in database
        user = VerifiedUserFactory()
        test_session.add(user)
        await test_session.commit()
        
        # Create valid token
        token = create_access_token({"sub": user.id})
        
        # Mock Redis to return no blacklist
        mock_redis.get.return_value = None
        
        authenticated_user = await get_current_user(test_session, token)
        
        assert authenticated_user.id == user.id
        assert authenticated_user.email == user.email
    
    async def test_get_current_user_no_token(self, test_session):
        """Test authentication without token."""
        with pytest.raises(AuthenticationError, match="Authentication token required"):
            await get_current_user(test_session, None)
    
    async def test_get_current_user_invalid_token(self, test_session, mock_redis):
        """Test authentication with invalid token."""
        set_redis_client(mock_redis)
        mock_redis.get.return_value = None
        
        invalid_token = "invalid.jwt.token"
        
        with pytest.raises(AuthenticationError, match="Invalid or expired token"):
            await get_current_user(test_session, invalid_token)
    
    async def test_get_current_user_blacklisted_token(self, test_session, mock_redis):
        """Test authentication with blacklisted token."""
        set_redis_client(mock_redis)
        
        # Create user and token
        user = VerifiedUserFactory()
        test_session.add(user)
        await test_session.commit()
        
        token = create_access_token({"sub": user.id})
        
        # Mock Redis to return blacklisted
        mock_redis.get.return_value = "blacklisted"
        
        with pytest.raises(AuthenticationError, match="Token has been revoked"):
            await get_current_user(test_session, token)
    
    async def test_get_current_user_user_not_found(self, test_session, mock_redis):
        """Test authentication when user doesn't exist."""
        set_redis_client(mock_redis)
        mock_redis.get.return_value = None
        
        # Create token for non-existent user
        token = create_access_token({"sub": "non_existent_user_id"})
        
        with pytest.raises(AuthenticationError, match="User not found"):
            await get_current_user(test_session, token)
    
    async def test_get_current_user_malformed_token(self, test_session, mock_redis):
        """Test authentication with malformed token payload."""
        set_redis_client(mock_redis)
        mock_redis.get.return_value = None
        
        # Create token without required 'sub' field
        token = create_access_token({"user_id": "123", "sub": ""})
        
        with pytest.raises(AuthenticationError, match="Invalid token format"):
            await get_current_user(test_session, token)


@pytest.mark.auth
@pytest.mark.unit
class TestActiveUser:
    """Test active user validation."""
    
    async def test_get_current_active_user_success(self, test_session):
        """Test getting active user successfully."""
        user = VerifiedUserFactory()
        user.is_active = True
        user.is_verified = True
        
        active_user = await get_current_active_user(user)
        
        assert active_user == user
    
    async def test_get_current_active_user_inactive(self, test_session):
        """Test getting inactive user."""
        user = VerifiedUserFactory()
        user.is_active = False
        
        with pytest.raises(InactiveUserError, match="Account has been deactivated"):
            await get_current_active_user(user)
    
    async def test_get_current_active_user_unverified(self, test_session):
        """Test getting unverified user."""
        user = UserFactory()
        user.is_active = True
        user.is_verified = False
        
        with pytest.raises(InactiveUserError, match="Email verification required"):
            await get_current_active_user(user)
    
    async def test_get_current_active_user_locked(self, test_session):
        """Test getting locked user."""
        user = VerifiedUserFactory()
        user.is_active = True
        user.is_verified = True
        
        # Lock the user account
        for _ in range(5):
            user.increment_failed_login()
        
        with pytest.raises(InactiveUserError, match="Account is temporarily locked"):
            await get_current_active_user(user)


@pytest.mark.auth
@pytest.mark.unit
class TestOptionalUser:
    """Test optional user authentication."""
    
    async def test_get_optional_current_user_with_valid_token(self, test_session, mock_redis):
        """Test optional authentication with valid token."""
        set_redis_client(mock_redis)
        
        # Create user
        user = VerifiedUserFactory()
        test_session.add(user)
        await test_session.commit()
        
        token = create_access_token({"sub": user.id})
        mock_redis.get.return_value = None
        
        optional_user = await get_optional_current_user(test_session, token)
        
        assert optional_user is not None
        assert optional_user.id == user.id
    
    async def test_get_optional_current_user_no_token(self, test_session):
        """Test optional authentication without token."""
        optional_user = await get_optional_current_user(test_session, None)
        
        assert optional_user is None
    
    async def test_get_optional_current_user_invalid_token(self, test_session, mock_redis):
        """Test optional authentication with invalid token."""
        set_redis_client(mock_redis)
        mock_redis.get.return_value = None
        
        invalid_token = "invalid.jwt.token"
        
        optional_user = await get_optional_current_user(test_session, invalid_token)
        
        assert optional_user is None


@pytest.mark.auth
@pytest.mark.unit
class TestSubscriptionTiers:
    """Test subscription tier requirements."""
    
    async def test_require_subscription_tier_sufficient(self):
        """Test user with sufficient subscription tier."""
        user = PremiumUserFactory()
        user.subscription_tier = "pro"
        
        result_user = await require_subscription_tier("free", user)
        
        assert result_user == user
    
    async def test_require_subscription_tier_exact_match(self):
        """Test user with exact subscription tier."""
        user = PremiumUserFactory()
        user.subscription_tier = "pro"
        
        result_user = await require_subscription_tier("pro", user)
        
        assert result_user == user
    
    async def test_require_subscription_tier_insufficient(self):
        """Test user with insufficient subscription tier."""
        user = UserFactory()
        user.subscription_tier = "free"
        
        with pytest.raises(HTTPException) as exc_info:
            await require_subscription_tier("pro", user)
        
        assert exc_info.value.status_code == 403
        assert "requires pro subscription" in exc_info.value.detail.lower()
    
    async def test_require_subscription_tier_unknown_tier(self):
        """Test user with unknown subscription tier."""
        user = UserFactory()
        user.subscription_tier = "unknown_tier"
        
        with pytest.raises(HTTPException) as exc_info:
            await require_subscription_tier("pro", user)
        
        assert exc_info.value.status_code == 403
    
    async def test_subscription_tier_hierarchy(self):
        """Test subscription tier hierarchy logic."""
        # Team tier should satisfy pro requirement
        team_user = UserFactory()
        team_user.subscription_tier = "team"
        
        result_user = await require_subscription_tier("pro", team_user)
        assert result_user == team_user
        
        # But free tier should not satisfy pro requirement
        free_user = UserFactory()
        free_user.subscription_tier = "free"
        
        with pytest.raises(HTTPException):
            await require_subscription_tier("pro", free_user)


@pytest.mark.auth
@pytest.mark.unit
class TestUserFromToken:
    """Test utility function for getting user from token."""
    
    async def test_get_user_from_token_success(self, test_session, mock_redis):
        """Test successfully getting user from token."""
        set_redis_client(mock_redis)
        
        # Create verified user
        user = VerifiedUserFactory()
        test_session.add(user)
        await test_session.commit()
        
        token = create_access_token({"sub": user.id})
        mock_redis.get.return_value = None
        
        result_user = await get_user_from_token(token, test_session)
        
        assert result_user is not None
        assert result_user.id == user.id
    
    async def test_get_user_from_token_blacklisted(self, test_session, mock_redis):
        """Test getting user from blacklisted token."""
        set_redis_client(mock_redis)
        
        token = "blacklisted_token"
        mock_redis.get.return_value = "blacklisted"
        
        result_user = await get_user_from_token(token, test_session)
        
        assert result_user is None
    
    async def test_get_user_from_token_invalid_token(self, test_session, mock_redis):
        """Test getting user from invalid token."""
        set_redis_client(mock_redis)
        mock_redis.get.return_value = None
        
        invalid_token = "invalid.jwt.token"
        
        result_user = await get_user_from_token(invalid_token, test_session)
        
        assert result_user is None
    
    async def test_get_user_from_token_inactive_user(self, test_session, mock_redis):
        """Test getting inactive user from token."""
        set_redis_client(mock_redis)
        
        # Create inactive user
        user = UserFactory()
        user.is_active = False
        user.is_verified = True
        test_session.add(user)
        await test_session.commit()
        
        token = create_access_token({"sub": user.id})
        mock_redis.get.return_value = None
        
        result_user = await get_user_from_token(token, test_session)
        
        assert result_user is None
    
    async def test_get_user_from_token_unverified_user(self, test_session, mock_redis):
        """Test getting unverified user from token."""
        set_redis_client(mock_redis)
        
        # Create unverified user
        user = UserFactory()
        user.is_active = True
        user.is_verified = False
        test_session.add(user)
        await test_session.commit()
        
        token = create_access_token({"sub": user.id})
        mock_redis.get.return_value = None
        
        result_user = await get_user_from_token(token, test_session)
        
        assert result_user is None


@pytest.mark.auth
@pytest.mark.unit
class TestAuthenticationErrors:
    """Test custom authentication error classes."""
    
    def test_authentication_error_default(self):
        """Test AuthenticationError with default message."""
        error = AuthenticationError()
        
        assert error.status_code == 401
        assert error.detail == "Could not validate credentials"
        assert error.headers == {"WWW-Authenticate": "Bearer"}
    
    def test_authentication_error_custom_message(self):
        """Test AuthenticationError with custom message."""
        custom_message = "Token has expired"
        error = AuthenticationError(custom_message)
        
        assert error.status_code == 401
        assert error.detail == custom_message
        assert error.headers == {"WWW-Authenticate": "Bearer"}
    
    def test_inactive_user_error_default(self):
        """Test InactiveUserError with default message."""
        error = InactiveUserError()
        
        assert error.status_code == 403
        assert error.detail == "Inactive user account"
    
    def test_inactive_user_error_custom_message(self):
        """Test InactiveUserError with custom message."""
        custom_message = "Account suspended"
        error = InactiveUserError(custom_message)
        
        assert error.status_code == 403
        assert error.detail == custom_message


@pytest.mark.auth
@pytest.mark.unit
class TestDependencyIntegration:
    """Test integration between different authentication dependencies."""
    
    async def test_dependency_chain_success(self, test_session, mock_redis):
        """Test successful dependency chain from token to active user."""
        set_redis_client(mock_redis)
        
        # Create verified user
        user = VerifiedUserFactory()
        test_session.add(user)
        await test_session.commit()
        
        token = create_access_token({"sub": user.id})
        mock_redis.get.return_value = None
        
        # Simulate dependency chain
        current_user = await get_current_user(test_session, token)
        active_user = await get_current_active_user(current_user)
        
        assert active_user.id == user.id
        assert active_user.is_active is True
        assert active_user.is_verified is True
    
    async def test_dependency_chain_failure_at_verification(self, test_session, mock_redis):
        """Test dependency chain failure at user verification step."""
        set_redis_client(mock_redis)
        
        # Create unverified user
        user = UserFactory()
        user.is_verified = False
        test_session.add(user)
        await test_session.commit()
        
        token = create_access_token({"sub": user.id})
        mock_redis.get.return_value = None
        
        # First step should succeed
        current_user = await get_current_user(test_session, token)
        assert current_user.id == user.id
        
        # Second step should fail
        with pytest.raises(InactiveUserError, match="Email verification required"):
            await get_current_active_user(current_user)
    
    async def test_subscription_tier_with_auth_chain(self, test_session, mock_redis):
        """Test subscription tier check with full auth chain."""
        set_redis_client(mock_redis)
        
        # Create free tier user
        user = VerifiedUserFactory()
        user.subscription_tier = "free"
        test_session.add(user)
        await test_session.commit()
        
        token = create_access_token({"sub": user.id})
        mock_redis.get.return_value = None
        
        # Get authenticated active user
        current_user = await get_current_user(test_session, token)
        active_user = await get_current_active_user(current_user)
        
        # Should succeed for free tier requirement
        result = await require_subscription_tier("free", active_user)
        assert result == active_user
        
        # Should fail for pro tier requirement
        with pytest.raises(HTTPException):
            await require_subscription_tier("pro", active_user)