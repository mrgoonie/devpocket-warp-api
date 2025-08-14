"""
User and UserSettings factories for testing.
"""

from datetime import datetime, timedelta
import factory
from factory import fuzzy
from faker import Faker

from app.models.user import User, UserSettings
from app.auth.security import get_password_hash

fake = Faker()


class UserFactory(factory.Factory):
    """Factory for User model."""
    
    class Meta:
        model = User
    
    # Basic user information
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.Sequence(lambda n: f"user{n}")
    password_hash = factory.LazyFunction(lambda: get_password_hash("TestPassword123!"))
    
    # Account status
    is_active = True
    is_verified = False
    
    # Subscription information
    subscription_tier = fuzzy.FuzzyChoice(["free", "premium", "team"])
    
    # API key validation
    has_api_key = False
    api_key_validated_at = None
    
    # Profile information
    display_name = factory.LazyAttribute(lambda obj: f"{obj.username.title()}")
    bio = factory.LazyFunction(lambda: fake.text(max_nb_chars=200))
    timezone = fuzzy.FuzzyChoice([
        "UTC", "US/Eastern", "US/Central", "US/Mountain", "US/Pacific",
        "Europe/London", "Europe/Berlin", "Asia/Tokyo", "Australia/Sydney"
    ])
    
    # Authentication tracking
    last_login_at = None
    failed_login_attempts = 0
    locked_until = None


class VerifiedUserFactory(UserFactory):
    """Factory for verified User."""
    
    is_verified = True
    verified_at = factory.LazyFunction(datetime.utcnow)
    last_login_at = factory.LazyFunction(lambda: datetime.utcnow() - timedelta(hours=1))


class PremiumUserFactory(VerifiedUserFactory):
    """Factory for premium User."""
    
    subscription_tier = "premium"
    subscription_expires_at = factory.LazyFunction(
        lambda: datetime.utcnow() + timedelta(days=30)
    )
    has_api_key = True
    api_key_validated_at = factory.LazyFunction(datetime.utcnow)


class TeamUserFactory(VerifiedUserFactory):
    """Factory for team User."""
    
    subscription_tier = "team"
    subscription_expires_at = factory.LazyFunction(
        lambda: datetime.utcnow() + timedelta(days=365)
    )
    has_api_key = True
    api_key_validated_at = factory.LazyFunction(datetime.utcnow)


class LockedUserFactory(UserFactory):
    """Factory for locked User."""
    
    failed_login_attempts = 5
    locked_until = factory.LazyFunction(
        lambda: datetime.utcnow() + timedelta(minutes=15)
    )


class UserSettingsFactory(factory.Factory):
    """Factory for UserSettings model."""
    
    class Meta:
        model = UserSettings
    
    # Associated user (will be set by tests)
    user_id = factory.LazyAttribute(lambda obj: str(fake.uuid4()))
    
    # Terminal settings
    terminal_theme = fuzzy.FuzzyChoice(["dark", "light", "high-contrast"])
    terminal_font_size = fuzzy.FuzzyInteger(10, 20)
    terminal_font_family = fuzzy.FuzzyChoice([
        "Fira Code", "Monaco", "Consolas", "Ubuntu Mono", "DejaVu Sans Mono"
    ])
    
    # AI preferences
    preferred_ai_model = fuzzy.FuzzyChoice([
        "claude-3-haiku", "claude-3-sonnet", "claude-3-opus",
        "gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"
    ])
    ai_suggestions_enabled = True
    ai_explanations_enabled = True
    
    # Sync settings
    sync_enabled = True
    sync_commands = True
    sync_ssh_profiles = True
    
    # Custom settings
    custom_settings = factory.LazyFunction(lambda: {
        "notifications": {
            "email": True,
            "push": False
        },
        "shortcuts": {
            "ctrl_c": "interrupt",
            "ctrl_d": "exit"
        },
        "appearance": {
            "animations": True,
            "sounds": False
        }
    })