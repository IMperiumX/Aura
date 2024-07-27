from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from aura.assessments.models import HealthAssessment
from aura.assessments.models import HealthRiskPrediction
from aura.core.services import RecommendationEngine
from aura.users.api.serializers import TherapistSerializer

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

    def get_serializer(self, *args, **kwargs):
        print(self.action)
        if self.action == "recommend_therapist":
            return TherapistSerializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def recommend_therapist(self, request, pk=None):
        assessment = self.get_object()
        best_match = RecommendationEngine().find_best_match(assessment)

        serializer = self.get_serializer(best_match)

        return Response(serializer.data)


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
