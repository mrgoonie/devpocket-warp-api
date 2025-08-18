"""
User and UserSettings factories for testing.
"""

import factory
import factory.fuzzy
import uuid
import time
import random
from faker import Faker

from app.auth.security import hash_password
from app.models.user import User, UserRole, UserSettings

fake = Faker()


def _generate_unique_email():
    """Generate a unique email with timestamp, process ID, and UUID."""
    import os
    unique_id = str(uuid.uuid4())[:8]
    process_id = str(os.getpid())[-4:]  # Process isolation for parallel workers
    timestamp = str(int(time.time_ns()))[-12:]  # Nanosecond precision
    random_suffix = str(random.randint(100000, 999999))
    ultra_unique = f"{unique_id}_{process_id}_{timestamp}_{random_suffix}"
    return f"test_{ultra_unique}@example.com"


def _generate_unique_username():
    """Generate a unique username with timestamp, process ID, and UUID."""
    import os
    unique_id = str(uuid.uuid4())[:8]
    process_id = str(os.getpid())[-4:]  # Process isolation for parallel workers
    timestamp = str(int(time.time_ns()))[-12:]  # Nanosecond precision
    random_suffix = str(random.randint(100000, 999999))
    ultra_unique = f"{unique_id}_{process_id}_{timestamp}_{random_suffix}"
    return f"test_{ultra_unique}"[:30]  # Ensure max 30 chars  # Ensure max 30 chars


class UserFactory(factory.Factory):
    """Factory for User model."""

    class Meta:
        model = User

    # Basic user information - using unique generators to avoid conflicts
    email = factory.LazyFunction(_generate_unique_email)
    username = factory.LazyFunction(_generate_unique_username)
    hashed_password = factory.LazyFunction(lambda: hash_password("TestPassword123!"))
    full_name = factory.LazyAttribute(lambda obj: f"{obj.username.title()} User")
    role = UserRole.USER

    # Account status
    is_active = True
    is_verified = False

    # Subscription information - align with model defaults
    subscription_tier = "free"
    subscription_expires_at = None

    # Optional fields that exist in the database
    verification_token = None
    reset_token = None
    reset_token_expires = None
    openrouter_api_key = None
    
    # Security fields - ensure they have default values
    failed_login_attempts = 0
    locked_until = None
    last_login_at = None
    verified_at = None


class VerifiedUserFactory(UserFactory):
    """Factory for verified User."""

    is_verified = True
    verified_at = factory.Faker('date_time_this_month')


class PremiumUserFactory(VerifiedUserFactory):
    """Factory for premium User."""

    subscription_tier = "premium"
    subscription_expires_at = factory.Faker(
        'date_time_between', start_date='+1d', end_date='+30d'
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
