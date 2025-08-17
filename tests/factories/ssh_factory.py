"""
SSH Profile and SSH Key factories for testing.
"""

import json
from datetime import UTC, datetime, timedelta

import factory
from factory import fuzzy
from faker import Faker

from app.models.ssh_profile import SSHKey, SSHProfile

fake = Faker()


class SSHProfileFactory(factory.Factory):
    """Factory for SSHProfile model."""

    class Meta:
        model = SSHProfile

    # Foreign key (will be set by tests)
    user_id = factory.LazyAttribute(lambda obj: str(fake.uuid4()))

    # Profile identification
    name = factory.Sequence(lambda n: f"server-{n}")
    description = factory.LazyFunction(lambda: fake.text(max_nb_chars=100))

    # Connection details
    host = factory.LazyFunction(fake.domain_name)
    port = fuzzy.FuzzyChoice([22, 2222, 443, 8022])
    username = factory.LazyFunction(fake.user_name)

    # Authentication method
    auth_method = fuzzy.FuzzyChoice(["key", "password", "agent"])
    ssh_key_id = None  # Will be set conditionally

    # Connection options
    compression = True
    strict_host_key_checking = True
    connection_timeout = fuzzy.FuzzyInteger(10, 60)

    # Advanced SSH options
    ssh_options = factory.LazyFunction(
        lambda: json.dumps(
            {
                "ServerAliveInterval": 60,
                "ServerAliveCountMax": 3,
                "ForwardAgent": False,
                "ForwardX11": False,
            }
        )
    )

    # Profile status
    is_active = True

    # Connection statistics
    last_used_at = factory.LazyFunction(
        lambda: datetime.now(UTC) - timedelta(days=1)
    )
    connection_count = fuzzy.FuzzyInteger(0, 100)
    successful_connections = factory.LazyAttribute(
        lambda obj: int(obj.connection_count * 0.8)  # 80% success rate
    )
    failed_connections = factory.LazyAttribute(
        lambda obj: obj.connection_count - obj.successful_connections
    )


class ProductionSSHProfileFactory(SSHProfileFactory):
    """Factory for production SSH profile."""

    name = factory.Sequence(lambda n: f"prod-server-{n}")
    port = 22
    strict_host_key_checking = True
    connection_timeout = 30
    compression = False  # Better for production

    ssh_options = factory.LazyFunction(
        lambda: json.dumps(
            {
                "ServerAliveInterval": 30,
                "ServerAliveCountMax": 5,
                "ForwardAgent": False,
                "ForwardX11": False,
                "TCPKeepAlive": True,
            }
        )
    )


class DevelopmentSSHProfileFactory(SSHProfileFactory):
    """Factory for development SSH profile."""

    name = factory.Sequence(lambda n: f"dev-server-{n}")
    host = factory.LazyFunction(lambda: fake.ipv4_private())
    port = fuzzy.FuzzyChoice([22, 2222, 8022])
    strict_host_key_checking = False  # More relaxed for dev

    ssh_options = factory.LazyFunction(
        lambda: json.dumps(
            {
                "ServerAliveInterval": 60,
                "ServerAliveCountMax": 3,
                "ForwardAgent": True,  # Often needed for dev
                "ForwardX11": True,
            }
        )
    )


class SSHKeyFactory(factory.Factory):
    """Factory for SSHKey model."""

    class Meta:
        model = SSHKey

    # Foreign key (will be set by tests)
    user_id = factory.LazyAttribute(lambda obj: str(fake.uuid4()))

    # Key identification
    name = factory.Sequence(lambda n: f"ssh-key-{n}")
    description = factory.LazyFunction(lambda: fake.text(max_nb_chars=100))

    # Key details
    key_type = fuzzy.FuzzyChoice(["rsa", "ecdsa", "ed25519", "dsa"])
    key_size = factory.LazyAttribute(
        lambda obj: {
            "rsa": fuzzy.FuzzyChoice([2048, 3072, 4096]).fuzz(),
            "dsa": 1024,
            "ecdsa": fuzzy.FuzzyChoice([256, 384, 521]).fuzz(),
            "ed25519": None,
        }.get(obj.key_type)
    )

    fingerprint = factory.LazyFunction(lambda: fake.sha256()[:32])

    # Mock encrypted private key (in real scenario this would be properly encrypted)
    encrypted_private_key = factory.LazyFunction(lambda: fake.binary(length=2048))

    # Mock public key
    public_key = factory.LazyAttribute(
        lambda obj: f"ssh-{obj.key_type} {fake.lexify('?' * 64)} {fake.user_name()}@{fake.domain_name()}"
    )

    # Key metadata
    comment = factory.LazyAttribute(
        lambda obj: f"{fake.user_name()}@{fake.domain_name()}"
    )
    has_passphrase = fuzzy.FuzzyChoice([True, False])

    # File system reference
    file_path = factory.LazyAttribute(
        lambda obj: f"/home/{fake.user_name()}/.ssh/id_{obj.key_type}"
    )

    # Key status
    is_active = True

    # Usage tracking
    last_used_at = factory.LazyFunction(
        lambda: datetime.now(UTC) - timedelta(hours=6)
    )
    usage_count = fuzzy.FuzzyInteger(0, 50)


class RSAKeyFactory(SSHKeyFactory):
    """Factory for RSA SSH key."""

    key_type = "rsa"
    key_size = 4096

    public_key = factory.LazyFunction(
        lambda: f"ssh-rsa {fake.lexify('?' * 64)} {fake.user_name()}@{fake.domain_name()}"
    )


class Ed25519KeyFactory(SSHKeyFactory):
    """Factory for Ed25519 SSH key (modern, secure)."""

    key_type = "ed25519"
    key_size = None

    public_key = factory.LazyFunction(
        lambda: f"ssh-ed25519 {fake.lexify('?' * 43)} {fake.user_name()}@{fake.domain_name()}"
    )


class ECDSAKeyFactory(SSHKeyFactory):
    """Factory for ECDSA SSH key."""

    key_type = "ecdsa"
    key_size = 256

    public_key = factory.LazyFunction(
        lambda: f"ssh-ecdsa {fake.lexify('?' * 64)} {fake.user_name()}@{fake.domain_name()}"
    )


class ProtectedSSHKeyFactory(SSHKeyFactory):
    """Factory for passphrase-protected SSH key."""

    has_passphrase = True
    comment = "Protected key with passphrase"


class FrequentlyUsedSSHKeyFactory(SSHKeyFactory):
    """Factory for frequently used SSH key."""

    last_used_at = factory.LazyFunction(
        lambda: datetime.now(UTC) - timedelta(minutes=30)
    )
    usage_count = fuzzy.FuzzyInteger(50, 200)
