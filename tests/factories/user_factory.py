"""
User and UserSettings factories for testing.
"""

import factory
import factory.fuzzy
from faker import Faker

from app.auth.security import hash_password
from app.models.user import User, UserRole, UserSettings

fake = Faker()


class UserFactory(factory.Factory):
    """Factory for User model."""

    class Meta:
        model = User

    # Basic user information
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.Sequence(lambda n: f"user{n}")
    hashed_password = factory.LazyFunction(lambda: hash_password("TestPassword123!"))
    full_name = factory.LazyAttribute(lambda obj: f"{obj.username.title()} User")
    role = UserRole.USER

    # Account status
    is_active = True
    is_verified = False

    # Optional fields that exist in the database
    verification_token = None
    reset_token = None
    reset_token_expires = None
    openrouter_api_key = None


class VerifiedUserFactory(UserFactory):
    """Factory for verified User."""

    is_verified = True
    verified_at = factory.LazyFunction(lambda: fake.date_time_this_month())


class PremiumUserFactory(VerifiedUserFactory):
    """Factory for premium User."""

    subscription_tier = "premium"
    subscription_expires_at = factory.LazyFunction(
        lambda: fake.date_time_between(start_date="+1d", end_date="+30d")
    )


class UserSettingsFactory(factory.Factory):
    """Factory for UserSettings model."""

    class Meta:
        model = UserSettings

    # Terminal settings
    terminal_theme = factory.fuzzy.FuzzyChoice(["dark", "light", "solarized"])
    terminal_font_size = factory.fuzzy.FuzzyInteger(10, 20)
    terminal_font_family = factory.fuzzy.FuzzyChoice(
        ["Fira Code", "Consolas", "Monaco"]
    )

    # AI preferences
    preferred_ai_model = factory.fuzzy.FuzzyChoice(
        ["claude-3-haiku", "claude-3-sonnet", "gpt-3.5-turbo", "gpt-4"]
    )
    ai_suggestions_enabled = True
    ai_explanations_enabled = True

    # Sync settings
    sync_enabled = True
    sync_commands = True
    sync_ssh_profiles = True

    # Custom settings (can be None)
    custom_settings = None
