# DevPocket Authentication System

This document describes the comprehensive JWT-based authentication system implemented for the DevPocket API.

## Overview

The authentication system provides secure user registration, login, token management, and password operations with the following features:

- **JWT-based authentication** with access and refresh tokens
- **Secure password hashing** using bcrypt with configurable rounds
- **Rate limiting** to prevent abuse and brute force attacks
- **Token blacklisting** for secure logout and session management
- **Password strength validation** with comprehensive requirements
- **Account security** with failed login tracking and automatic lockout
- **Password reset** functionality with secure tokens
- **Middleware integration** for automatic request authentication
- **Comprehensive error handling** with proper HTTP status codes

## Architecture

### Core Components

1. **Security Module** (`app/auth/security.py`)
   - Password hashing and verification
   - JWT token creation, validation, and blacklisting
   - Password reset token generation
   - Utility functions for secure operations

2. **Dependencies** (`app/auth/dependencies.py`)
   - FastAPI dependency functions for route protection
   - User extraction from JWT tokens
   - Subscription tier requirements
   - Optional authentication support

3. **Schemas** (`app/auth/schemas.py`)
   - Pydantic models for request/response validation
   - Password strength validation
   - Comprehensive input validation

4. **Router** (`app/auth/router.py`)
   - Authentication endpoints (register, login, logout, etc.)
   - Password management endpoints
   - Account status endpoints
   - Rate limiting implementation

5. **Middleware** (`app/middleware/`)
   - Authentication middleware for request processing
   - Rate limiting middleware
   - Security headers middleware
   - CORS configuration

## API Endpoints

### Authentication Endpoints

#### POST `/api/auth/register`
Register a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "username": "testuser",
  "password": "StrongP@ss123!",
  "display_name": "Test User",
  "device_id": "device-123",
  "device_type": "ios"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "user-uuid",
    "email": "user@example.com",
    "username": "testuser",
    "subscription_tier": "free",
    "is_active": true,
    "is_verified": false,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

#### POST `/api/auth/login`
Authenticate user with username/email and password.

**Request (Form Data):**
```
username=testuser
password=StrongP@ss123!
```

**Response:** Same as registration response.

#### POST `/api/auth/refresh`
Refresh access token using refresh token.

**Request:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

#### POST `/api/auth/logout`
Logout user and blacklist current token.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "message": "Logout successful"
}
```

#### GET `/api/auth/me`
Get current authenticated user information.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": "user-uuid",
  "email": "user@example.com",
  "username": "testuser",
  "subscription_tier": "free",
  "is_active": true,
  "is_verified": true,
  "created_at": "2024-01-01T00:00:00Z",
  "last_login_at": "2024-01-01T12:00:00Z"
}
```

### Password Management Endpoints

#### POST `/api/auth/forgot-password`
Request password reset email.

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "If the email exists in our system, you will receive a password reset link."
}
```

#### POST `/api/auth/reset-password`
Reset password using reset token.

**Request:**
```json
{
  "token": "reset-token-from-email",
  "new_password": "NewStrongP@ss123!"
}
```

**Response:**
```json
{
  "message": "Password reset successful"
}
```

#### POST `/api/auth/change-password`
Change password for authenticated user.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "current_password": "OldP@ss123!",
  "new_password": "NewStrongP@ss123!"
}
```

**Response:**
```json
{
  "message": "Password changed successfully"
}
```

