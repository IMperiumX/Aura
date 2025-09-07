from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from aura.mentalhealth.api.views import ChatbotInteractionViewSet
from aura.mentalhealth.api.views import DisorderViewSet
from aura.mentalhealth.api.views import TherapySessionViewSet
from aura.users.api.views import UserViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

# User module routes
router.register("users", UserViewSet)


# Mental health module routes
router.register("therapy-sessions", TherapySessionViewSet)
router.register("disorders", DisorderViewSet)
router.register("chatbot-interactions", ChatbotInteractionViewSet)


app_name = "api"
urlpatterns = router.urls
