from django.conf import settings
from django.urls import path
from rest_framework.routers import DefaultRouter, SimpleRouter

from aura.assessments.api.views import (HealthAssessmentViewSet,
                                        HealthRiskPredictionViewSet)
from aura.mentalhealth.api.views import TherapySessionViewSet
from aura.users.api.views import LoginView, UserViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register(
    "users",
    UserViewSet,
)
router.register(
    "assessments",
    HealthAssessmentViewSet,
    basename="assessments",
)
router.register(
    "predictions",
    HealthRiskPredictionViewSet,
    basename="predictions",
)
router.register(
    "sessions",
    TherapySessionViewSet,
    basename="sessions",
)

app_name = "api"
urlpatterns = router.urls


urlpatterns.append(
    path("login/", LoginView.as_view(), name="rest_login"),
)
