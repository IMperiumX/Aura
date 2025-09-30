"""
Service layer for authentication operations.
Orchestrates authentication use cases and provides a clean interface for views.
"""

from aura.core.application.use_cases.authentication import LoginUserRequest
from aura.core.application.use_cases.authentication import LoginUserUseCase
from aura.core.application.use_cases.authentication import LogoutUserRequest
from aura.core.application.use_cases.authentication import LogoutUserUseCase
from aura.core.application.use_cases.authentication import RegisterUserRequest
from aura.core.application.use_cases.authentication import RegisterUserUseCase
from aura.core.domain.repositories.user_repository import UserRepository


class AuthenticationService:
    """Service for authentication operations."""

    def __init__(self, user_repository: UserRepository):
        self._user_repository = user_repository
        self._register_use_case = RegisterUserUseCase(user_repository)
        self._login_use_case = LoginUserUseCase(user_repository)
        self._logout_use_case = LogoutUserUseCase()

    def register_user(self, email: str, password: str, user_type: str, **kwargs):
        """Register a new user."""
        request = RegisterUserRequest(
            email=email,
            password=password,
            user_type=user_type,
            first_name=kwargs.get("first_name"),
            last_name=kwargs.get("last_name"),
        )
        return self._register_use_case.execute(request)

    def login_user(self, email: str, password: str):
        """Authenticate a user."""
        request = LoginUserRequest(email=email, password=password)
        return self._login_use_case.execute(request)

    def logout_user(self, user):
        """Logout a user."""
        request = LogoutUserRequest(user=user)
        return self._logout_use_case.execute(request)

    def get_user_profile(self, user):
        """Get user profile information."""
        return {
            "id": str(user.id),
            "email": user.email,
            "user_type": user.user_type,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "date_joined": user.date_joined.isoformat() if user.date_joined else None,
        }
