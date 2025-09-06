"""
URL routing for mental health API endpoints.
Clean architecture presentation layer.
"""

from django.urls import include
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ChatbotInteractionViewSet
from .views import DisorderViewSet
from .views import TherapySessionViewSet

router = DefaultRouter()
router.register(r"therapy-sessions", TherapySessionViewSet, basename="therapy-session")
router.register(r"disorders", DisorderViewSet, basename="disorder")
router.register(r"chatbot-interactions", ChatbotInteractionViewSet, basename="chatbot-interaction")

app_name = "mentalhealth"

urlpatterns = [
    path("", include(router.urls)),
]


def register_routes(gateway_router: DefaultRouter, prefix="mental-health"):
    """Register routes with the API gateway."""
    for pattern in router.urls:
        gateway_router.register(
            f"{prefix}/{pattern.pattern}",
            pattern.callback,
            basename=pattern.name,
        )
