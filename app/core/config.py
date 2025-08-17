"""
Configuration settings for DevPocket API.
"""

from typing import List, Union
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseModel):
    """Database configuration settings."""

    url: str
    host: str = "localhost"
    port: int = 5432
    name: str = "devpocket_warp_dev"
    user: str = "devpocket_user"
    password: str = "devpocket_password"


class RedisSettings(BaseModel):
    """Redis configuration settings."""

    url: str
    host: str = "localhost"
    port: int = 6379
    db: int = 0


class JWTSettings(BaseModel):
    """JWT configuration settings."""

    secret_key: str
    algorithm: str = "HS256"
    expiration_hours: int = 24
    refresh_expiration_days: int = 30


class CORSSettings(BaseModel):
    """CORS configuration settings."""

    origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    allow_credentials: bool = True
    allow_methods: List[str] = [
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "OPTIONS",
        "PATCH",
    ]
    allow_headers: List[str] = ["*"]


class OpenRouterSettings(BaseModel):
    """OpenRouter API configuration settings."""

    base_url: str = "https://openrouter.ai/api/v1"
    site_url: str = "https://devpocket.app"
    app_name: str = "DevPocket"


class SecuritySettings(BaseModel):
    """Security configuration settings."""

    bcrypt_rounds: int = 12
    max_connections_per_ip: int = 100
    rate_limit_per_minute: int = 60


class SSHSettings(BaseModel):
    """SSH configuration settings."""

    timeout: int = 30
    max_connections: int = 10
    key_storage_path: str = "./ssh_keys"


class TerminalSettings(BaseModel):
    """Terminal configuration settings."""

    timeout: int = 300
    max_command_length: int = 1000
    max_output_size: int = 1048576  # 1MB


