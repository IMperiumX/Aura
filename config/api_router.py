from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from aura.users.api.views import UserViewSet

from .gateway import gateway

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

# User module routes
router.register("users", UserViewSet)

# Try to register mental health module routes if available
try:
    from aura.mentalhealth.api.views import ChatbotInteractionViewSet
    from aura.mentalhealth.api.views import DisorderViewSet
    from aura.mentalhealth.api.views import TherapySessionViewSet

    # Mental health module routes
    router.register("mental-health/therapy-sessions", TherapySessionViewSet)
    router.register("mental-health/disorders", DisorderViewSet)
    router.register("mental-health/chatbot-interactions", ChatbotInteractionViewSet)
except ImportError:
    # Mental health module not available yet
    pass

# Initialize API gateway with router and modules
gateway.router = router
gateway.initialize_modules()

app_name = "api"
urlpatterns = router.urls
