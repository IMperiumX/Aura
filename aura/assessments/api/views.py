from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from aura.assessments.api.serializers import HealthAssessmentSerializer
from aura.assessments.api.serializers import HealthRiskPredictionSerializer
from aura.assessments.api.serializers import HealthAssessmentCreateSerializer
from aura.assessments.models import HealthAssessment
from aura.assessments.models import HealthRiskPrediction
from aura.core.services import RecommendationEngine
from aura.users.api.permissions import IsPatient
from aura.users.api.permissions import IsTherapist
from aura.users.api.serializers import TherapistSerializer

from aura.users.models import Patient


class HealthAssessmentViewSet(viewsets.ModelViewSet):
    queryset = HealthAssessment.objects.all()
    serializer_class = HealthAssessmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]

    filterset_fields = [
        "patient",
        "status",
        "assessment_type",
        "created",
        "modified",
    ]
    search_fields = [
        "patient",
        "status",
        "assessment_type",
        "created",
        "modified",
    ]
    ordering_fields = [
        "patient",
        "status",
        "assessment_type",
        "created",
        "modified",
    ]

    def get_queryset(self):
        return self.queryset.filter(patient=self.request.user.patient_profile)

    def perform_create(self, serializer):
        patient = Patient.objects.get(user=self.request.user)
        serializer.save(patient=patient, status=HealthAssessment.IN_PROGRESS)

    def get_serializer(self, *args, **kwargs):
        if self.action == "create":
            return HealthAssessmentCreateSerializer
        if self.action == "recommend_therapist":
            return TherapistSerializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
    )
    def therapist_recommendations(self, request, pk=None):
        assessment = self.get_object()
        # TODO: Move to assessment as instance method, assessment.get_therapist_recommendations()
        best_match = RecommendationEngine().find_best_match(assessment)

        serializer = self.get_serializer(best_match)

        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def submit_assessment(self, request, pk=None):
        assessment = self.get_object()
        if assessment.status != HealthAssessment.IN_PROGRESS:
            return Response(
                {"status": _("Assessment cannot be submitted")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # XXX: we'll just change the status and add a mock result
        # TODO: use RAG pipeline to process the assessment
        # assessment.status = HealthAssessment.SUBMITTED
        # assessment.result = "Assessment processed successfully"
        # assessment.risk_level = HealthAssessment.RiskLevel.MODERATE
        # assessment.recommendations = "Based on your responses, we recommend..."
        # assessment.save()

        # # Create a mock health risk prediction
        # HealthRiskPrediction.objects.create(
        #     health_issue="Potential cardiovascular issues",
        #     preventive_measures="Regular exercise and balanced diet",
        #     confidence_level=75.5,
        #     source="AI-based prediction",
        #     assessment=assessment,
        #     patient=assessment.patient,
        # )

        serializer = self.get_serializer(assessment)
        return Response(serializer.data)

    @action(detail=False)
    def my_assessments(self, request):
        patient = Patient.objects.get(user=request.user)
        assessments = HealthAssessment.objects.filter(patient=patient)
        serializer = self.get_serializer(assessments, many=True)
        return Response(serializer.data)


class HealthRiskPredictionViewSet(viewsets.ModelViewSet):
    queryset = HealthRiskPrediction.objects.all()
    serializer_class = HealthRiskPredictionSerializer
    permission_classes = [IsAuthenticated, IsPatient | IsTherapist]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "patient",
        "created",
        "modified",
    ]
    search_fields = [
        "patient",
        "created",
        "modified",
    ]
    ordering_fields = [
        "confidence_level",
    ]

    def perform_create(self, serializer):
        serializer.save(patient=self.request.user.patient_profile)

    def get_queryset(self):
        queryset = super().get_queryset()

        return queryset.filter(
            patient=self.request.user.patient_profile,
        ).select_related("assessment")