#### GET `/api/auth/account-status`
Get account lock status and failed login attempts.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "is_locked": false,
  "locked_until": null,
  "failed_attempts": 0
}
```

## Security Features

### Password Requirements
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter  
- At least one number
- At least one special character

### Account Security
- **Failed Login Tracking**: Tracks failed login attempts per user
- **Account Lockout**: Automatically locks accounts after 5 failed attempts for 15 minutes
- **Rate Limiting**: Limits login attempts (5 per 15 minutes) and registration (3 per hour)

### Token Security
- **JWT Tokens**: Secure, stateless authentication
- **Token Expiration**: Access tokens expire in 24 hours, refresh tokens in 30 days
- **Token Blacklisting**: Logout immediately invalidates tokens
- **Secure Algorithms**: Uses HS256 with configurable secret keys

### API Security
- **Rate Limiting**: Per-IP and per-user rate limits based on subscription tier
- **Security Headers**: Comprehensive security headers on all responses
- **CORS Configuration**: Proper CORS setup for mobile app integration
- **Input Validation**: All inputs validated with Pydantic schemas

## Rate Limiting

### Default Limits (per minute)
- **Authentication endpoints**: 10 requests
- **General API**: 100 requests  
- **AI endpoints**: 30 requests
- **Upload endpoints**: 20 requests

### Subscription-based Limits
- **Free tier**: 60 API, 10 AI, 5 upload requests/minute
- **Pro tier**: 300 API, 60 AI, 20 upload requests/minute
- **Team tier**: 1000 API, 200 AI, 50 upload requests/minute
- **Enterprise tier**: 5000 API, 1000 AI, 200 upload requests/minute

## Usage Examples

### Using Authentication Dependencies

```python
from fastapi import Depends
from app.auth.dependencies import get_current_active_user, require_pro_tier
from app.models.user import User

@app.get("/api/user-profile")
async def get_profile(user: User = Depends(get_current_active_user)):
    return {"user_id": user.id, "username": user.username}

@app.get("/api/pro-feature")
async def pro_feature(user: User = Depends(require_pro_tier())):
    return {"message": "This is a Pro feature!"}
```

### Manual Token Validation

```python
from app.auth.security import verify_token
from app.auth.dependencies import get_user_from_token

# Verify token manually
token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
payload = verify_token(token)
if payload:
    user_id = payload["sub"]

# Get user from token (for WebSocket, background tasks)
async def websocket_auth(token: str, db: AsyncSession):
    user = await get_user_from_token(token, db)
    return user
```

## Configuration

### Environment Variables

```bash
# JWT Configuration
JWT_SECRET_KEY=your-32-character-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
JWT_REFRESH_EXPIRATION_DAYS=30

# Security Settings
BCRYPT_ROUNDS=12
RATE_LIMIT_PER_MINUTE=60
MAX_CONNECTIONS_PER_IP=100

# Database & Redis
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db
REDIS_URL=redis://localhost:6379/0
```

### Security Best Practices

1. **Generate Secure Keys**: Use `openssl rand -hex 32` for JWT secret
2. **Use HTTPS**: Always use HTTPS in production
3. **Environment Variables**: Store secrets in environment variables
4. **Rate Limiting**: Enable rate limiting in production
5. **Token Expiration**: Use appropriate token expiration times
6. **Password Strength**: Enforce strong password requirements
7. **Account Lockout**: Monitor and respond to failed login attempts

## Error Handling

The authentication system provides comprehensive error responses:

### Common Error Responses

```json
{
  "error": {
    "code": 401,
    "message": "Could not validate credentials",
    "type": "authentication_error"
  }
}
```

```json
{
  "error": {
    "code": 429,
    "message": "Rate limit exceeded. Please try again later.",
    "type": "rate_limit_error",
    "details": {
      "limit": 10,
      "current": 10,
      "reset_at": 1640995200
    }
  }
}
```

### HTTP Status Codes

- **200**: Successful operation
- **201**: User created successfully
- **400**: Bad request (validation error)
- **401**: Authentication required or failed
- **403**: Access forbidden (inactive user, insufficient permissions)
- **423**: Account locked
- **429**: Rate limit exceeded
- **500**: Internal server error

## Testing

Run the authentication test suite:

```bash
python test_auth.py
```

This tests:
- Password hashing and verification
- JWT token creation and validation
- Schema validation
- Password strength checking

## Integration

The authentication system is automatically integrated into the FastAPI application through middleware and dependencies. Simply use the provided dependencies in your route handlers to protect endpoints and access user information.

## Future Enhancements

- **Two-Factor Authentication**: SMS/TOTP support
- **OAuth2 Integration**: Social login providers
- **Session Management**: Advanced session tracking
- **Audit Logging**: Comprehensive security event logging
- **IP Whitelisting**: Location-based access control