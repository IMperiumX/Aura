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
router.register("therapy-sessions", TherapySessionViewSet, basename="therapy-session")
router.register("disorders", DisorderViewSet, basename="disorder")
router.register("chatbot-interactions", ChatbotInteractionViewSet, basename="chatbot-interaction")

app_name = "mentalhealth"

urlpatterns = [
    path("", include(router.urls)),
]
