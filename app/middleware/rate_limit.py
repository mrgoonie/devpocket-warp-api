"""
Rate limiting middleware for DevPocket API.

Provides request rate limiting based on IP address, user ID, and endpoint
to prevent abuse and ensure fair usage of the API.
"""

import time
from collections import defaultdict, deque
from typing import Dict, Deque, Tuple, Optional
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import logger


class RateLimitStore:
    """
    In-memory rate limit storage.
    In production, this should be replaced with Redis for distributed rate limiting.
    """

    def __init__(self):
        # Store format: {key: deque([(timestamp, count), ...])}
        self._store: Dict[str, Deque[Tuple[float, int]]] = defaultdict(deque)
        self._cleanup_interval = 60  # Clean up old entries every 60 seconds
        self._last_cleanup = time.time()

    def add_request(
        self, key: str, window: int = 60, limit: int = 100
    ) -> Tuple[bool, int, int]:
        """
        Add a request and check if rate limit is exceeded.

        Args:
            key: Rate limiting key (e.g., IP address or user ID)
            window: Time window in seconds
            limit: Maximum requests allowed in the window

        Returns:
            Tuple of (is_allowed, current_count, remaining_requests)
        """
        now = time.time()

        # Clean up old entries periodically
        self._cleanup_if_needed(now)

        # Get request queue for this key
        requests = self._store[key]

        # Remove old requests outside the window
        while requests and requests[0][0] < now - window:
            requests.popleft()

        # Count current requests in window
        current_count = sum(count for _, count in requests)

        # Check if limit is exceeded
        if current_count >= limit:
            return False, current_count, 0

        # Add this request
        requests.append((now, 1))
        remaining = limit - current_count - 1

        return True, current_count + 1, remaining

    def _cleanup_if_needed(self, now: float) -> None:
        """Clean up old entries to prevent memory leaks."""
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup_old_entries(now)
            self._last_cleanup = now

    def _cleanup_old_entries(self, now: float, max_age: int = 3600) -> None:
        """Remove entries older than max_age seconds."""
        cutoff = now - max_age
        keys_to_remove = []

        for key, requests in self._store.items():
            # Remove old requests
            while requests and requests[0][0] < cutoff:
                requests.popleft()

            # Remove empty queues
            if not requests:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._store[key]


# Global rate limit store
rate_limit_store = RateLimitStore()


