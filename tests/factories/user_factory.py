"""
User and UserSettings factories for testing.
"""

from datetime import datetime, timedelta
import factory
from factory import fuzzy
from faker import Faker

from app.models.user import User, UserRole
from app.auth.security import hash_password

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
    role = UserRole.USER.value
    
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


