from django.conf import settings
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from aura.assessments.api.views import HealthAssessmentViewSet
from aura.assessments.api.views import HealthRiskPredictionViewSet
from aura.users.api.views import LoginView
from aura.users.api.views import UserViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)
router.register("assessments", HealthAssessmentViewSet)
router.register("predictions", HealthRiskPredictionViewSet)

app_name = "api"
urlpatterns = router.urls


urlpatterns.append(
    path("login/", LoginView.as_view(), name="rest_login"),
)
