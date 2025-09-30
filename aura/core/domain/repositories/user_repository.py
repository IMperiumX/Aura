"""
Repository interface for User entity operations.
Defines the contract for user data persistence and retrieval.
"""

from abc import ABC
from abc import abstractmethod

from aura.users.models import User


class UserRepository(ABC):
    """Abstract repository interface for user operations."""

    @abstractmethod
    def find_by_id(self, user_id: int) -> User | None:
        """Find a user by ID."""

    @abstractmethod
    def find_by_email(self, email: str) -> User | None:
        """Find a user by email address."""

    @abstractmethod
    def find_by_username(self, username: str) -> User | None:
        """Find a user by username."""

    @abstractmethod
    def create_user(self, email: str, password: str, user_type: str, **kwargs) -> User:
        """Create a new user."""

    @abstractmethod
    def update_user(self, user: User) -> User:
        """Update an existing user."""

    @abstractmethod
    def delete_user(self, user_id: int) -> bool:
        """Delete a user by ID."""

    @abstractmethod
    def authenticate_user(self, email: str, password: str) -> User | None:
        """Authenticate a user with email and password."""

    @abstractmethod
    def is_email_available(self, email: str) -> bool:
        """Check if email is available for registration."""

    @abstractmethod
    def find_users_by_type(self, user_type: str) -> list[User]:
        """Find all users of a specific type."""

    @abstractmethod
    def get_active_users(self) -> list[User]:
        """Get all active users."""
