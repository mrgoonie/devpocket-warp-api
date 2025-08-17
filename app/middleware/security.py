"""
Security headers middleware for DevPocket API.

Adds security headers to all responses to protect against common web vulnerabilities
and improve the overall security posture of the application.
"""

from typing import Any, Dict, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security headers middleware.

    Adds essential security headers to protect against:
    - Cross-Site Scripting (XSS)
    - Clickjacking
    - Content type sniffing
    - HTTPS downgrade attacks
    - Information disclosure
    """

    def __init__(self, app: Any, headers: Optional[Dict[str, str]] = None) -> None:
        """
        Initialize security headers middleware.

        Args:
            app: FastAPI application instance
            headers: Custom headers to add (overrides defaults)
        """
        super().__init__(app)

        # Default security headers
        self.default_headers = {
            # Prevent XSS attacks
            "X-XSS-Protection": "1; mode=block",
            # Prevent content type sniffing
            "X-Content-Type-Options": "nosniff",
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            # Remove server information
            "Server": "DevPocket API",
            # Referrer policy for privacy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # Permissions policy (formerly Feature Policy)
            "Permissions-Policy": (
                "camera=(), "
                "microphone=(), "
                "geolocation=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "accelerometer=()"
            ),
        }

        # Add HSTS header for production
        if not settings.app_debug:
            self.default_headers.update(
                {
                    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload"
                }
            )

        # Content Security Policy for web endpoints
        if settings.app_debug:
            # Relaxed CSP for development
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self' ws: wss:; "
                "object-src 'none'; "
                "base-uri 'self'"
            )
        else:
            # Strict CSP for production
            csp = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self'; "
                "img-src 'self' data: https://devpocket.app; "
                "font-src 'self'; "
                "connect-src 'self' wss://api.devpocket.app; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "frame-ancestors 'none'"
            )

        self.default_headers["Content-Security-Policy"] = csp

        # Use custom headers if provided, otherwise use defaults
        self.headers = headers if headers is not None else self.default_headers

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """
        Add security headers to response.

        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain

        Returns:
            Response with security headers added
        """
        try:
            response: Response = await call_next(request)

            # Add security headers
            for header, value in self.headers.items():
                # Don't override headers that are already set
                if header not in response.headers:
                    # Use path-specific CSP for Content-Security-Policy
                    if header == "Content-Security-Policy":
                        path_specific_csp = SecurityConfig.get_csp_for_path(
                            request.url.path, debug=settings.app_debug
                        )
                        response.headers[header] = path_specific_csp
                    else:
                        response.headers[header] = value

            # Add API-specific headers
            self._add_api_headers(request, response)

            return response

        except Exception as e:
            # Even if there's an error, we want to add security headers
            # to the error response
            response = Response(
                content='{"error": {"code": 500, "message": "Internal server error"}}',
                status_code=500,
                media_type="application/json",
            )

            for header, value in self.headers.items():
                if header == "Content-Security-Policy":
                    path_specific_csp = SecurityConfig.get_csp_for_path(
                        request.url.path, debug=settings.app_debug
                    )
                    response.headers[header] = path_specific_csp
                else:
                    response.headers[header] = value

            # Log the error but don't expose it
            import logging

            logging.error(f"Security middleware error: {e}")

            return response

    def _add_api_headers(self, request: Request, response: Response) -> None:
        """
        Add API-specific security headers.

        Args:
            request: FastAPI request object
            response: FastAPI response object
        """
        # Add CORS headers if not already present (handled by CORS middleware)
        if "Access-Control-Allow-Origin" not in response.headers:
            # For API endpoints, we might want specific CORS handling
            if request.url.path.startswith("/api/"):
                response.headers["Access-Control-Allow-Origin"] = "*"

        # Add cache control headers for API responses
        if request.url.path.startswith("/api/"):
            if "Cache-Control" not in response.headers:
                # API responses should not be cached by default
                response.headers[
                    "Cache-Control"
                ] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"

        # Add security headers for authentication endpoints
        if request.url.path.startswith("/api/auth/"):
            response.headers["X-Auth-Service"] = "DevPocket"

            # Additional security for sensitive endpoints
            if request.url.path in ["/api/auth/login", "/api/auth/register"]:
                response.headers[
                    "X-Robots-Tag"
                ] = "noindex, nofollow, noarchive, nosnippet"

        # Add API versioning header
        response.headers["X-API-Version"] = settings.app_version

        # Add request ID header for debugging (if available in request state)
        request_id = getattr(request.state, "request_id", None)
        if request_id:
            response.headers["X-Request-ID"] = request_id


class SecurityConfig:
    """Configuration class for security settings."""

    @staticmethod
    def get_csp_for_path(path: str, debug: bool = False) -> str:
        """
        Get Content Security Policy for specific path.

        Args:
            path: Request path
            debug: Whether in debug mode

        Returns:
            CSP header value
        """
        if path.startswith("/docs") or path.startswith("/redoc"):
            # Relaxed CSP for API documentation
            return (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net blob:; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
                "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "worker-src blob:; "
                "connect-src 'self'"
            )
        elif path.startswith("/api/"):
            # Strict CSP for API endpoints
            return (
                "default-src 'none'; "
                "script-src 'none'; "
                "object-src 'none'; "
                "base-uri 'none'"
            )
        else:
            # Default CSP
            if debug:
                return (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                    "style-src 'self' 'unsafe-inline'; "
                    "img-src 'self' data: https:; "
                    "connect-src 'self' ws: wss:"
                )
            else:
                return (
                    "default-src 'self'; "
                    "script-src 'self'; "
                    "style-src 'self'; "
                    "img-src 'self' data: https://devpocket.app; "
                    "connect-src 'self' wss://api.devpocket.app; "
                    "object-src 'none'; "
                    "base-uri 'self'"
                )

    @staticmethod
    def get_headers_for_environment(debug: bool = False) -> Dict[str, str]:
        """
        Get security headers appropriate for environment.

        Args:
            debug: Whether in debug mode

        Returns:
            Dictionary of security headers
        """
        headers = {
            "X-XSS-Protection": "1; mode=block",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Server": "DevPocket API",
        }

        if not debug:
            headers.update(
                {
                    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
                    "Permissions-Policy": (
                        "camera=(), microphone=(), geolocation=(), "
                        "payment=(), usb=(), magnetometer=(), "
                        "gyroscope=(), accelerometer=()"
                    ),
                }
            )

        return headers
