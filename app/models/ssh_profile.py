"""
SSH Profile and SSH Key models for DevPocket API.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, ForeignKey, Integer, Text, Boolean, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import BaseModel


class SSHProfile(BaseModel):
    """SSH Profile model for storing SSH connection configurations."""
    
    __tablename__ = "ssh_profiles"
    
    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Profile identification
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Connection details
    host: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    port: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=22,
        server_default="22"
    )
    
    username: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    
    # Authentication method
    auth_method: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="key",
        server_default="'key'"
    )  # key, password, agent
    
    # SSH key reference (if using key auth)
    ssh_key_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ssh_keys.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Connection options
    compression: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true"
    )
    
    strict_host_key_checking: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true"
    )
    
    connection_timeout: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=30,
        server_default="30"
    )
    
    # Advanced SSH options (JSON string)
    ssh_options: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )  # JSON string of additional SSH options
    
    # Profile status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true"
    )
    
    # Connection statistics
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True
    )
    
    connection_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0"
    )
    
    successful_connections: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0"
    )
    
    failed_connections: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0"
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="ssh_profiles"
    )
    
    ssh_key: Mapped[Optional["SSHKey"]] = relationship(
        "SSHKey",
        back_populates="profiles"
    )
    
    # Methods
    def record_connection_attempt(self, success: bool) -> None:
        """Record a connection attempt."""
        self.connection_count += 1
        if success:
            self.successful_connections += 1
            self.last_used_at = datetime.now()
        else:
            self.failed_connections += 1
    
    @property
    def success_rate(self) -> float:
        """Calculate connection success rate."""
        if self.connection_count == 0:
            return 0.0
        return (self.successful_connections / self.connection_count) * 100
    
    def to_ssh_config(self) -> str:
        """Generate SSH config format string."""
        config_lines = [
            f"Host {self.name}",
            f"    HostName {self.host}",
            f"    Port {self.port}",
            f"    User {self.username}",
        ]
        
        if self.ssh_key and self.auth_method == "key":
            config_lines.append(f"    IdentityFile {self.ssh_key.file_path}")
        
        config_lines.extend([
            f"    Compression {'yes' if self.compression else 'no'}",
            f"    StrictHostKeyChecking {'yes' if self.strict_host_key_checking else 'no'}",
            f"    ConnectTimeout {self.connection_timeout}",
        ])
        
        return "\n".join(config_lines)
    
    def __repr__(self) -> str:
        return f"<SSHProfile(id={self.id}, name={self.name}, host={self.host}, user_id={self.user_id})>"


class SSHKey(BaseModel):
    """SSH Key model for storing SSH private keys."""
    
    __tablename__ = "ssh_keys"
    
    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Key identification
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Key details
    key_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )  # rsa, ecdsa, ed25519, dsa
    
    key_size: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )  # Key size in bits (for RSA, DSA)
    
    fingerprint: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        unique=True,
        index=True
    )
    
    # Encrypted private key (stored as encrypted binary data)
    encrypted_private_key: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False
    )
    
    # Public key (stored as text)
    public_key: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    
    # Key metadata
    comment: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    has_passphrase: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false"
    )
    
    # File system reference
    file_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )  # Path where the key is stored on disk
    
    # Key status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true"
    )
    
    # Usage tracking
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True
    )
    
    usage_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0"
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="ssh_keys"
    )
    
    profiles: Mapped[List["SSHProfile"]] = relationship(
        "SSHProfile",
        back_populates="ssh_key"
    )
    
    # Methods
    def record_usage(self) -> None:
        """Record key usage."""
        self.usage_count += 1
        self.last_used_at = datetime.now()
    
    def generate_fingerprint(self) -> str:
        """Generate SSH key fingerprint."""
        # This would normally use cryptographic functions
        # For now, return a placeholder that would be generated
        # when the actual key is processed
        import hashlib
        return hashlib.sha256(self.public_key.encode()).hexdigest()[:32]
    
    @property
    def short_fingerprint(self) -> str:
        """Get short version of fingerprint for display."""
        return f"{self.fingerprint[:8]}...{self.fingerprint[-8:]}"
    
    def __repr__(self) -> str:
        return f"<SSHKey(id={self.id}, name={self.name}, type={self.key_type}, user_id={self.user_id})>"