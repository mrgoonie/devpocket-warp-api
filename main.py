"""
Main FastAPI application for DevPocket API.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import redis.asyncio as aioredis

from app.auth.security import set_redis_client
from app.auth.router import router as auth_router
from app.api.ssh import router as ssh_router
from app.api.sessions import router as sessions_router
from app.api.commands import router as commands_router
from app.api.ai import router as ai_router
from app.api.sync import router as sync_router
from app.api.profile import router as profile_router
from app.websocket import websocket_router
from app.websocket.manager import connection_manager
from app.core.config import settings
from app.core.logging import logger, log_request, log_error
from app.db.database import (
    db_manager,
    init_database,
    check_database_connection,
)
from app.middleware import (
    AuthenticationMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    setup_cors,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    try:
        # Initialize database
        await db_manager.connect()

        # Check database connection
        db_connected = await check_database_connection()
        if not db_connected:
            logger.error("Database connection failed during startup")
            raise RuntimeError("Database connection failed")

        # Initialize Redis
        app.state.redis = await aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )

        # Test Redis connection
        await app.state.redis.ping()
        logger.info("Redis connection established")

        # Set Redis client for authentication module
        set_redis_client(app.state.redis)

        # Set Redis client for WebSocket connection manager
        connection_manager.redis = app.state.redis

        # Initialize database tables if needed
        if settings.app_debug:
            await init_database()

        logger.info("Application startup completed successfully")

    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down application")

    try:
        # Stop WebSocket connection manager background tasks
        await connection_manager.stop_background_tasks()

        # Close Redis connection
        if hasattr(app.state, "redis"):
            await app.state.redis.close()
            logger.info("Redis connection closed")

        # Close database connections
        await db_manager.disconnect()

        logger.info("Application shutdown completed")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


def create_application() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        FastAPI: Configured FastAPI application
    """

    app = FastAPI(
        title=settings.app_name,
        description="AI-Powered Mobile Terminal Backend API",
        version=settings.app_version,
        debug=settings.app_debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.app_debug else None,
        redoc_url="/redoc" if settings.app_debug else None,
    )

    # Add middleware
    setup_middleware(app)

    # Add exception handlers
    setup_exception_handlers(app)

    # Add routes
    setup_routes(app)

    return app


def setup_middleware(app: FastAPI) -> None:
    """
    Set up application middleware.

    Args:
        app: FastAPI application instance
    """

    # Security headers middleware (first to ensure headers are always added)
    app.add_middleware(SecurityHeadersMiddleware)

    # Rate limiting middleware
    app.add_middleware(RateLimitMiddleware, enabled=True)

    # Authentication middleware (before routes that need auth)
    app.add_middleware(AuthenticationMiddleware)

    # CORS middleware using our setup function
    setup_cors(app)

    # Trusted host middleware (for production)
    if not settings.app_debug:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=[
                "devpocket.app",
                "api.devpocket.app",
                "*.devpocket.app",
            ],
        )

    logger.info("Middleware configured successfully")


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Set up application exception handlers.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc: HTTPException):
        """Handle HTTP exceptions."""
        log_error(exc, {"url": str(request.url), "method": request.method})
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "type": "http_error",
                }
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc: Exception):
        """Handle general exceptions."""
        log_error(exc, {"url": str(request.url), "method": request.method})
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": 500,
                    "message": (
                        "Internal server error" if not settings.app_debug else str(exc)
                    ),
                    "type": "internal_error",
                }
            },
        )


def setup_routes(app: FastAPI) -> None:
    """
    Set up application routes.

    Args:
        app: FastAPI application instance
    """

    @app.get("/")
    async def root():
        """Root endpoint - API status."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "operational",
            "docs_url": "/docs" if settings.app_debug else None,
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        try:
            # Check database
            db_healthy = await check_database_connection()

            # Check Redis
            redis_healthy = True
            try:
                await app.state.redis.ping()
            except Exception:
                redis_healthy = False

            status = "healthy" if db_healthy and redis_healthy else "unhealthy"

            return {
                "status": status,
                "checks": {
                    "database": "healthy" if db_healthy else "unhealthy",
                    "redis": "healthy" if redis_healthy else "unhealthy",
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            log_error(e, {"endpoint": "health_check"})
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "error": str(e) if settings.app_debug else "Service unavailable",
                },
            )

    # Include authentication routes
    app.include_router(auth_router)

    # Include Core API routers
    app.include_router(ssh_router)
    app.include_router(sessions_router)
    app.include_router(commands_router)
    app.include_router(ai_router)
    app.include_router(sync_router)
    app.include_router(profile_router)

    # Include WebSocket router
    app.include_router(websocket_router)

    logger.info("Routes configured successfully")


# Create the FastAPI application
app = create_application()


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on {settings.app_host}:{settings.app_port}")

    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.reload,
        workers=1 if settings.reload else settings.workers,
        log_level=settings.log_level.lower(),
        access_log=True,
    )
