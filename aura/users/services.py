"""
User module services for inter-module communication.
"""

from typing import Any

from django.contrib.auth import get_user_model

User = get_user_model()


class UserService:
    """Service for user-related operations."""

    def get_user_by_id(self, user_id: int) -> User | None:
        """Get user by ID."""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    def get_user_profile(self, user_id: int) -> dict[str, Any] | None:
        """Get user profile data."""
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "date_joined": user.date_joined.isoformat() if user.date_joined else None,
        }

    def update_user_profile(self, user_id: int, data: dict[str, Any]) -> bool:
        """Update user profile."""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        for field, value in data.items():
            if hasattr(user, field):
                setattr(user, field, value)

        user.save()
        return True

    def is_user_therapist(self, user_id: int) -> bool:
        """Check if user is a therapist."""
        user = self.get_user_by_id(user_id)
        return user and hasattr(user, "therapist")

    def is_user_patient(self, user_id: int) -> bool:
        """Check if user is a patient."""
        user = self.get_user_by_id(user_id)
        return user and hasattr(user, "patient")


class AuthenticationService:
    """Service for authentication-related operations."""

    def authenticate_user(self, email: str, password: str) -> User | None:
        """Authenticate user with email and password."""
        from django.contrib.auth import authenticate

        return authenticate(email=email, password=password)

    def is_user_authenticated(self, user: User) -> bool:
        """Check if user is authenticated."""
        return user and user.is_authenticated

    def get_user_permissions(self, user: User) -> list:
        """Get user permissions."""
        if not user or not user.is_authenticated:
            return []

        permissions = list(user.user_permissions.values_list("codename", flat=True))

        # Add group permissions
        for group in user.groups.all():
            permissions.extend(
                group.permissions.values_list("codename", flat=True),
            )

        return permissions


def register_services(service_registry):
    """Register user services with the service registry."""

    service_registry.register_service(
        module_name="users",
        service_name="UserService",
        service_class=UserService,
    )

    service_registry.register_service(
        module_name="users",
        service_name="AuthenticationService",
        service_class=AuthenticationService,
    )


def subscribe_to_events(event_bus, module_name):
    """Subscribe to inter-module events."""

    def handle_therapy_session_scheduled(data):
        """Handle therapy session scheduled events."""
        patient_id = data.get("patient_id")
        therapist_id = data.get("therapist_id")
        print(
            f"Users module handling therapy session scheduled for patient {patient_id} and therapist {therapist_id}",
        )
        # Could send notifications, update user activity, etc.

    def handle_payment_completed(data):
        """Handle payment completion events."""
        user_id = data.get("user_id")
        print(f"Users module handling payment completion for user {user_id}")
        # Could update user subscription status, etc.

    # Subscribe to events
    event_bus.subscribe("therapy_session.scheduled", handle_therapy_session_scheduled, module_name)
    event_bus.subscribe("payment.completed", handle_payment_completed, module_name)
