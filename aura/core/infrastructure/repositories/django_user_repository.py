"""
Django ORM implementation of UserRepository.
Implements user data operations using Django models.
"""

from django.contrib.auth import authenticate
from django.db import transaction

from aura.core.domain.repositories.user_repository import UserRepository
from aura.users.models import User


class DjangoUserRepository(UserRepository):
    """Django ORM implementation of UserRepository."""

    def find_by_id(self, user_id: int) -> User | None:
        """Find a user by ID."""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    def find_by_email(self, email: str) -> User | None:
        """Find a user by email address."""
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            return None

    def find_by_username(self, username: str) -> User | None:
        """Find a user by username."""
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None

    @transaction.atomic
    def create_user(self, email: str, password: str, user_type: str, **kwargs) -> User:
        """Create a new user."""
        user = User.objects.create_user(email=email, password=password, user_type=user_type, **kwargs)
        return user

    def update_user(self, user: User) -> User:
        """Update an existing user."""
        user.save()
        return user

    @transaction.atomic
    def delete_user(self, user_id: int) -> bool:
        """Delete a user by ID."""
        try:
            user = User.objects.get(id=user_id)
            user.delete()
            return True
        except User.DoesNotExist:
            return False

    def authenticate_user(self, email: str, password: str) -> User | None:
        """Authenticate a user with email and password."""
        return authenticate(email=email, password=password)

    def is_email_available(self, email: str) -> bool:
        """Check if email is available for registration."""
        return not User.objects.filter(email=email).exists()

    def find_users_by_type(self, user_type: str) -> list[User]:
        """Find all users of a specific type."""
        return list(User.objects.filter(user_type=user_type))

    def get_active_users(self) -> list[User]:
        """Get all active users."""
        return list(User.objects.filter(is_active=True))
