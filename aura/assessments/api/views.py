# ruff: noqa: ERA001
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from aura.assessments.api.filters import PatientAssessmentFilterSet
from aura.assessments.api.filters import QuestionFilterSet
from aura.assessments.api.filters import RiskPredictionFilterSet
from aura.assessments.api.serializers import Assessment
from aura.assessments.api.serializers import AssessmentCreateSerializer
from aura.assessments.api.serializers import PatientAssessmentSerializer
from aura.assessments.api.serializers import RiskPredictionSerializer
from aura.assessments.models import PatientAssessment
from aura.assessments.models import Question
from aura.assessments.models import RiskPrediction
from aura.core.tasks import setup_rag_pipeline_task
from aura.users.api.permissions import IsPatient
from aura.users.api.permissions import IsTherapist
from aura.users.api.serializers import TherapistSerializer
from aura.users.models import Patient

from .serializers import QuestionSerializer


class PatientAssessmentViewSet(viewsets.ModelViewSet):
    queryset = PatientAssessment.objects.none()
    serializer_class = PatientAssessmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PatientAssessmentFilterSet
    filterset_fields = [
        "created",
        "modified",
    ]
    search_fields = [
        "patient",
        "created",
        "modified",
    ]
    ordering_fields = [
        "patient",
        "created",
        "modified",
    ]

    def get_queryset(self):
        return (
            PatientAssessment.objects.select_related("patient", "assessment")
            .only("patient", "assessment", "result", "recommendations")
            .filter(patient=self.request.user.patient_profile.get())
        )

    def perform_create(self, serializer):
        patient = Patient.objects.get(user=self.request.user)
        serializer.save(patient=patient, status=Assessment.IN_PROGRESS)

    def get_serializer(self, *args, **kwargs):
        if self.action == "create":
            return AssessmentCreateSerializer
        if self.action == "recommend_therapist":
            return TherapistSerializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
    )
    def therapist_recommendations(self, request, pk: int | None = None):
        # TODO: get py object from a celery task
        # start here: https://www.reddit.com/r/django/comments/1wx587/how_do_i_return_the_result_of_a_celery_task_to/
        task = setup_rag_pipeline_task.delay()
        from celery.result import AsyncResult

        if task.status == "SUCCESS":
            result = AsyncResult(task.id).get()
            query_engine = result
            response = query_engine.query("Best Therapist for me?")
            return Response(response)
            # or store the result in (PatientAssesment) and return the assessment object
            assessment = ...
            assessment.recommendations = response
            serializer = self.get_serializer(self.get_object())
            return Response(serializer.data)
        return Response("Working on it!", status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"])
    def submit_assessment(self, request, pk=None):
        assessment = self.get_object()
        if assessment.status != Assessment.IN_PROGRESS:
            return Response(
                {"status": _("Assessment cannot be submitted")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # XXX: we'll just change the status and add a mock result
        # TODO: use RAG pipeline to process the assessment
        # assessment.status = Assessment.SUBMITTED
        # assessment.result = "Assessment processed successfully"
        # assessment.risk_level = Assessment.RiskLevel.MODERATE
        # assessment.recommendations = "Based on your responses, we recommend..."
        # assessment.save()

        # # Create a mock health risk prediction
        # RiskPrediction.objects.create(
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
        assessments = Assessment.objects.filter(patient=patient)
        serializer = self.get_serializer(assessments, many=True)
        return Response(serializer.data)


class RiskPredictionViewSet(viewsets.ModelViewSet):
    queryset = RiskPrediction.objects.all()
    serializer_class = RiskPredictionSerializer
    permission_classes = [IsAuthenticated, IsPatient | IsTherapist]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RiskPredictionFilterSet
    filterset_fields = [
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


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = QuestionFilterSet