class Settings(BaseSettings):
    """Application settings."""

    # Application settings
    app_name: str = "DevPocket API"
    app_version: str = "1.0.0"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # Database settings
    database_url: str = "postgresql://devpocket_user:devpocket_password@localhost:5432/devpocket_warp_dev"
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "devpocket_warp_dev"
    database_user: str = "devpocket_user"
    database_password: str = "devpocket_password"

    # Redis settings
    redis_url: str = "redis://localhost:6379/0"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: Union[int, str] = 0

    # JWT settings
    jwt_secret_key: str = "development-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    jwt_refresh_expiration_days: int = 30

    # CORS settings
    cors_origins: Union[
        str, List[str]
    ] = "http://localhost:3000,http://127.0.0.1:3000,https://devpocket.app"
    cors_allow_credentials: bool = True
    cors_allow_methods: Union[str, List[str]] = "GET,POST,PUT,DELETE,OPTIONS,PATCH"
    cors_allow_headers: Union[str, List[str]] = "*"

    # OpenRouter settings
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_site_url: str = "https://devpocket.app"
    openrouter_app_name: str = "DevPocket"

    # Security settings
    bcrypt_rounds: int = 12
    max_connections_per_ip: int = 100
    rate_limit_per_minute: int = 60

    # SSH settings
    ssh_timeout: int = 30
    ssh_max_connections: int = 10
    ssh_key_storage_path: str = "./ssh_keys"

    # Terminal settings
    terminal_timeout: int = 300
    max_command_length: int = 1000
    max_output_size: int = 1048576  # 1MB

    # Logging settings
    log_level: str = "INFO"
    log_format: str = "json"

    # Development settings
    reload: bool = True
    workers: Union[int, str] = 1

    # Additional secret key (for general encryption)
    secret_key: str = ""

    # Email service settings
    resend_api_key: str = ""
    from_email: str = "noreply@devpocket.app"
    support_email: str = "support@devpocket.app"

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v):
        """Validate JWT secret key."""
        if len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters long")
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def validate_cors_origins(cls, v):
        """Validate CORS origins."""
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v if isinstance(v, list) else [v]

    @field_validator("cors_allow_methods", mode="before")
    @classmethod
    def validate_cors_methods(cls, v):
        """Validate CORS methods."""
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v if isinstance(v, list) else [v]

    @field_validator("cors_allow_headers", mode="before")
    @classmethod
    def validate_cors_headers(cls, v):
        """Validate CORS headers."""
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v if isinstance(v, list) else [v]

    @field_validator("redis_db", mode="before")
    @classmethod
    def validate_redis_db(cls, v):
        """Validate Redis database number."""
        if isinstance(v, str):
            # Handle cases where redis_db might be set to a string like 'devpocket_dev'
            if v.isdigit():
                return int(v)
            else:
                # If it's not a valid integer, default to 0
                return 0
        return v if isinstance(v, int) else 0

    @field_validator("workers", mode="before")
    @classmethod
    def validate_workers(cls, v):
        """Validate number of workers."""
        if isinstance(v, str):
            # Handle boolean-like strings
            if v.lower() in ("true", "false"):
                return 1 if v.lower() == "true" else 1  # Default to 1 worker
            elif v.isdigit():
                return int(v)
            else:
                # If it's not a valid integer, default to 1
                return 1
        return v if isinstance(v, int) else 1

    @property
    def database(self) -> DatabaseSettings:
        """Get database settings."""
        return DatabaseSettings(
            url=self.database_url,
            host=self.database_host,
            port=self.database_port,
            name=self.database_name,
            user=self.database_user,
            password=self.database_password,
        )

    @property
    def redis(self) -> RedisSettings:
        """Get Redis settings."""
        # Ensure redis_db is always an integer
        db_value = self.redis_db
        if isinstance(db_value, str):
            db_value = 0 if not db_value.isdigit() else int(db_value)

        return RedisSettings(
            url=self.redis_url,
            host=self.redis_host,
            port=self.redis_port,
            db=db_value,
        )

    @property
    def jwt(self) -> JWTSettings:
        """Get JWT settings."""
        return JWTSettings(
            secret_key=self.jwt_secret_key,
            algorithm=self.jwt_algorithm,
            expiration_hours=self.jwt_expiration_hours,
            refresh_expiration_days=self.jwt_refresh_expiration_days,
        )

    @property
    def cors(self) -> CORSSettings:
        """Get CORS settings."""
        return CORSSettings(
            origins=self.cors_origins
            if isinstance(self.cors_origins, list)
            else [self.cors_origins],
            allow_credentials=self.cors_allow_credentials,
            allow_methods=self.cors_allow_methods
            if isinstance(self.cors_allow_methods, list)
            else [self.cors_allow_methods],
            allow_headers=self.cors_allow_headers
            if isinstance(self.cors_allow_headers, list)
            else [self.cors_allow_headers],
        )

    @property
    def openrouter(self) -> OpenRouterSettings:
        """Get OpenRouter settings."""
        return OpenRouterSettings(
            base_url=self.openrouter_base_url,
            site_url=self.openrouter_site_url,
            app_name=self.openrouter_app_name,
        )

    @property
    def security(self) -> SecuritySettings:
        """Get security settings."""
        return SecuritySettings(
            bcrypt_rounds=self.bcrypt_rounds,
            max_connections_per_ip=self.max_connections_per_ip,
            rate_limit_per_minute=self.rate_limit_per_minute,
        )

    @property
    def ssh(self) -> SSHSettings:
        """Get SSH settings."""
        return SSHSettings(
            timeout=self.ssh_timeout,
            max_connections=self.ssh_max_connections,
            key_storage_path=self.ssh_key_storage_path,
        )

    @property
    def terminal(self) -> TerminalSettings:
        """Get terminal settings."""
        return TerminalSettings(
            timeout=self.terminal_timeout,
            max_command_length=self.max_command_length,
            max_output_size=self.max_output_size,
        )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


# Global settings instance
settings = Settings()
