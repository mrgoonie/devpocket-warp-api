"""
Pydantic schemas for SSH management endpoints.

Contains request and response models for SSH profiles, keys, and related operations.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, validator
from enum import Enum


class SSHKeyType(str, Enum):
    """Supported SSH key types."""
    RSA = "rsa"
    DSA = "dsa"
    ECDSA = "ecdsa"
    ED25519 = "ed25519"


class SSHProfileStatus(str, Enum):
    """SSH profile connection status."""
    NEVER_CONNECTED = "never_connected"
    CONNECTED = "connected"
    CONNECTION_FAILED = "connection_failed"
    CONNECTION_TIMEOUT = "connection_timeout"


# SSH Profile Schemas
class SSHProfileBase(BaseModel):
    """Base schema for SSH profile."""
    name: str = Field(..., min_length=1, max_length=100, description="Profile name")
    host: str = Field(..., min_length=1, max_length=255, description="SSH server hostname or IP")
    port: int = Field(default=22, ge=1, le=65535, description="SSH server port")
    username: str = Field(..., min_length=1, max_length=100, description="SSH username")
    description: Optional[str] = Field(None, max_length=500, description="Profile description")
    
    # Connection settings
    connect_timeout: int = Field(default=30, ge=5, le=300, description="Connection timeout in seconds")
    keepalive_interval: int = Field(default=60, ge=0, le=3600, description="Keep alive interval in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum connection retry attempts")
    
    # Environment settings
    terminal_type: str = Field(default="xterm-256color", max_length=50, description="Terminal type")
    environment: Optional[Dict[str, str]] = Field(default=None, description="Environment variables")
    
    # Advanced settings
    compression: bool = Field(default=False, description="Enable SSH compression")
    forward_agent: bool = Field(default=False, description="Enable SSH agent forwarding")
    forward_x11: bool = Field(default=False, description="Enable X11 forwarding")


class SSHProfileCreate(SSHProfileBase):
    """Schema for creating SSH profile."""
    pass


class SSHProfileUpdate(BaseModel):
    """Schema for updating SSH profile."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Profile name")
    host: Optional[str] = Field(None, min_length=1, max_length=255, description="SSH server hostname or IP")
    port: Optional[int] = Field(None, ge=1, le=65535, description="SSH server port")
    username: Optional[str] = Field(None, min_length=1, max_length=100, description="SSH username")
    description: Optional[str] = Field(None, max_length=500, description="Profile description")
    
    # Connection settings
    connect_timeout: Optional[int] = Field(None, ge=5, le=300, description="Connection timeout in seconds")
    keepalive_interval: Optional[int] = Field(None, ge=0, le=3600, description="Keep alive interval in seconds")
    max_retries: Optional[int] = Field(None, ge=0, le=10, description="Maximum connection retry attempts")
    
    # Environment settings
    terminal_type: Optional[str] = Field(None, max_length=50, description="Terminal type")
    environment: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    
    # Advanced settings
    compression: Optional[bool] = Field(None, description="Enable SSH compression")
    forward_agent: Optional[bool] = Field(None, description="Enable SSH agent forwarding")
    forward_x11: Optional[bool] = Field(None, description="Enable X11 forwarding")
    is_active: Optional[bool] = Field(None, description="Profile active status")


class SSHProfileResponse(SSHProfileBase):
    """Schema for SSH profile response."""
    id: str = Field(..., description="Profile unique identifier")
    user_id: str = Field(..., description="Owner user ID")
    is_active: bool = Field(..., description="Profile active status")
    
    # Statistics
    connection_count: int = Field(..., description="Total connection attempts")
    successful_connections: int = Field(..., description="Successful connections")
    last_connection_at: Optional[datetime] = Field(None, description="Last connection attempt")
    last_successful_connection_at: Optional[datetime] = Field(None, description="Last successful connection")
    
    # Status
    last_connection_status: Optional[SSHProfileStatus] = Field(None, description="Last connection status")
    last_error_message: Optional[str] = Field(None, description="Last error message")
    
    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last used timestamp")

    model_config = ConfigDict(from_attributes=True)


