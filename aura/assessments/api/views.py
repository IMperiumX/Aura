# ruff: noqa: ERA001
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
import logging

from aura.analytics import AnalyticsRecordingMixin
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

logger = logging.getLogger(__name__)


class PatientAssessmentViewSet(viewsets.ModelViewSet, AnalyticsRecordingMixin):
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
        """Create patient assessment with analytics tracking."""
        patient = Patient.objects.get(user=self.request.user)
        assessment = serializer.save(patient=patient, status=Assessment.IN_PROGRESS)

        # Record assessment start event
        try:
            self.record_analytics_event(
                "assessment.started",
                instance=assessment,
                request=self.request,
                assessment_id=assessment.id,
                patient_id=patient.id,
                assessment_type=assessment.assessment.assessment_type,
            )
        except Exception as e:
            logger.warning(f"Failed to record assessment start event: {e}")

    def perform_update(self, serializer):
        """Update assessment with completion tracking."""
        old_instance = self.get_object()
        assessment = serializer.save()

        # Check if assessment was completed
        if (old_instance.status != Assessment.COMPLETED and
            assessment.status == Assessment.COMPLETED):

            try:
                # Calculate completion time if we have created timestamp
                completion_time_minutes = None
                if assessment.created:
                    duration = timezone.now() - assessment.created
                    completion_time_minutes = int(duration.total_seconds() / 60)

                # Get number of questions
                num_questions = assessment.assessment.questions.count() if hasattr(assessment.assessment, 'questions') else None

                self.record_analytics_event(
                    "assessment.completed",
                    instance=assessment,
                    request=self.request,
                    assessment_id=assessment.id,
                    patient_id=assessment.patient.id,
                    assessment_type=assessment.assessment.assessment_type,
                    risk_level=assessment.assessment.risk_level,
                    completion_time_minutes=completion_time_minutes,
                    num_questions=num_questions,
                )
            except Exception as e:
                logger.warning(f"Failed to record assessment completion event: {e}")

    def get_serializer(self, *args, **kwargs):
        if self.action == "create":
            return AssessmentCreateSerializer
        if self.action == "recommend_therapist":
            return TherapistSerializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)

    @extend_schema(
        responses={200: PatientAssessmentSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Full Text search assessments",
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
    )
    def therapist_recommendations(self, request, pk: int | None = None):
        """Generate therapist recommendations with analytics tracking."""
        assessment = self.get_object()

        # TODO: get py object from a celery task
        # start here: https://www.reddit.com/r/django/comments/1wx587/how_do_i_return_the_result_of_a_celery_task_to/
        task = setup_rag_pipeline_task.delay()
        from celery.result import AsyncResult

        if task.status == "SUCCESS":
            result = AsyncResult(task.id).get()
            query_engine = result
            response = query_engine.query("Best Therapist for me?")

            # Record recommendation generation event
            try:
                self.record_analytics_event(
                    "therapist.recommendation_generated",
                    instance=assessment,
                    request=request,
                    assessment_id=assessment.id,
                    patient_id=assessment.patient.id,
                    recommendation_count=1,  # Could be calculated from response
                    generation_method='rag_pipeline',
                )
            except Exception as e:
                logger.warning(f"Failed to record therapist recommendation event: {e}")

            return Response(response)
            # or store the result in (PatientAssesment) and return the assessment object
            # assessment = ...
            # assessment.recommendations = response
            # serializer = self.get_serializer(self.get_object())
            # return Response(serializer.data)

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


class RiskPredictionViewSet(viewsets.ModelViewSet, AnalyticsRecordingMixin):
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
        """Create risk prediction with analytics tracking."""
        prediction = serializer.save(patient=self.request.user.patient_profile)

        try:
            # Get risk factors if available
            risk_factors = getattr(prediction, 'risk_factors', {})
            if isinstance(risk_factors, dict):
                import json
                risk_factors = json.dumps(risk_factors)

            self.record_analytics_event(
                "risk_prediction.generated",
                instance=prediction,
                request=self.request,
                prediction_id=prediction.id,
                patient_id=prediction.patient.id,
                assessment_id=prediction.assessment.id if prediction.assessment else None,
                confidence_level=float(prediction.confidence_level) if prediction.confidence_level else None,
                risk_factors=risk_factors,
            )
        except Exception as e:
            logger.warning(f"Failed to record risk prediction event: {e}")

    def get_queryset(self):
        queryset = super().get_queryset()

        return queryset.filter(
            patient=self.request.user.patient_profile,
        ).select_related("assessment")


class QuestionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = QuestionFilterSet
    filterset_fields = [
        "created",
        "modified",
    ]
    search_fields = [
        "question_text",
        "created",
        "modified",
    ]
    ordering_fields = [
        "created",
        "modified",
    ]
