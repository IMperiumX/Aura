from django.conf import settings
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from aura.assessments.api.views import PatientAssessmentViewSet
from aura.assessments.api.views import QuestionViewSet
from aura.assessments.api.views import RiskPredictionViewSet
from aura.communication.api.views import AttachmentViewSet
from aura.communication.api.views import MessageViewSet
from aura.communication.api.views import ThreadViewSet
from aura.mentalhealth.api.views import ChatbotInteractionViewSet
from aura.mentalhealth.api.views import DisorderViewSet
from aura.mentalhealth.api.views import TherapyApproachViewSet
from aura.mentalhealth.api.views import TherapySessionViewSet
from aura.users.api.views import PatientViewSet
from aura.users.api.views import PhysicianReferralListCreate
from aura.users.api.views import RegisterView
from aura.users.api.views import UserViewSet

# Patient Flow Board imports
from aura.patientflow.views import (
    ClinicViewSet,
    StatusViewSet,
    AppointmentViewSet,
    PatientFlowEventViewSet,
    NotificationViewSet,
    FlowBoardViewSet,
    AnalyticsViewSet,
)

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register(
    "users",
    UserViewSet,
    basename="users",
)
router.register(
    "patients",
    PatientViewSet,
    basename="patients",
)
router.register(
    "patient-assessments",
    PatientAssessmentViewSet,
    basename="patient-assessments",
)
router.register(
    "predictions",
    RiskPredictionViewSet,
    basename="predictions",
)
router.register(
    "questions",
    QuestionViewSet,
    basename="questions",
)
router.register(
    "sessions",
    TherapySessionViewSet,
    basename="sessions",
)

router.register(
    "approaches",
    TherapyApproachViewSet,
    basename="approaches",
)
router.register(
    "chatbot-interactions",
    ChatbotInteractionViewSet,
    basename="chatbot-interactions",
)
router.register(
    "disorders",
    DisorderViewSet,
    basename="disorders",
)
router.register(
    "threads",
    ThreadViewSet,
    basename="threads",
)
router.register(
    "messages",
    MessageViewSet,
    basename="messages",
)
router.register(
    "attachments",
    AttachmentViewSet,
    basename="attachments",
)

router.register(
    "referrals",
    PhysicianReferralListCreate,
    basename="referrals",
)

# Patient Flow Board endpoints
router.register(
    "patientflow/clinics",
    ClinicViewSet,
    basename="patientflow-clinics",
)
router.register(
    "patientflow/statuses",
    StatusViewSet,
    basename="patientflow-statuses",
)
router.register(
    "patientflow/appointments",
    AppointmentViewSet,
    basename="patientflow-appointments",
)
router.register(
    "patientflow/flow-events",
    PatientFlowEventViewSet,
    basename="patientflow-flow-events",
)
router.register(
    "patientflow/notifications",
    NotificationViewSet,
    basename="patientflow-notifications",
)
router.register(
    "patientflow/flow-board",
    FlowBoardViewSet,
    basename="patientflow-flow-board",
)
router.register(
    "patientflow/analytics",
    AnalyticsViewSet,
    basename="patientflow-analytics",
)


app_name = "api"
urlpatterns = router.urls


urlpatterns += [
    path("registeration/", RegisterView.as_view(), name="rest_register"),
]
