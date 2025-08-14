"""
CORS configuration for DevPocket API.

Configures Cross-Origin Resource Sharing (CORS) settings to allow
the Flutter mobile app and web clients to access the API securely.
"""

from typing import List, Union
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import logger


def setup_cors(app: FastAPI) -> None:
    """
    Configure CORS middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    
    # Get CORS settings from configuration
    cors_settings = settings.cors
    
    # Log CORS configuration (but not in production for security)
    if settings.app_debug:
        logger.info(
            f"Configuring CORS with origins: {cors_settings.origins}",
            extra={
                "allow_credentials": cors_settings.allow_credentials,
                "allow_methods": cors_settings.allow_methods,
                "allow_headers": cors_settings.allow_headers
            }
        )
    
    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_settings.origins,
        allow_credentials=cors_settings.allow_credentials,
        allow_methods=cors_settings.allow_methods,
        allow_headers=cors_settings.allow_headers,
        expose_headers=[
            "X-Request-ID",
            "X-API-Version",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset"
        ],
        max_age=86400,  # Cache preflight requests for 24 hours
    )
    
    logger.info("CORS middleware configured successfully")


def get_cors_origins_for_environment(debug: bool = False) -> List[str]:
    """
    Get appropriate CORS origins based on environment.
    
    Args:
        debug: Whether in debug/development mode
        
    Returns:
        List of allowed origins
    """
    if debug:
        # Development origins
        return [
            "http://localhost:3000",      # React development server
            "http://127.0.0.1:3000",
            "http://localhost:8080",      # Alternative development port
            "http://127.0.0.1:8080",
            "http://localhost:5000",      # Flutter web development
            "http://127.0.0.1:5000",
            "capacitor://localhost",      # Capacitor apps
            "ionic://localhost",          # Ionic apps
        ]
    else:
        # Production origins
        return [
            "https://devpocket.app",
            "https://www.devpocket.app",
            "https://app.devpocket.app",
            "capacitor://devpocket.app",  # Capacitor mobile apps
            "ionic://devpocket.app",      # Ionic mobile apps
        ]


def validate_cors_origin(origin: str) -> bool:
    """
    Validate if an origin is allowed for CORS.
    
    Args:
        origin: Origin to validate
        
    Returns:
        True if origin is allowed, False otherwise
    """
    allowed_origins = settings.cors_origins
    
    # Check exact matches
    if origin in allowed_origins:
        return True
    
    # Check wildcard patterns (for development)
    if settings.app_debug:
        # Allow localhost with any port in debug mode
        if origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:"):
            return True
        
        # Allow capacitor and ionic schemes
        if origin.startswith("capacitor://") or origin.startswith("ionic://"):
            return True
    
    return False


class CORSConfig:
    """CORS configuration helper class."""
    
    # Standard headers that mobile apps typically need
    MOBILE_HEADERS = [
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-Device-ID",
        "X-App-Version",
        "X-Platform",
    ]
    
    # Methods commonly used by mobile apps
    MOBILE_METHODS = [
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
        "HEAD"
    ]
    
    # Headers to expose to mobile clients
    EXPOSED_HEADERS = [
        "X-Request-ID",
        "X-API-Version",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "X-Auth-Token-Expires",
        "Content-Disposition",  # For file downloads
        "Content-Length",
    ]
    
    @classmethod
    def get_mobile_cors_config(cls) -> dict:
        """
        Get CORS configuration optimized for mobile apps.
        
        Returns:
            Dictionary with CORS configuration
        """
        return {
            "allow_origins": get_cors_origins_for_environment(settings.app_debug),
            "allow_credentials": True,
            "allow_methods": cls.MOBILE_METHODS,
            "allow_headers": cls.MOBILE_HEADERS,
            "expose_headers": cls.EXPOSED_HEADERS,
            "max_age": 86400,  # Cache preflight for 24 hours
        }
    
    @classmethod
    def get_restrictive_cors_config(cls) -> dict:
        """
        Get restrictive CORS configuration for production.
        
        Returns:
            Dictionary with restrictive CORS configuration
        """
        return {
            "allow_origins": [
                "https://devpocket.app",
                "https://www.devpocket.app",
                "https://app.devpocket.app"
            ],
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": [
                "Accept",
                "Content-Type",
                "Authorization",
                "X-Requested-With"
            ],
            "expose_headers": cls.EXPOSED_HEADERS,
            "max_age": 3600,  # Cache preflight for 1 hour
        }
    
    @classmethod
    def get_development_cors_config(cls) -> dict:
        """
        Get permissive CORS configuration for development.
        
        Returns:
            Dictionary with development CORS configuration
        """
        return {
            "allow_origins": ["*"],  # Allow all origins in development
            "allow_credentials": False,  # Can't use credentials with wildcard
            "allow_methods": ["*"],  # Allow all methods
            "allow_headers": ["*"],  # Allow all headers
            "expose_headers": cls.EXPOSED_HEADERS,
            "max_age": 300,  # Short cache for development
        }


def setup_cors_for_environment(app: FastAPI, environment: str = "development") -> None:
    """
    Setup CORS based on environment.
    
    Args:
        app: FastAPI application instance
        environment: Environment name (development, staging, production)
    """
    if environment == "development":
        config = CORSConfig.get_development_cors_config()
    elif environment == "production":
        config = CORSConfig.get_restrictive_cors_config()
    else:
        config = CORSConfig.get_mobile_cors_config()
    
    app.add_middleware(CORSMiddleware, **config)
    
    logger.info(f"CORS configured for {environment} environment")