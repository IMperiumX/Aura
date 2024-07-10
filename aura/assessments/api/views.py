from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions
from rest_framework import viewsets

from aura.assessments.models import HealthAssessment
from aura.assessments.models import HealthRiskPrediction

from .serializers import HealthAssessmentSerializer
from .serializers import HealthRiskPredictionSerializer


class HealthAssessmentViewSet(viewsets.ModelViewSet):
    serializer_class = HealthAssessmentSerializer
    queryset = HealthAssessment.objects.all()
    permission_classes = [permissions.IsAuthenticated]
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

    def perform_create(self, serializer):
        serializer.save(patient=self.request.user.patient_profile)

    def get_queryset(self):
        return self.queryset.filter(patient=self.request.user.patient_profile)


class HealthRiskPredictionViewSet(viewsets.ModelViewSet):
    serializer_class = HealthRiskPredictionSerializer
    queryset = HealthRiskPrediction.objects.all()
    permission_classes = [permissions.IsAuthenticated]
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
        return self.queryset.filter(
            patient=self.request.user.patient_profile,
        ).select_related("assessment")
