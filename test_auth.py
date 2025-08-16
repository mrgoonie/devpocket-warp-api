#!/usr/bin/env python3
"""
Simple test script for DevPocket authentication system.

This script tests the basic functionality of the authentication system
without requiring external dependencies like Redis or PostgreSQL.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock environment variables for testing
os.environ.setdefault(
    "JWT_SECRET_KEY", "test-secret-key-for-development-32-chars-minimum-length"
)
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


def test_password_security():
    """Test password hashing and verification."""
    print("Testing password security...")

    try:
        from app.auth.security import (
            hash_password,
            verify_password,
            is_password_strong,
        )

        # Test password strength validation
        weak_password = "123"
        strong_password = "MyStrongP@ssw0rd!"

        is_strong_weak, errors_weak = is_password_strong(weak_password)
        is_strong_strong, errors_strong = is_password_strong(strong_password)

        assert not is_strong_weak, "Weak password should not be considered strong"
        assert is_strong_strong, "Strong password should be considered strong"
        assert len(errors_weak) > 0, "Weak password should have validation errors"
        assert (
            len(errors_strong) == 0
        ), "Strong password should have no validation errors"

        print("✓ Password strength validation working correctly")

        # Test password hashing
        test_password = "TestPassword123!"
        hashed = hash_password(test_password)

        assert (
            hashed != test_password
        ), "Hashed password should not equal plain password"
        assert verify_password(
            test_password, hashed
        ), "Password verification should succeed"
        assert not verify_password(
            "wrong_password", hashed
        ), "Wrong password should fail verification"

        print("✓ Password hashing and verification working correctly")

    except Exception as e:
        print(f"✗ Password security test failed: {e}")
        return False

    return True


def test_jwt_tokens():
    """Test JWT token creation and verification."""
    print("Testing JWT token functionality...")

    try:
        from app.auth.security import (
            create_access_token,
            create_refresh_token,
            decode_token,
            verify_token,
        )

        # Test data
        user_data = {
            "sub": "test-user-id",
            "email": "test@example.com",
            "subscription_tier": "free",
        }

        # Test access token creation
        access_token = create_access_token(user_data)
        assert access_token is not None, "Access token should be created"
        assert len(access_token) > 10, "Access token should have reasonable length"

        print("✓ Access token creation working")

        # Test refresh token creation
        refresh_token = create_refresh_token(user_data)
        assert refresh_token is not None, "Refresh token should be created"
        assert (
            refresh_token != access_token
        ), "Refresh token should differ from access token"

        print("✓ Refresh token creation working")

        # Test token decoding
        decoded_payload = decode_token(access_token)
        assert (
            decoded_payload["sub"] == user_data["sub"]
        ), "Decoded subject should match"
        assert (
            decoded_payload["email"] == user_data["email"]
        ), "Decoded email should match"
        assert "exp" in decoded_payload, "Token should have expiration"
        assert "iat" in decoded_payload, "Token should have issued at time"
        assert "type" in decoded_payload, "Token should have type"

        print("✓ Token decoding working correctly")

        # Test token verification
        verified_payload = verify_token(access_token)
        assert verified_payload is not None, "Token verification should succeed"
        assert (
            verified_payload["sub"] == user_data["sub"]
        ), "Verified payload should match"

        print("✓ Token verification working correctly")

        # Test invalid token
        invalid_payload = verify_token("invalid.jwt.token")
        assert invalid_payload is None, "Invalid token should return None"

        print("✓ Invalid token handling working correctly")

    except Exception as e:
        print(f"✗ JWT token test failed: {e}")
        return False

    return True


def test_schemas():
    """Test Pydantic schemas validation."""
    print("Testing Pydantic schemas...")

    try:
        from app.auth.schemas import (
            UserCreate,
            is_password_strong,
        )

        # Test password strength function
        weak_pass = "123"
        strong_pass = "StrongP@ss123!"

        is_strong_weak, errors_weak = is_password_strong(weak_pass)
        is_strong_strong, errors_strong = is_password_strong(strong_pass)

        assert (
            not is_strong_weak and len(errors_weak) > 0
        ), "Weak password validation failed"
        assert (
            is_strong_strong and len(errors_strong) == 0
        ), "Strong password validation failed"

        print("✓ Password strength validation in schemas working")

        # Test valid user creation schema
        valid_user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "StrongP@ss123!",
            "device_id": "test-device",
            "device_type": "ios",
        }

        user_create = UserCreate(**valid_user_data)
        assert user_create.email == "test@example.com", "Email should be set correctly"
        assert user_create.username == "testuser", "Username should be set correctly"

        print("✓ UserCreate schema validation working")

        # Test invalid user creation (weak password)
        invalid_user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "weak",  # This should fail validation
        }

        try:
            UserCreate(**invalid_user_data)
            assert False, "Weak password should cause validation error"
        except ValueError as e:
            assert "Password requirements not met" in str(
                e
            ), "Should get password validation error"
            print("✓ Weak password validation working in schemas")

    except Exception as e:
        print(f"✗ Schema test failed: {e}")
        return False

    return True


def main():
    """Run all authentication tests."""
    print("DevPocket Authentication System Test Suite")
    print("=" * 50)

    tests = [
        test_password_security,
        test_jwt_tokens,
        test_schemas,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        print(f"\n{test.__name__}:")
        if test():
            passed += 1
            print("✓ PASSED")
        else:
            print("✗ FAILED")

    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Authentication system is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
