"""
Test authentication API endpoints.
"""

import pytest
from datetime import datetime, timedelta
from fastapi import status
from unittest.mock import patch, AsyncMock

from app.auth.security import create_access_token, hash_password
from app.models.user import User
from tests.factories import UserFactory, VerifiedUserFactory


@pytest.mark.auth
@pytest.mark.api
class TestRegistrationEndpoint:
    """Test user registration endpoint."""
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, async_client):
        """Test successful user registration."""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "SecurePass123!",
            "full_name": "New User"
        }
        
        response = await async_client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert data["full_name"] == user_data["full_name"]
        assert "id" in data
        assert "password" not in data  # Password should not be returned
        assert data["is_verified"] is False  # Should start unverified
    
    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(self, async_client, test_session):
        """Test registration with duplicate email."""
        # Create existing user
        existing_user = VerifiedUserFactory()
        test_session.add(existing_user)
        await test_session.commit()
        
        user_data = {
            "email": existing_user.email,  # Duplicate email
            "username": "newuser",
            "password": "SecurePass123!",
            "full_name": "New User"
        }
        
        response = await async_client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "email" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_register_user_duplicate_username(self, async_client, test_session):
        """Test registration with duplicate username."""
        # Create existing user
        existing_user = VerifiedUserFactory()
        test_session.add(existing_user)
        await test_session.commit()
        
        user_data = {
            "email": "newuser@example.com",
            "username": existing_user.username,  # Duplicate username
            "password": "SecurePass123!",
            "full_name": "New User"
        }
        
        response = await async_client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "username" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_register_user_weak_password(self, async_client):
        """Test registration with weak password."""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "weak",  # Weak password
            "full_name": "New User"
        }
        
        response = await async_client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "password" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_register_user_invalid_email(self, async_client):
        """Test registration with invalid email format."""
        user_data = {
            "email": "invalid-email",  # Invalid email
            "username": "newuser",
            "password": "SecurePass123!",
            "full_name": "New User"
        }
        
        response = await async_client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_register_user_missing_fields(self, async_client):
        """Test registration with missing required fields."""
        incomplete_data = {
            "email": "newuser@example.com",
            # Missing username, password, full_name
        }
        
        response = await async_client.post("/api/auth/register", json=incomplete_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.auth
@pytest.mark.api
class TestLoginEndpoint:
    """Test user login endpoint."""
    
    @pytest.mark.asyncio
    async def test_login_success(self, async_client, test_session):
        """Test successful user login."""
        password = "SecurePass123!"
        user = VerifiedUserFactory()
        user.password_hash = hash_password(password)
        test_session.add(user)
        await test_session.commit()
        
        login_data = {
            "username": user.email,
            "password": password
        }
        
        response = await async_client.post(
            "/api/auth/login",
            data=login_data,  # OAuth2 expects form data
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    @pytest.mark.asyncio
    async def test_login_with_username(self, async_client, test_session):
        """Test login using username instead of email."""
        password = "SecurePass123!"
        user = VerifiedUserFactory()
        user.password_hash = hash_password(password)
        test_session.add(user)
        await test_session.commit()
        
        login_data = {
            "username": user.username,  # Use username instead of email
            "password": password
        }
        
        response = await async_client.post(
            "/api/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, async_client, test_session):
        """Test login with invalid credentials."""
        user = VerifiedUserFactory()
        user.password_hash = hash_password("correct_password")
        test_session.add(user)
        await test_session.commit()
        
        login_data = {
            "username": user.email,
            "password": "wrong_password"
        }
        
        response = await async_client.post(
            "/api/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "Invalid credentials" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, async_client):
        """Test login with non-existent user."""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "password123"
        }
        
        response = await async_client.post(
            "/api/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_login_unverified_user(self, async_client, test_session):
        """Test login with unverified user."""
        password = "SecurePass123!"
        user = UserFactory()  # Unverified user
        user.password_hash = hash_password(password)
        user.is_verified = False
        test_session.add(user)
        await test_session.commit()
        
        login_data = {
            "username": user.email,
            "password": password
        }
        
        response = await async_client.post(
            "/api/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "verify" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_login_inactive_user(self, async_client, test_session):
        """Test login with inactive user."""
        password = "SecurePass123!"
        user = VerifiedUserFactory()
        user.password_hash = hash_password(password)
        user.is_active = False
        test_session.add(user)
        await test_session.commit()
        
        login_data = {
            "username": user.email,
            "password": password
        }
        
        response = await async_client.post(
            "/api/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "deactivated" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_login_locked_user(self, async_client, test_session):
        """Test login with locked user account."""
        password = "SecurePass123!"
        user = VerifiedUserFactory()
        user.password_hash = hash_password(password)
        
        # Lock the account
        for _ in range(5):
            user.increment_failed_login()
        
        test_session.add(user)
        await test_session.commit()
        
        login_data = {
            "username": user.email,
            "password": password
        }
        
        response = await async_client.post(
            "/api/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "locked" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_login_failed_attempt_tracking(self, async_client, test_session):
        """Test failed login attempt tracking."""
        password = "SecurePass123!"
        user = VerifiedUserFactory()
        user.password_hash = hash_password(password)
        user.failed_login_attempts = 0
        test_session.add(user)
        await test_session.commit()
        
        login_data = {
            "username": user.email,
            "password": "wrong_password"
        }
        
        # Make failed login attempt
        response = await async_client.post(
            "/api/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Check that failed attempts were incremented
        await test_session.refresh(user)
        assert user.failed_login_attempts == 1


@pytest.mark.auth
@pytest.mark.api
class TestLogoutEndpoint:
    """Test user logout endpoint."""
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_logout_success(self, async_client, auth_headers, mock_redis):
        """Test successful logout."""
        response = await async_client.post(
            "/api/auth/logout",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Successfully logged out"
        
        # Verify token was blacklisted
        mock_redis.setex.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_logout_without_auth(self, async_client):
        """Test logout without authentication."""
        response = await async_client.post("/api/auth/logout")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.auth
@pytest.mark.api
class TestRefreshTokenEndpoint:
    """Test token refresh endpoint."""
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, async_client, test_session):
        """Test successful token refresh."""
        user = VerifiedUserFactory()
        test_session.add(user)
        await test_session.commit()
        
        # Create refresh token
        refresh_token = create_refresh_token({"sub": user.id})
        
        refresh_data = {"refresh_token": refresh_token}
        
        response = await async_client.post("/api/auth/refresh", json=refresh_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data  # New refresh token
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, async_client):
        """Test refresh with invalid token."""
        refresh_data = {"refresh_token": "invalid.refresh.token"}
        
        response = await async_client.post("/api/auth/refresh", json=refresh_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_refresh_token_wrong_type(self, async_client, test_session):
        """Test refresh with access token instead of refresh token."""
        user = VerifiedUserFactory()
        test_session.add(user)
        await test_session.commit()
        
        # Use access token instead of refresh token
        access_token = create_access_token({"sub": user.id})
        refresh_data = {"refresh_token": access_token}
        
        response = await async_client.post("/api/auth/refresh", json=refresh_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.auth
@pytest.mark.api
class TestPasswordResetEndpoints:
    """Test password reset endpoints."""
    
    @patch('app.auth.router.send_password_reset_email')
    @pytest.mark.asyncio
    async def test_request_password_reset_success(self, mock_send_email, async_client, test_session):
        """Test successful password reset request."""
        user = VerifiedUserFactory()
        test_session.add(user)
        await test_session.commit()
        
        mock_send_email.return_value = AsyncMock()
        
        reset_data = {"email": user.email}
        
        response = await async_client.post("/api/auth/password-reset-request", json=reset_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "reset email sent" in data["message"].lower()
        
        # Verify email was sent
        mock_send_email.assert_called_once_with(user.email)
    
    @pytest.mark.asyncio
    async def test_request_password_reset_nonexistent_email(self, async_client):
        """Test password reset request for non-existent email."""
        reset_data = {"email": "nonexistent@example.com"}
        
        response = await async_client.post("/api/auth/password-reset-request", json=reset_data)
        
        # Should return success to prevent email enumeration
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_confirm_password_reset_success(self, async_client, test_session):
        """Test successful password reset confirmation."""
        user = VerifiedUserFactory()
        test_session.add(user)
        await test_session.commit()
        
        # Generate reset token
        from app.auth.security import generate_password_reset_token
        reset_token = generate_password_reset_token(user.email)
        
        new_password = "NewSecurePass123!"
        reset_data = {
            "token": reset_token,
            "new_password": new_password
        }
        
        response = await async_client.post("/api/auth/password-reset-confirm", json=reset_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "password reset successfully" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_confirm_password_reset_invalid_token(self, async_client):
        """Test password reset with invalid token."""
        reset_data = {
            "token": "invalid.reset.token",
            "new_password": "NewSecurePass123!"
        }
        
        response = await async_client.post("/api/auth/password-reset-confirm", json=reset_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "invalid" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_confirm_password_reset_weak_password(self, async_client, test_session):
        """Test password reset with weak new password."""
        user = VerifiedUserFactory()
        test_session.add(user)
        await test_session.commit()
        
        from app.auth.security import generate_password_reset_token
        reset_token = generate_password_reset_token(user.email)
        
        reset_data = {
            "token": reset_token,
            "new_password": "weak"  # Weak password
        }
        
        response = await async_client.post("/api/auth/password-reset-confirm", json=reset_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "password" in data["detail"].lower()


@pytest.mark.auth
@pytest.mark.api
class TestEmailVerificationEndpoints:
    """Test email verification endpoints."""
    
    @patch('app.auth.router.send_verification_email')
    @pytest.mark.asyncio
    async def test_request_email_verification_success(self, mock_send_email, async_client, test_session):
        """Test successful email verification request."""
        user = UserFactory()  # Unverified user
        user.is_verified = False
        test_session.add(user)
        await test_session.commit()
        
        mock_send_email.return_value = AsyncMock()
        
        verify_data = {"email": user.email}
        
        response = await async_client.post("/api/auth/verify-email-request", json=verify_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "verification email sent" in data["message"].lower()
        
        # Verify email was sent
        mock_send_email.assert_called_once_with(user.email)
    
    @pytest.mark.asyncio
    async def test_request_email_verification_already_verified(self, async_client, test_session):
        """Test email verification request for already verified user."""
        user = VerifiedUserFactory()  # Already verified
        test_session.add(user)
        await test_session.commit()
        
        verify_data = {"email": user.email}
        
        response = await async_client.post("/api/auth/verify-email-request", json=verify_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "already verified" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_confirm_email_verification_success(self, async_client, test_session):
        """Test successful email verification confirmation."""
        user = UserFactory()
        user.is_verified = False
        test_session.add(user)
        await test_session.commit()
        
        # Generate verification token
        verification_token = create_access_token(
            {"sub": user.email, "type": "email_verification"},
            expires_delta=timedelta(hours=24)
        )
        
        response = await async_client.get(f"/api/auth/verify-email/{verification_token}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "email verified successfully" in data["message"].lower()
        
        # Check that user is now verified
        await test_session.refresh(user)
        assert user.is_verified is True
    
    @pytest.mark.asyncio
    async def test_confirm_email_verification_invalid_token(self, async_client):
        """Test email verification with invalid token."""
        response = await async_client.get("/api/auth/verify-email/invalid.token")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "invalid" in data["detail"].lower()


@pytest.mark.auth
@pytest.mark.api
class TestProtectedEndpoints:
    """Test access to protected endpoints."""
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_protected_endpoint_with_auth(self, async_client, auth_headers):
        """Test accessing protected endpoint with valid authentication."""
        response = await async_client.get("/api/auth/me", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "username" in data
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_without_auth(self, async_client):
        """Test accessing protected endpoint without authentication."""
        response = await async_client.get("/api/auth/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_with_invalid_token(self, async_client):
        """Test accessing protected endpoint with invalid token."""
        headers = {"Authorization": "Bearer invalid.jwt.token"}
        
        response = await async_client.get("/api/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_with_expired_token(self, async_client, test_session):
        """Test accessing protected endpoint with expired token."""
        user = VerifiedUserFactory()
        test_session.add(user)
        await test_session.commit()
        
        # Create expired token
        expired_token = create_access_token(
            {"sub": user.id},
            expires_delta=timedelta(seconds=-1)
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        response = await async_client.get("/api/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.auth
@pytest.mark.api
class TestRateLimiting:
    """Test rate limiting on authentication endpoints."""
    
    @pytest.mark.asyncio
    async def test_login_rate_limiting(self, async_client, test_session):
        """Test rate limiting on login endpoint."""
        user = VerifiedUserFactory()
        user.password_hash = hash_password("password123")
        test_session.add(user)
        await test_session.commit()
        
        login_data = {
            "username": user.email,
            "password": "wrong_password"
        }
        
        # Make multiple failed login attempts
        for i in range(10):
            response = await async_client.post(
                "/api/auth/login",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if i < 5:
                # Should return 401 for failed login
                assert response.status_code == status.HTTP_401_UNAUTHORIZED
            else:
                # Should return 429 for rate limiting after too many attempts
                assert response.status_code in [status.HTTP_429_TOO_MANY_REQUESTS, status.HTTP_401_UNAUTHORIZED]
    
    @pytest.mark.asyncio
    async def test_registration_rate_limiting(self, async_client):
        """Test rate limiting on registration endpoint."""
        # Make multiple registration attempts
        for i in range(10):
            user_data = {
                "email": f"user{i}@example.com",
                "username": f"user{i}",
                "password": "SecurePass123!",
                "full_name": f"User {i}"
            }
            
            response = await async_client.post("/api/auth/register", json=user_data)
            
            if i < 5:
                # Should succeed or fail with validation error
                assert response.status_code in [
                    status.HTTP_201_CREATED,
                    status.HTTP_400_BAD_REQUEST,
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ]
            else:
                # May hit rate limiting
                assert response.status_code in [
                    status.HTTP_201_CREATED,
                    status.HTTP_400_BAD_REQUEST,
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    status.HTTP_429_TOO_MANY_REQUESTS
                ]