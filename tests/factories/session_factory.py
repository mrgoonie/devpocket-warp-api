"""
Session factory for testing.
"""

from datetime import UTC, datetime, timedelta

import factory
from factory import fuzzy
from faker import Faker

from app.models.session import Session

fake = Faker()


class SessionFactory(factory.Factory):
    """Factory for Session model."""

    class Meta:
        model = Session

    # Foreign key (will be set by tests)
    user_id = factory.LazyAttribute(lambda obj: str(fake.uuid4()))

    # Device information
    device_id = factory.LazyFunction(lambda: str(fake.uuid4()))
    device_type = fuzzy.FuzzyChoice(["ios", "android", "web"])
    device_name = factory.LazyAttribute(
        lambda obj: {
            "ios": fake.random_element(
                ["iPhone 15", "iPhone 14", "iPad Pro", "iPad Air"]
            ),
            "android": fake.random_element(
                ["Samsung Galaxy", "Google Pixel", "OnePlus", "Xiaomi"]
            ),
            "web": fake.random_element(["Chrome", "Firefox", "Safari", "Edge"]),
        }.get(obj.device_type, "Unknown Device")
    )

    # Session metadata
    session_name = factory.LazyFunction(lambda: fake.word().title() + " Session")
    session_type = fuzzy.FuzzyChoice(["terminal", "ssh", "pty"])

    # Connection information
    ip_address = factory.LazyFunction(fake.ipv4)
    user_agent = factory.LazyAttribute(
        lambda obj: {
            "ios": "DevPocket/1.0 (iOS 17.0; iPhone)",
            "android": "DevPocket/1.0 (Android 13; Mobile)",
            "web": fake.user_agent(),
        }.get(obj.device_type, fake.user_agent())
    )

    # Session status
    is_active = True
    last_activity_at = factory.LazyFunction(
        lambda: datetime.now(UTC) - timedelta(minutes=5)
    )
    ended_at = None

    # SSH connection details (conditionally set for SSH sessions)
    ssh_host = factory.Maybe(
        "is_ssh",
        yes_declaration=factory.LazyFunction(fake.domain_name),
        no_declaration=None,
    )
    ssh_port = factory.Maybe(
        "is_ssh",
        yes_declaration=fuzzy.FuzzyInteger(22, 65535),
        no_declaration=None,
    )
    ssh_username = factory.Maybe(
        "is_ssh",
        yes_declaration=factory.LazyFunction(fake.user_name),
        no_declaration=None,
    )

    # Terminal configuration
    terminal_cols = fuzzy.FuzzyInteger(80, 120)
    terminal_rows = fuzzy.FuzzyInteger(24, 50)

    # Trait for SSH sessions
    class Params:
        is_ssh = factory.Trait(
            session_type="ssh",
            ssh_host=factory.LazyFunction(fake.domain_name),
            ssh_port=22,
            ssh_username=factory.LazyFunction(fake.user_name),
        )


class ActiveSessionFactory(SessionFactory):
    """Factory for active Session."""

    is_active = True
    last_activity_at = factory.LazyFunction(datetime.utcnow)
    ended_at = None


class EndedSessionFactory(SessionFactory):
    """Factory for ended Session."""

    is_active = False
    ended_at = factory.LazyFunction(lambda: datetime.now(UTC) - timedelta(hours=1))


class SSHSessionFactory(SessionFactory):
    """Factory for SSH Session."""

    session_type = "ssh"
    ssh_host = factory.LazyFunction(fake.domain_name)
    ssh_port = 22
    ssh_username = factory.LazyFunction(fake.user_name)


class WebSessionFactory(SessionFactory):
    """Factory for web Session."""

    device_type = "web"
    device_name = "Chrome Browser"
    user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


class MobileSessionFactory(SessionFactory):
    """Factory for mobile Session."""

    device_type = fuzzy.FuzzyChoice(["ios", "android"])

    @factory.lazy_attribute
    def user_agent(self):
        if self.device_type == "ios":
            return "DevPocket/1.0 (iOS 17.0; iPhone)"
        else:
            return "DevPocket/1.0 (Android 13; Mobile)"