class SSHProfileListResponse(BaseModel):
    """Schema for SSH profile list response."""
    profiles: List[SSHProfileResponse]
    total: int
    offset: int
    limit: int


# SSH Key Schemas
class SSHKeyBase(BaseModel):
    """Base schema for SSH key."""
    name: str = Field(..., min_length=1, max_length=100, description="Key name")
    key_type: SSHKeyType = Field(..., description="SSH key type")
    comment: Optional[str] = Field(None, max_length=200, description="Key comment")
    passphrase_protected: bool = Field(default=False, description="Whether key is passphrase protected")


class SSHKeyCreate(SSHKeyBase):
    """Schema for creating SSH key."""
    private_key: str = Field(..., min_length=1, description="Private key content (will be encrypted)")
    public_key: str = Field(..., min_length=1, description="Public key content")
    passphrase: Optional[str] = Field(None, description="Key passphrase for encryption")

    @validator('private_key')
    def validate_private_key(cls, v):
        """Validate private key format."""
        if not v.startswith(('-----BEGIN ', 'ssh-')):
            raise ValueError('Invalid private key format')
        return v

    @validator('public_key')
    def validate_public_key(cls, v):
        """Validate public key format."""
        if not v.startswith(('ssh-', 'ecdsa-', 'ssh-ed25519')):
            raise ValueError('Invalid public key format')
        return v