class RateLimitConfig:
    """Rate limiting configuration for different endpoints and user types."""

    # Default rate limits (requests per minute)
    DEFAULT_LIMITS = {
        "global": 1000,  # Global limit per IP
        "auth": 10,  # Authentication endpoints
        "api": 100,  # General API endpoints
        "upload": 20,  # File upload endpoints
        "ai": 30,  # AI-powered endpoints
    }

    # Rate limits by subscription tier
    TIER_LIMITS = {
        "free": {
            "api": 60,  # 60 requests per minute
            "ai": 10,  # 10 AI requests per minute
            "upload": 5,  # 5 uploads per minute
        },
        "pro": {
            "api": 300,  # 300 requests per minute
            "ai": 60,  # 60 AI requests per minute
            "upload": 20,  # 20 uploads per minute
        },
        "team": {
            "api": 1000,  # 1000 requests per minute
            "ai": 200,  # 200 AI requests per minute
            "upload": 50,  # 50 uploads per minute
        },
        "enterprise": {
            "api": 5000,  # 5000 requests per minute
            "ai": 1000,  # 1000 AI requests per minute
            "upload": 200,  # 200 uploads per minute
        },
    }

    @classmethod
    def get_limit(
        cls, endpoint_type: str, subscription_tier: Optional[str] = None
    ) -> int:
        """
        Get rate limit for endpoint type and subscription tier.

        Args:
            endpoint_type: Type of endpoint (api, auth, ai, etc.)
            subscription_tier: User's subscription tier

        Returns:
            Rate limit (requests per minute)
        """
        if subscription_tier and subscription_tier in cls.TIER_LIMITS:
            return cls.TIER_LIMITS[subscription_tier].get(
                endpoint_type,
                cls.DEFAULT_LIMITS.get(endpoint_type, cls.DEFAULT_LIMITS["api"]),
            )

        return cls.DEFAULT_LIMITS.get(endpoint_type, cls.DEFAULT_LIMITS["api"])


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for API requests.

    This middleware:
    1. Tracks requests per IP address and user
    2. Applies different limits based on endpoint type
    3. Considers subscription tiers for authenticated users
    4. Returns 429 Too Many Requests when limits are exceeded
    5. Adds rate limit headers to responses
    """

    def __init__(self, app, enabled: bool = True):
        """
        Initialize rate limiting middleware.

        Args:
            app: FastAPI application instance
            enabled: Whether rate limiting is enabled
        """
        super().__init__(app)
        self.enabled = enabled

        # Paths that are exempt from rate limiting
        self.exempt_paths = ["/health", "/docs", "/redoc", "/openapi.json"]

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request through rate limiting middleware.

        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response with rate limit headers
        """
        if not self.enabled or self._is_exempt(request):
            return await call_next(request)

        try:
            # Determine endpoint type and rate limits
            endpoint_type = self._get_endpoint_type(request)
            client_ip = self._get_client_ip(request)
            user_id = getattr(request.state, "user_id", None)
            subscription_tier = getattr(request.state, "subscription_tier", None)

            # Check rate limits
            ip_allowed, ip_count, ip_remaining = self._check_ip_rate_limit(
                client_ip, endpoint_type
            )

            user_allowed, user_count, user_remaining = True, 0, 1000
            if user_id:
                (
                    user_allowed,
                    user_count,
                    user_remaining,
                ) = self._check_user_rate_limit(
                    user_id, endpoint_type, subscription_tier
                )

            # Use the most restrictive limit
            is_allowed = ip_allowed and user_allowed
            remaining = min(ip_remaining, user_remaining)
            current_count = max(ip_count, user_count)

            if not is_allowed:
                logger.warning(
                    f"Rate limit exceeded for {client_ip}",
                    extra={
                        "client_ip": client_ip,
                        "user_id": user_id,
                        "endpoint_type": endpoint_type,
                        "path": request.url.path,
                        "ip_count": ip_count,
                        "user_count": user_count,
                    },
                )

                return self._create_rate_limit_response(
                    current_count, remaining, endpoint_type
                )

            # Process request
            response = await call_next(request)

            # Add rate limit headers
            self._add_rate_limit_headers(
                response, current_count, remaining, endpoint_type
            )

            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            # Don't fail requests due to rate limiting errors
            return await call_next(request)

    def _is_exempt(self, request: Request) -> bool:
        """Check if request is exempt from rate limiting."""
        return request.url.path in self.exempt_paths

    def _get_endpoint_type(self, request: Request) -> str:
        """
        Determine endpoint type for rate limiting.

        Args:
            request: FastAPI request object

        Returns:
            Endpoint type string
        """
        path = request.url.path

        if path.startswith("/api/auth/"):
            return "auth"
        elif path.startswith("/api/ai/"):
            return "ai"
        elif path.startswith("/api/upload/") or "upload" in path:
            return "upload"
        elif path.startswith("/api/"):
            return "api"
        else:
            return "global"

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def _check_ip_rate_limit(
        self, ip: str, endpoint_type: str
    ) -> Tuple[bool, int, int]:
        """
        Check IP-based rate limit.

        Args:
            ip: Client IP address
            endpoint_type: Type of endpoint being accessed

        Returns:
            Tuple of (is_allowed, current_count, remaining)
        """
        limit = RateLimitConfig.get_limit(endpoint_type)
        key = f"ip:{ip}:{endpoint_type}"

        return rate_limit_store.add_request(key, window=60, limit=limit)

    def _check_user_rate_limit(
        self,
        user_id: str,
        endpoint_type: str,
        subscription_tier: Optional[str],
    ) -> Tuple[bool, int, int]:
        """
        Check user-based rate limit.

        Args:
            user_id: User identifier
            endpoint_type: Type of endpoint being accessed
            subscription_tier: User's subscription tier

        Returns:
            Tuple of (is_allowed, current_count, remaining)
        """
        limit = RateLimitConfig.get_limit(endpoint_type, subscription_tier)
        key = f"user:{user_id}:{endpoint_type}"

        return rate_limit_store.add_request(key, window=60, limit=limit)

    def _create_rate_limit_response(
        self, current_count: int, remaining: int, endpoint_type: str
    ) -> Response:
        """Create rate limit exceeded response."""
        limit = RateLimitConfig.get_limit(endpoint_type)

        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(time.time()) + 60),
            "Retry-After": "60",
        }

        error_response = {
            "error": {
                "code": 429,
                "message": "Rate limit exceeded. Please try again later.",
                "type": "rate_limit_error",
                "details": {
                    "limit": limit,
                    "current": current_count,
                    "reset_at": int(time.time()) + 60,
                },
            }
        }

        return Response(
            content=str(error_response),
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers=headers,
            media_type="application/json",
        )

    def _add_rate_limit_headers(
        self,
        response: Response,
        current_count: int,
        remaining: int,
        endpoint_type: str,
    ) -> None:
        """Add rate limit headers to response."""
        limit = RateLimitConfig.get_limit(endpoint_type)

        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
