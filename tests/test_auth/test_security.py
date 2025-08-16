"""
Test JWT and password security functionality.
"""

import pytest
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt

from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token,
    blacklist_token,
    is_token_blacklisted,
    generate_password_reset_token,
    verify_password_reset_token,
    generate_secure_token,
    is_password_strong,
    set_redis_client,
)
from app.core.config import settings


@pytest.mark.auth
@pytest.mark.unit
class TestPasswordSecurity:
    """Test password hashing and verification."""

    def test_password_hashing(self):
        """Test password hashing produces different hashes for same password."""
        password = "TestPassword123!"

        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2  # Salt should make them different
        assert len(hash1) > 50  # Bcrypt hashes are long
        assert hash1.startswith("$2b$")  # Bcrypt identifier

    def test_password_verification_success(self):
        """Test successful password verification."""
        password = "TestPassword123!"
        password_hash = hash_password(password)

        assert verify_password(password, password_hash) is True

    def test_password_verification_failure(self):
        """Test password verification with wrong password."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword456!"
        password_hash = hash_password(password)

        assert verify_password(wrong_password, password_hash) is False

    def test_password_verification_with_invalid_hash(self):
        """Test password verification with invalid hash."""
        password = "TestPassword123!"
        invalid_hash = "invalid_hash"

        assert verify_password(password, invalid_hash) is False

    def test_password_strength_validation_strong(self):
        """Test strong password validation."""
        strong_password = "StrongPass123!"

        is_strong, errors = is_password_strong(strong_password)

        assert is_strong is True
        assert len(errors) == 0

    def test_password_strength_validation_weak(self):
        """Test weak password validation."""
        weak_password = "weak"

        is_strong, errors = is_password_strong(weak_password)

        assert is_strong is False
        assert len(errors) > 0
        assert "Password must be at least 8 characters long" in errors
        assert "Password must contain at least one uppercase letter" in errors
        assert "Password must contain at least one number" in errors
        assert "Password must contain at least one special character" in errors

    def test_password_strength_validation_missing_elements(self):
        """Test password validation with missing elements."""
        test_cases = [
            (
                "lowercase123!",
                ["Password must contain at least one uppercase letter"],
            ),
            (
                "UPPERCASE123!",
                ["Password must contain at least one lowercase letter"],
            ),
            ("NoNumbers!", ["Password must contain at least one number"]),
            (
                "NoSpecial123",
                ["Password must contain at least one special character"],
            ),
        ]

        for password, expected_errors in test_cases:
            is_strong, errors = is_password_strong(password)
            assert is_strong is False
            for expected_error in expected_errors:
                assert expected_error in errors


@pytest.mark.auth
@pytest.mark.unit
class TestJWTTokens:
    """Test JWT token creation and verification."""

    def test_create_access_token(self):
        """Test access token creation."""
        user_data = {"sub": "test@example.com", "user_id": "123"}

        token = create_access_token(user_data)

        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long

        # Decode to verify structure
        payload = decode_token(token)
        assert payload["sub"] == "test@example.com"
        assert payload["user_id"] == "123"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_create_access_token_with_custom_expiry(self):
        """Test access token with custom expiration."""
        user_data = {"sub": "test@example.com"}
        custom_expiry = timedelta(minutes=30)

        token = create_access_token(user_data, expires_delta=custom_expiry)
        payload = decode_token(token)

        # Check expiration is approximately 30 minutes from now
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_exp = datetime.now(timezone.utc) + custom_expiry

        # Allow 10 second tolerance
        assert abs((exp_time - expected_exp).total_seconds()) < 10

    def test_create_access_token_missing_subject(self):
        """Test access token creation fails without subject."""
        user_data = {"user_id": "123"}  # Missing 'sub'

        with pytest.raises(ValueError, match="Token data must include 'sub'"):
            create_access_token(user_data)

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        user_data = {"sub": "test@example.com"}

        token = create_refresh_token(user_data)
        payload = decode_token(token)

        assert payload["sub"] == "test@example.com"
        assert payload["type"] == "refresh"
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_valid_token(self):
        """Test decoding a valid token."""
        user_data = {"sub": "test@example.com", "role": "user"}
        token = create_access_token(user_data)

        payload = decode_token(token)

        assert payload["sub"] == "test@example.com"
        assert payload["role"] == "user"
        assert payload["type"] == "access"

    def test_decode_invalid_token(self):
        """Test decoding an invalid token."""
        invalid_token = "invalid.jwt.token"

        with pytest.raises(JWTError):
            decode_token(invalid_token)

    def test_decode_expired_token(self):
        """Test decoding an expired token."""
        user_data = {"sub": "test@example.com"}
        expired_token = create_access_token(
            user_data, expires_delta=timedelta(seconds=-1)  # Already expired
        )

        with pytest.raises(JWTError, match="Token has expired"):
            decode_token(expired_token)

    def test_verify_valid_token(self):
        """Test verifying a valid token."""
        user_data = {"sub": "test@example.com"}
        token = create_access_token(user_data)

        payload = verify_token(token)

        assert payload is not None
        assert payload["sub"] == "test@example.com"

    def test_verify_invalid_token(self):
        """Test verifying an invalid token."""
        invalid_token = "invalid.jwt.token"

        payload = verify_token(invalid_token)

        assert payload is None

    def test_verify_expired_token(self):
        """Test verifying an expired token."""
        user_data = {"sub": "test@example.com"}
        expired_token = create_access_token(
            user_data, expires_delta=timedelta(seconds=-1)
        )

        payload = verify_token(expired_token)

        assert payload is None


@pytest.mark.auth
@pytest.mark.unit
class TestTokenBlacklisting:
    """Test token blacklisting functionality."""

    @pytest.mark.asyncio
    async def test_blacklist_token(self, mock_redis):
        """Test adding token to blacklist."""
        set_redis_client(mock_redis)

        user_data = {"sub": "test@example.com"}
        token = create_access_token(user_data)

        await blacklist_token(token)

        # Verify Redis was called with correct parameters
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0].startswith("blacklist:")
        assert call_args[0][2] == "blacklisted"

    @pytest.mark.asyncio
    async def test_blacklist_token_with_custom_expiry(self, mock_redis):
        """Test blacklisting token with custom expiration."""
        set_redis_client(mock_redis)

        token = "test.jwt.token"
        custom_expiry = datetime.now(timezone.utc) + timedelta(hours=2)

        await blacklist_token(token, expires_at=custom_expiry)

        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_true(self, mock_redis):
        """Test checking if token is blacklisted (blacklisted)."""
        set_redis_client(mock_redis)
        mock_redis.get.return_value = "blacklisted"

        token = "test.jwt.token"

        is_blacklisted = await is_token_blacklisted(token)

        assert is_blacklisted is True
        mock_redis.get.assert_called_once_with(f"blacklist:{token}")

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_false(self, mock_redis):
        """Test checking if token is blacklisted (not blacklisted)."""
        set_redis_client(mock_redis)
        mock_redis.get.return_value = None

        token = "test.jwt.token"

        is_blacklisted = await is_token_blacklisted(token)

        assert is_blacklisted is False
        mock_redis.get.assert_called_once_with(f"blacklist:{token}")

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_redis_error(self, mock_redis):
        """Test token blacklist check with Redis error."""
        set_redis_client(mock_redis)
        mock_redis.get.side_effect = Exception("Redis connection error")

        token = "test.jwt.token"

        is_blacklisted = await is_token_blacklisted(token)

        assert is_blacklisted is False  # Should return False on error

    @pytest.mark.asyncio
    async def test_blacklist_token_no_redis(self):
        """Test blacklisting token when Redis is unavailable."""
        set_redis_client(None)

        token = "test.jwt.token"

        # Should not raise exception
        await blacklist_token(token)


@pytest.mark.auth
@pytest.mark.unit
class TestPasswordReset:
    """Test password reset token functionality."""

    def test_generate_password_reset_token(self):
        """Test generating password reset token."""
        email = "test@example.com"

        token = generate_password_reset_token(email)

        assert isinstance(token, str)
        assert len(token) > 50

        # Verify token contains correct information
        payload = decode_token(token)
        assert payload["sub"] == email
        assert payload["type"] == "password_reset"
        assert "reset_id" in payload

        # Check expiration is approximately 1 hour
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_exp = datetime.now(timezone.utc) + timedelta(hours=1)
        assert abs((exp_time - expected_exp).total_seconds()) < 10

    def test_verify_password_reset_token_valid(self):
        """Test verifying valid password reset token."""
        email = "test@example.com"
        token = generate_password_reset_token(email)

        verified_email = verify_password_reset_token(token)

        assert verified_email == email

    def test_verify_password_reset_token_invalid(self):
        """Test verifying invalid password reset token."""
        invalid_token = "invalid.jwt.token"

        verified_email = verify_password_reset_token(invalid_token)

        assert verified_email is None

    def test_verify_password_reset_token_wrong_type(self):
        """Test verifying token with wrong type."""
        # Create regular access token instead of reset token
        user_data = {"sub": "test@example.com"}
        access_token = create_access_token(user_data)

        verified_email = verify_password_reset_token(access_token)

        assert verified_email is None

    def test_verify_password_reset_token_expired(self):
        """Test verifying expired password reset token."""
        email = "test@example.com"

        # Create expired token using manual encoding
        data = {
            "sub": email,
            "type": "password_reset",
            "reset_id": "test123",
            "exp": datetime.now(timezone.utc)
            + timedelta(seconds=-1),  # Already expired
            "iat": datetime.now(timezone.utc),
        }

        expired_token = jwt.encode(
            data, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

        verified_email = verify_password_reset_token(expired_token)

        assert verified_email is None


@pytest.mark.auth
@pytest.mark.unit
class TestUtilities:
    """Test security utility functions."""

    def test_generate_secure_token_default_length(self):
        """Test generating secure token with default length."""
        token = generate_secure_token()

        assert isinstance(token, str)
        assert len(token) > 30  # URL-safe base64 encoding makes it longer

    def test_generate_secure_token_custom_length(self):
        """Test generating secure token with custom length."""
        length = 16
        token = generate_secure_token(length)

        assert isinstance(token, str)
        # URL-safe base64 encoding can make it longer than input
        assert len(token) >= length

    def test_generate_secure_token_uniqueness(self):
        """Test that generated tokens are unique."""
        tokens = [generate_secure_token() for _ in range(100)]

        # All tokens should be unique
        assert len(set(tokens)) == 100


@pytest.mark.auth
@pytest.mark.unit
class TestSecurityEdgeCases:
    """Test edge cases and error conditions."""

    def test_create_token_with_none_data(self):
        """Test token creation with None data."""
        with pytest.raises(AttributeError):
            create_access_token(None)

    def test_create_token_with_empty_subject(self):
        """Test token creation with empty subject."""
        user_data = {"sub": ""}

        with pytest.raises(ValueError, match="Token data must include 'sub'"):
            create_access_token(user_data)

    def test_decode_token_with_wrong_algorithm(self):
        """Test decoding token with wrong algorithm."""
        # Create token with different algorithm (not supported by our settings)
        from jose import jwt as jose_jwt

        payload = {
            "sub": "test@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        wrong_algo_token = jose_jwt.encode(payload, "wrong_secret", algorithm="HS512")

        with pytest.raises(JWTError):
            decode_token(wrong_algo_token)

    def test_decode_token_with_wrong_secret(self):
        """Test decoding token with wrong secret."""
        # Create token with different secret
        from jose import jwt as jose_jwt

        payload = {
            "sub": "test@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        wrong_secret_token = jose_jwt.encode(
            payload, "wrong_secret", algorithm=settings.jwt_algorithm
        )

        with pytest.raises(JWTError):
            decode_token(wrong_secret_token)

    def test_hash_password_with_empty_string(self):
        """Test hashing empty password."""
        empty_password = ""

        # Should still create a hash
        password_hash = hash_password(empty_password)
        assert isinstance(password_hash, str)
        assert len(password_hash) > 0

        # Should verify correctly
        assert verify_password(empty_password, password_hash) is True

    def test_verify_password_with_empty_hash(self):
        """Test verifying password with empty hash."""
        password = "TestPassword123!"
        empty_hash = ""

        assert verify_password(password, empty_hash) is False


@pytest.mark.auth
@pytest.mark.unit
class TestTokenTimingAttacks:
    """Test protection against timing attacks."""

    def test_password_verification_timing_consistency(self):
        """Test that password verification takes consistent time."""
        import time

        correct_password = "TestPassword123!"
        wrong_password = "WrongPassword456!"
        password_hash = hash_password(correct_password)

        # Measure time for correct password
        start_time = time.time()
        verify_password(correct_password, password_hash)
        correct_time = time.time() - start_time

        # Measure time for wrong password
        start_time = time.time()
        verify_password(wrong_password, password_hash)
        wrong_time = time.time() - start_time

        # Times should be roughly similar (within reasonable tolerance)
        # This is a basic check - bcrypt inherently provides timing attack protection
        time_diff = abs(correct_time - wrong_time)
        assert time_diff < 0.1  # Allow 100ms difference

    def test_token_verification_timing_consistency(self):
        """Test that token verification takes consistent time."""
        import time

        user_data = {"sub": "test@example.com"}
        valid_token = create_access_token(user_data)
        invalid_token = "invalid.jwt.token"

        # Measure time for valid token
        start_time = time.time()
        verify_token(valid_token)
        valid_time = time.time() - start_time

        # Measure time for invalid token
        start_time = time.time()
        verify_token(invalid_token)
        invalid_time = time.time() - start_time

        # Times should be roughly similar
        time_diff = abs(valid_time - invalid_time)
        assert time_diff < 0.1  # Allow 100ms difference