class SSHKeyUpdate(BaseModel):
    """Schema for updating SSH key."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Key name")
    comment: Optional[str] = Field(None, max_length=200, description="Key comment")
    is_active: Optional[bool] = Field(None, description="Key active status")


class SSHKeyResponse(SSHKeyBase):
    """Schema for SSH key response (excludes private key)."""
    id: str = Field(..., description="Key unique identifier")
    user_id: str = Field(..., description="Owner user ID")
    fingerprint: str = Field(..., description="Key fingerprint")
    public_key: str = Field(..., description="Public key content")
    is_active: bool = Field(..., description="Key active status")
    
    # Statistics
    usage_count: int = Field(..., description="Usage count")
    last_used_at: Optional[datetime] = Field(None, description="Last used timestamp")
    
    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class SSHKeyListResponse(BaseModel):
    """Schema for SSH key list response."""
    keys: List[SSHKeyResponse]
    total: int
    offset: int
    limit: int


# Connection Testing Schemas
class SSHConnectionTestRequest(BaseModel):
    """Schema for SSH connection test request."""
    profile_id: Optional[str] = Field(None, description="Existing profile ID to test")
    
    # Temporary connection details (if not using existing profile)
    host: Optional[str] = Field(None, min_length=1, max_length=255, description="SSH server hostname or IP")
    port: Optional[int] = Field(None, ge=1, le=65535, description="SSH server port")
    username: Optional[str] = Field(None, min_length=1, max_length=100, description="SSH username")
    
    # Authentication method
    auth_method: str = Field(default="key", description="Authentication method: 'key' or 'password'")
    ssh_key_id: Optional[str] = Field(None, description="SSH key ID for key-based auth")
    password: Optional[str] = Field(None, description="Password for password-based auth")
    
    # Connection settings
    connect_timeout: int = Field(default=30, ge=5, le=60, description="Connection timeout in seconds")

    @validator('profile_id', 'host')
    def validate_profile_or_host(cls, v, values):
        """Ensure either profile_id or host is provided."""
        if 'profile_id' in values and not values.get('profile_id') and not v:
            raise ValueError('Either profile_id or host must be provided')
        return v


class SSHConnectionTestResponse(BaseModel):
    """Schema for SSH connection test response."""
    success: bool = Field(..., description="Connection test result")
    message: str = Field(..., description="Test result message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional test details")
    duration_ms: int = Field(..., description="Test duration in milliseconds")
    server_info: Optional[Dict[str, str]] = Field(None, description="SSH server information")
    timestamp: datetime = Field(..., description="Test timestamp")


# Profile-Key Association Schemas
class ProfileKeyAssociation(BaseModel):
    """Schema for associating SSH key with profile."""
    key_id: str = Field(..., description="SSH key ID")
    is_primary: bool = Field(default=False, description="Whether this is the primary key for the profile")


class ProfileKeyAssociationResponse(BaseModel):
    """Schema for profile-key association response."""
    profile_id: str = Field(..., description="Profile ID")
    key_id: str = Field(..., description="SSH key ID")
    is_primary: bool = Field(..., description="Whether this is the primary key")
    created_at: datetime = Field(..., description="Association creation timestamp")
    
    # Include key details
    key: SSHKeyResponse = Field(..., description="Associated SSH key details")

    model_config = ConfigDict(from_attributes=True)


# Search and Filter Schemas
class SSHProfileSearchRequest(BaseModel):
    """Schema for SSH profile search request."""
    search_term: Optional[str] = Field(None, min_length=1, max_length=100, description="Search term")
    host_filter: Optional[str] = Field(None, description="Filter by host")
    status_filter: Optional[SSHProfileStatus] = Field(None, description="Filter by status")
    active_only: bool = Field(default=True, description="Show only active profiles")
    sort_by: str = Field(default="last_used", description="Sort field: name, host, last_used, created_at")
    sort_order: str = Field(default="desc", description="Sort order: asc, desc")
    offset: int = Field(default=0, ge=0, description="Pagination offset")
    limit: int = Field(default=50, ge=1, le=100, description="Pagination limit")


class SSHKeySearchRequest(BaseModel):
    """Schema for SSH key search request."""
    search_term: Optional[str] = Field(None, min_length=1, max_length=100, description="Search term")
    key_type_filter: Optional[SSHKeyType] = Field(None, description="Filter by key type")
    active_only: bool = Field(default=True, description="Show only active keys")
    sort_by: str = Field(default="last_used", description="Sort field: name, created_at, last_used")
    sort_order: str = Field(default="desc", description="Sort order: asc, desc")
    offset: int = Field(default=0, ge=0, description="Pagination offset")
    limit: int = Field(default=50, ge=1, le=100, description="Pagination limit")


# Analytics and Statistics Schemas
class SSHProfileStats(BaseModel):
    """Schema for SSH profile statistics."""
    total_profiles: int = Field(..., description="Total number of profiles")
    active_profiles: int = Field(..., description="Number of active profiles")
    profiles_by_status: Dict[str, int] = Field(..., description="Profile count by status")
    most_used_profiles: List[SSHProfileResponse] = Field(..., description="Most frequently used profiles")
    recent_connections: List[Dict[str, Any]] = Field(..., description="Recent connection attempts")


class SSHKeyStats(BaseModel):
    """Schema for SSH key statistics."""
    total_keys: int = Field(..., description="Total number of keys")
    active_keys: int = Field(..., description="Number of active keys")
    keys_by_type: Dict[str, int] = Field(..., description="Key count by type")
    most_used_keys: List[SSHKeyResponse] = Field(..., description="Most frequently used keys")


# Error Schemas
class SSHErrorResponse(BaseModel):
    """Schema for SSH-related error responses."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(..., description="Error timestamp")


# Common Response Schemas
class MessageResponse(BaseModel):
    """Schema for simple message responses."""
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class BulkOperationResponse(BaseModel):
    """Schema for bulk operation responses."""
    success_count: int = Field(..., description="Number of successful operations")
    error_count: int = Field(..., description="Number of failed operations")
    errors: Optional[List[Dict[str, str]]] = Field(None, description="Error details for failed operations")
    message: str = Field(..., description="Overall operation message")