"""
Authentication middleware for DevPocket API.

Provides request-level authentication processing, user context injection,
and authentication logging for protected routes.
"""

from typing import Optional, Callable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.security import verify_token, is_token_blacklisted_sync
from app.core.logging import logger


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware for processing JWT tokens.

    This middleware:
    1. Extracts JWT tokens from requests
    2. Validates token format and signature
    3. Checks token blacklist status
    4. Adds user context to request state
    5. Logs authentication events
    """

    def __init__(self, app, skip_paths: Optional[list] = None):
        """
        Initialize authentication middleware.

        Args:
            app: FastAPI application instance
            skip_paths: List of paths to skip authentication for
        """
        super().__init__(app)

        # Default paths that don't require authentication
        self.skip_paths = skip_paths or [
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/forgot-password",
            "/api/auth/reset-password",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through authentication middleware.

        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        # Skip authentication for certain paths
        if self._should_skip_auth(request):
            return await call_next(request)

        # Extract token from request
        token = self._extract_token(request)

        if token:
            try:
                # Verify token
                payload = await self._verify_token(token)

                if payload:
                    # Add user context to request state
                    request.state.user_id = payload.get("sub")
                    request.state.user_email = payload.get("email")
                    request.state.subscription_tier = payload.get("subscription_tier")
                    request.state.token_payload = payload
                    request.state.is_authenticated = True

                    logger.debug(
                        f"User authenticated via middleware: {payload.get('sub')}"
                    )
                else:
                    request.state.is_authenticated = False
                    logger.debug("Invalid token in authentication middleware")

            except Exception as e:
                logger.warning(f"Authentication middleware error: {e}")
                request.state.is_authenticated = False
        else:
            request.state.is_authenticated = False

        # Add request timing for monitoring
        import time

        start_time = time.time()

        try:
            response = await call_next(request)

            # Log successful requests with authentication info
            process_time = time.time() - start_time
            self._log_request(request, response, process_time)

            return response

        except HTTPException as e:
            # Log authentication-related HTTP exceptions
            if e.status_code in (401, 403):
                logger.warning(
                    f"Authentication failed for {request.url.path}: {e.detail}",
                    extra={
                        "status_code": e.status_code,
                        "path": str(request.url.path),
                        "method": request.method,
                        "client_ip": self._get_client_ip(request),
                        "user_agent": request.headers.get("user-agent", "unknown"),
                    },
                )
            raise
        except Exception as e:
            # Log unexpected errors
            logger.error(
                f"Unexpected error in authentication middleware: {e}",
                extra={
                    "path": str(request.url.path),
                    "method": request.method,
                    "client_ip": self._get_client_ip(request),
                },
            )
            raise

    def _should_skip_auth(self, request: Request) -> bool:
        """
        Check if authentication should be skipped for this request.

        Args:
            request: FastAPI request object

        Returns:
            True if authentication should be skipped
        """
        path = request.url.path

        # Check exact matches
        if path in self.skip_paths:
            return True

        # Check prefix matches for certain paths
        skip_prefixes = ["/static/", "/assets/", "/_health"]
        if any(path.startswith(prefix) for prefix in skip_prefixes):
            return True

        return False

    def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from request.

        Args:
            request: FastAPI request object

        Returns:
            JWT token if found, None otherwise
        """
        # Try Authorization header first
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header.split(" ", 1)[1]

        # Try query parameter (for WebSocket upgrades)
        token_param = request.query_params.get("token")
        if token_param:
            return token_param

        # Try cookie
        token_cookie = request.cookies.get("access_token")
        if token_cookie:
            return token_cookie

        return None

    async def _verify_token(self, token: str) -> Optional[dict]:
        """
        Verify JWT token and return payload.

        Args:
            token: JWT token to verify

        Returns:
            Token payload if valid, None otherwise
        """
        try:
            # Check if token is blacklisted (sync version for middleware)
            if is_token_blacklisted_sync(token):
                logger.warning("Blacklisted token used in middleware")
                return None

            # Verify and decode token
            payload = verify_token(token)
            return payload

        except Exception as e:
            logger.debug(f"Token verification failed in middleware: {e}")
            return None

    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.

        Args:
            request: FastAPI request object

        Returns:
            Client IP address
        """
        # Check for forwarded IP headers (for proxy/load balancer scenarios)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"

    def _log_request(
        self, request: Request, response: Response, process_time: float
    ) -> None:
        """
        Log request details for monitoring and debugging.

        Args:
            request: FastAPI request object
            response: FastAPI response object
            process_time: Request processing time in seconds
        """
        # Only log detailed info for authenticated requests or errors
        if (
            getattr(request.state, "is_authenticated", False)
            or response.status_code >= 400
        ):
            log_data = {
                "method": request.method,
                "path": str(request.url.path),
                "status_code": response.status_code,
                "process_time": round(process_time, 4),
                "client_ip": self._get_client_ip(request),
                "user_agent": request.headers.get("user-agent", "unknown")[
                    :200
                ],  # Truncate long user agents
                "is_authenticated": getattr(request.state, "is_authenticated", False),
            }

            if getattr(request.state, "user_id", None):
                log_data["user_id"] = request.state.user_id
                log_data["subscription_tier"] = getattr(
                    request.state, "subscription_tier", "unknown"
                )

            if response.status_code >= 400:
                logger.warning("Request completed with error", extra=log_data)
            else:
                logger.info("Request completed successfully", extra=log_data)
