"""
Main FastAPI application for DevPocket API.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import logger, log_request, log_error
from app.db.database import db_manager, init_database, check_database_connection


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
        # Close Redis connection
        if hasattr(app.state, 'redis'):
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
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    
    # Trusted host middleware (for production)
    if not settings.app_debug:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["devpocket.app", "api.devpocket.app", "*.devpocket.app"]
        )


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
                    "type": "http_error"
                }
            }
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
                    "message": "Internal server error" if not settings.app_debug else str(exc),
                    "type": "internal_error"
                }
            }
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
            "docs_url": "/docs" if settings.app_debug else None
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
                    "redis": "healthy" if redis_healthy else "unhealthy"
                },
                "timestamp": "2024-01-01T00:00:00Z"  # Will be updated with actual timestamp
            }
            
        except Exception as e:
            log_error(e, {"endpoint": "health_check"})
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "error": str(e) if settings.app_debug else "Service unavailable"
                }
            )
    
    # Import and include API routers here
    # This will be expanded when we create the API endpoints
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