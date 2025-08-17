"""
Middleware package for DevPocket API.

Contains middleware for authentication, CORS, rate limiting,
security headers, and other cross-cutting concerns.
"""

from .auth import AuthenticationMiddleware
from .cors import setup_cors
from .rate_limit import RateLimitMiddleware
from .security import SecurityHeadersMiddleware

__all__ = [
    "AuthenticationMiddleware",
    "RateLimitMiddleware",
    "SecurityHeadersMiddleware",
    "setup_cors",
]
