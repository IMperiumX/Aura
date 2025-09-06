"""
Domain services for mental health module.
Export services for inter-module communication.
"""

from aura.mentalhealth.infrastructure.repositories.django_therapy_session_repository import (
    DjangoTherapySessionRepository,
)

from .therapy_session_service import TherapySessionDomainService

__all__ = ["TherapySessionDomainService"]


def register_services(service_registry):
    """Register mental health services with the service registry."""

    # Register therapy session service
    service_registry.register_service(
        module_name="mentalhealth",
        service_name="TherapySessionService",
        service_class=TherapySessionDomainService,
        dependencies=[DjangoTherapySessionRepository()],
    )


def subscribe_to_events(event_bus, module_name):
    """Subscribe to inter-module events."""

    def handle_user_updated(data):
        """Handle user update events."""
        user_id = data.get("user_id")
        # Update any cached user data in mental health contexts
        print(f"Mental health module handling user update for user {user_id}")

    def handle_payment_completed(data):
        """Handle payment completion events."""
        user_id = data.get("user_id")
        session_id = data.get("session_id")
        # Activate therapy session after payment
        print(f"Mental health module handling payment completion for session {session_id}")

    # Subscribe to events
    event_bus.subscribe("user.updated", handle_user_updated, module_name)
    event_bus.subscribe("payment.completed", handle_payment_completed, module_name)
