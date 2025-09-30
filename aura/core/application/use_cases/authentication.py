"""
Use cases for authentication operations.
Contains business logic for user registration, login, and logout.
"""

from dataclasses import dataclass

from knox.models import AuthToken

from aura.core.domain.repositories.user_repository import UserRepository
from aura.users.models import User


@dataclass
class RegisterUserRequest:
    """Request for user registration."""

    email: str
    password: str
    user_type: str
    first_name: str | None = None
    last_name: str | None = None


@dataclass
class RegisterUserResponse:
    """Response for user registration."""

    success: bool
    user: User | None = None
    error_message: str | None = None


@dataclass
class LoginUserRequest:
    """Request for user login."""

    email: str
    password: str


@dataclass
class LoginUserResponse:
    """Response for user login."""

    success: bool
    user: User | None = None
    token: str | None = None
    token_expiry: str | None = None
    error_message: str | None = None


@dataclass
class LogoutUserRequest:
    """Request for user logout."""

    user: User


@dataclass
class LogoutUserResponse:
    """Response for user logout."""

    success: bool
    error_message: str | None = None


class RegisterUserUseCase:
    """Use case for registering a new user."""

    def __init__(self, user_repository: UserRepository):
        self._user_repository = user_repository

    def execute(self, request: RegisterUserRequest) -> RegisterUserResponse:
        """Execute the register user use case."""
        try:
            # Validate input
            self._validate_registration_request(request)

            # Check if email is available
            if not self._user_repository.is_email_available(request.email):
                return RegisterUserResponse(success=False, error_message="Email address is already registered")

            # Create user
            user = self._user_repository.create_user(
                email=request.email,
                password=request.password,
                user_type=request.user_type,
                first_name=request.first_name,
                last_name=request.last_name,
            )

            return RegisterUserResponse(success=True, user=user)

        except ValueError as e:
            return RegisterUserResponse(success=False, error_message=str(e))
        except Exception as e:
            return RegisterUserResponse(success=False, error_message=f"Registration failed: {e!s}")

    def _validate_registration_request(self, request: RegisterUserRequest) -> None:
        """Validate registration request."""
        if not request.email:
            raise ValueError("Email is required")

        if not request.password:
            raise ValueError("Password is required")

        if len(request.password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not request.user_type:
            raise ValueError("User type is required")

        if request.user_type not in ["patient", "therapist"]:
            raise ValueError("Invalid user type")


class LoginUserUseCase:
    """Use case for user authentication."""

    def __init__(self, user_repository: UserRepository):
        self._user_repository = user_repository

    def execute(self, request: LoginUserRequest) -> LoginUserResponse:
        """Execute the login user use case."""
        try:
            # Validate input
            self._validate_login_request(request)

            # Authenticate user
            user = self._user_repository.authenticate_user(email=request.email, password=request.password)

            if not user:
                return LoginUserResponse(success=False, error_message="Invalid email or password")

            if not user.is_active:
                return LoginUserResponse(success=False, error_message="Account is deactivated")

            # Create token
            token_instance, token = AuthToken.objects.create(user)

            return LoginUserResponse(
                success=True, user=user, token=token, token_expiry=token_instance.expiry.isoformat()
            )

        except ValueError as e:
            return LoginUserResponse(success=False, error_message=str(e))
        except Exception as e:
            return LoginUserResponse(success=False, error_message=f"Login failed: {e!s}")

    def _validate_login_request(self, request: LoginUserRequest) -> None:
        """Validate login request."""
        if not request.email:
            raise ValueError("Email is required")

        if not request.password:
            raise ValueError("Password is required")


class LogoutUserUseCase:
    """Use case for user logout."""

    def execute(self, request: LogoutUserRequest) -> LogoutUserResponse:
        """Execute the logout user use case."""
        try:
            # Note: Token deletion is handled at the view level
            # This use case could be extended for additional logout logic
            return LogoutUserResponse(success=True)

        except Exception as e:
            return LogoutUserResponse(success=False, error_message=f"Logout failed: {e!s}")
