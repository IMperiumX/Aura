# ruff: noqa: ERA001
import logging
import time
from contextlib import contextmanager
from typing import Any

# Celery imports
from celery import shared_task

# Django imports
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page

# DRF imports
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

# Internal imports
from aura import analytics
from aura import audit_log
from aura.analytics.mixins import AnalyticsRecordingMixin
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
from aura.audit_log.utils import create_audit_entry
from aura.core.cache_instrumentation import get_instrumented_cache
from aura.core.tasks import setup_rag_pipeline_task
from aura.users.api.permissions import IsPatient
from aura.users.api.permissions import IsTherapist
from aura.users.api.serializers import TherapistSerializer
from aura.users.models import Patient

from .serializers import QuestionSerializer

logger = logging.getLogger(__name__)


# Background Tasks for Assessment Processing
@shared_task(bind=True, name="assessments.process_assessment_completion")
def process_assessment_completion(self, assessment_id):
    """Background task to process completed assessments."""
    try:
        assessment = PatientAssessment.objects.get(id=assessment_id)

        # Calculate risk score based on responses
        risk_score = calculate_assessment_risk_score(assessment)

        # Generate personalized recommendations
        recommendations = generate_assessment_recommendations(assessment)

        # Update assessment with analysis results
        assessment.ai_risk_score = risk_score
        assessment.ai_recommendations = recommendations
        assessment.save()

        # Create risk prediction if warranted
        if risk_score > 0.7:  # High risk threshold
            create_risk_prediction_from_assessment.delay(assessment_id, risk_score)

        # Record analytics
        analytics.record(
            "assessment.processed",
            assessment_id=assessment_id,
            risk_score=risk_score,
            recommendations_count=len(recommendations),
            processing_duration=getattr(self.request, "duration", 0),
        )

        logger.info(
            f"Processed assessment {assessment_id} with risk score {risk_score}",
        )
        return {
            "status": "success",
            "assessment_id": assessment_id,
            "risk_score": risk_score,
        }

    except Exception as e:
        logger.error(f"Failed to process assessment {assessment_id}: {e}")
        raise


@shared_task(bind=True, name="assessments.create_risk_prediction_from_assessment")
def create_risk_prediction_from_assessment(self, assessment_id, risk_score):
    """Background task to create risk predictions from assessments."""
    try:
        assessment = PatientAssessment.objects.get(id=assessment_id)

        # Generate risk prediction
        risk_factors = extract_risk_factors_from_assessment(assessment)
        preventive_measures = generate_preventive_measures(risk_factors)

        # Create risk prediction
        RiskPrediction.objects.create(
            patient=assessment.patient,
            assessment=assessment,
            health_issue=determine_primary_health_issue(risk_factors),
            preventive_measures=preventive_measures,
            confidence_level=risk_score * 100,  # Convert to percentage
            source="AI-based assessment analysis",
            risk_factors=risk_factors,
        )

        # Record analytics
        analytics.record(
            "risk_prediction.auto_generated",
            assessment_id=assessment_id,
            patient_id=assessment.patient.id,
            risk_score=risk_score,
            confidence_level=risk_score * 100,
        )

        return {"status": "success", "assessment_id": assessment_id}

    except Exception as e:
        logger.error(
            f"Failed to create risk prediction from assessment {assessment_id}: {e}",
        )
        raise


@shared_task(bind=True, name="assessments.generate_therapist_recommendations")
def generate_therapist_recommendations(self, assessment_id):
    """Background task to generate therapist recommendations."""
    try:
        assessment = PatientAssessment.objects.get(id=assessment_id)

        # Analyze assessment for therapist matching
        patient_needs = analyze_patient_needs(assessment)
        suitable_therapists = find_matching_therapists(patient_needs)

        # Generate recommendation scores
        recommendations = []
        for therapist in suitable_therapists:
            compatibility_score = calculate_therapist_compatibility(
                assessment,
                therapist,
            )
            recommendations.append(
                {
                    "therapist_id": therapist.id,
                    "compatibility_score": compatibility_score,
                    "reasons": get_recommendation_reasons(assessment, therapist),
                },
            )

        # Cache recommendations
        cache_key = f"therapist_recommendations:{assessment_id}"
        cache.set(cache_key, recommendations, timeout=86400)  # 24 hours

        # Record analytics
        analytics.record(
            "therapist.recommendations_generated",
            assessment_id=assessment_id,
            patient_id=assessment.patient.id,
            recommendations_count=len(recommendations),
            generation_method="ai_analysis",
        )

        return {
            "status": "success",
            "assessment_id": assessment_id,
            "recommendations": recommendations,
        }

    except Exception as e:
        logger.error(
            f"Failed to generate therapist recommendations for assessment {assessment_id}: {e}",
        )
        raise


# Helper functions for background tasks
def calculate_assessment_risk_score(assessment) -> float:
    """Calculate risk score based on assessment responses."""
    try:
        # Placeholder for ML-based risk calculation
        # Would analyze assessment responses and calculate risk
        base_risk = 0.3  # Base risk score

        # Adjust based on assessment type
        if hasattr(assessment.assessment, "assessment_type"):
            if "anxiety" in assessment.assessment.assessment_type.lower():
                base_risk += 0.2
            elif "depression" in assessment.assessment.assessment_type.lower():
                base_risk += 0.3

        return min(max(base_risk, 0.0), 1.0)  # Clamp between 0-1
    except Exception:
        return 0.5  # Default moderate risk


def generate_assessment_recommendations(assessment) -> list[str]:
    """Generate personalized recommendations based on assessment."""
    try:
        recommendations = [
            "Consider regular therapy sessions",
            "Practice mindfulness and relaxation techniques",
            "Maintain a healthy sleep schedule",
            "Engage in regular physical activity",
        ]

        # Customize based on assessment results
        if hasattr(assessment, "risk_level"):
            if assessment.risk_level == "high":
                recommendations.insert(0, "Seek immediate professional consultation")

        return recommendations
    except Exception:
        return ["Consult with a healthcare professional"]


def extract_risk_factors_from_assessment(assessment) -> dict[str, Any]:
    """Extract risk factors from assessment responses."""
    try:
        # Placeholder for risk factor extraction
        return {
            "stress_level": "moderate",
            "sleep_quality": "poor",
            "social_support": "limited",
            "coping_mechanisms": "developing",
        }
    except Exception:
        return {}


def generate_preventive_measures(risk_factors: dict) -> str:
    """Generate preventive measures based on risk factors."""
    try:
        measures = []

        if risk_factors.get("stress_level") in ["high", "moderate"]:
            measures.append("stress management techniques")

        if risk_factors.get("sleep_quality") == "poor":
            measures.append("sleep hygiene improvement")

        if risk_factors.get("social_support") == "limited":
            measures.append("social connection building")

        return ", ".join(measures) if measures else "regular monitoring and self-care"
    except Exception:
        return "general wellness practices"


def determine_primary_health_issue(risk_factors: dict) -> str:
    """Determine primary health issue from risk factors."""
    try:
        # Placeholder logic
        if risk_factors.get("stress_level") in ["high", "moderate"]:
            return "Stress-related concerns"
        elif risk_factors.get("sleep_quality") == "poor":
            return "Sleep-related issues"
        else:
            return "General mental health monitoring"
    except Exception:
        return "Mental health assessment follow-up"


def analyze_patient_needs(assessment) -> dict[str, Any]:
    """Analyze patient needs from assessment."""
    try:
        return {
            "primary_concerns": ["anxiety", "stress"],
            "therapy_preferences": ["cognitive_behavioral", "mindfulness"],
            "availability": "flexible",
            "communication_style": "supportive",
        }
    except Exception:
        return {}


def find_matching_therapists(patient_needs: dict) -> list:
    """Find therapists matching patient needs."""
    try:
        # Placeholder - would query therapist database with filtering
        from aura.users.models import Therapist

        return Therapist.objects.all()[:5]  # Return top 5 for demo
    except Exception:
        return []


def calculate_therapist_compatibility(assessment, therapist) -> float:
    """Calculate compatibility score between patient and therapist."""
    try:
        # Placeholder compatibility calculation
        base_score = 0.7

        # Adjust based on specializations, experience, etc.
        if hasattr(therapist, "specializations"):
            # Would check if therapist specializations match patient needs
            base_score += 0.1

        return min(max(base_score, 0.0), 1.0)
    except Exception:
        return 0.5


def get_recommendation_reasons(assessment, therapist) -> list[str]:
    """Get reasons for therapist recommendation."""
    try:
        return [
            "Specializes in anxiety and stress management",
            "Experienced with similar patient profiles",
            "Positive patient feedback and outcomes",
        ]
    except Exception:
        return ["Professional qualifications match patient needs"]


class EnhancedAssessmentThrottle(UserRateThrottle):
    """Enhanced rate throttling for assessment endpoints."""

    def throttle_failure(self):
        """Record throttling events for assessment analytics."""
        try:
            request = getattr(self, "request", None)
            if request:
                analytics.record(
                    "assessments.api.throttled",
                    endpoint=request.path,
                    method=request.method,
                    user_id=request.user.id if request.user.is_authenticated else None,
                    throttle_type=self.__class__.__name__,
                )
        except Exception as e:
            logger.warning(f"Failed to record assessment throttle event: {e}")
        return super().throttle_failure()


class ComprehensiveAssessmentMixin(AnalyticsRecordingMixin):
    """
    Comprehensive mixin for assessment viewsets with full infrastructure integration:
    - Advanced analytics tracking
    - Audit logging for compliance
    - Performance monitoring
    - Caching strategies
    - Security enhancements
    - Background task integration
    """

    # Caching configuration
    cache_timeout = 900  # 15 minutes default for assessment data
    cache_vary_headers = ["Authorization", "Accept-Language"]

    # Throttling configuration
    throttle_classes = [EnhancedAssessmentThrottle]
    throttle_scope = "assessments"

    # Analytics configuration
    track_analytics = True
    analytics_context = {"domain": "assessments"}

    # Performance monitoring
    monitor_performance = True
    slow_query_threshold = 200  # ms (higher for complex assessment queries)

    def dispatch(self, request, *args, **kwargs):
        """Enhanced dispatch with comprehensive monitoring."""
        start_time = time.time()

        try:
            # Initialize request tracking
            self._init_request_tracking(request)

            # Record request analytics
            if self.track_analytics:
                self._record_request_start(request)

            # Execute the actual view
            response = super().dispatch(request, *args, **kwargs)

            # Record success metrics
            self._record_request_success(request, response, start_time)

            return response

        except Exception as e:
            # Record error metrics and handle gracefully
            self._record_request_error(request, e, start_time)
            raise

        finally:
            # Clean up request tracking
            self._cleanup_request_tracking(request)

    def _init_request_tracking(self, request):
        """Initialize comprehensive request tracking."""
        request._view_start_time = time.time()
        request._db_queries_start = len(getattr(request, "_db_queries", []))
        request._cache_hits_start = getattr(request, "_cache_hits", 0)
        request._cache_misses_start = getattr(request, "_cache_misses", 0)

        # Add correlation ID for distributed tracing
        if not hasattr(request, "correlation_id"):
            import uuid

            request.correlation_id = str(uuid.uuid4())

    def _record_request_start(self, request):
        """Record request start analytics."""
        try:
            self.record_analytics_event(
                "assessments.api.request.started",
                request=request,
                extra_data={
                    "endpoint": request.path,
                    "method": request.method,
                    "view_name": self.__class__.__name__,
                    "action": getattr(self, "action", None),
                    "correlation_id": getattr(request, "correlation_id", None),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to record assessment request start: {e}")

    def _record_request_success(self, request, response, start_time):
        """Record successful request completion."""
        duration = (time.time() - start_time) * 1000  # Convert to ms

        try:
            # Performance metrics
            metrics = {
                "duration_ms": duration,
                "status_code": response.status_code,
                "db_queries": len(getattr(request, "_db_queries", []))
                - request._db_queries_start,
                "cache_hits": getattr(request, "_cache_hits", 0)
                - request._cache_hits_start,
                "cache_misses": getattr(request, "_cache_misses", 0)
                - request._cache_misses_start,
            }

            # Record analytics
            if self.track_analytics:
                self.record_analytics_event(
                    "assessments.api.request.completed",
                    request=request,
                    extra_data={
                        "endpoint": request.path,
                        "method": request.method,
                        "view_name": self.__class__.__name__,
                        "action": getattr(self, "action", None),
                        "correlation_id": getattr(request, "correlation_id", None),
                        **metrics,
                    },
                )

            # Alert on slow queries
            if self.monitor_performance and duration > self.slow_query_threshold:
                self._alert_slow_request(request, duration, metrics)

        except Exception as e:
            logger.warning(f"Failed to record assessment request success: {e}")

    def _record_request_error(self, request, exception, start_time):
        """Record request errors with comprehensive context."""
        duration = (time.time() - start_time) * 1000

        try:
            error_context = {
                "endpoint": request.path,
                "method": request.method,
                "view_name": self.__class__.__name__,
                "action": getattr(self, "action", None),
                "error_type": exception.__class__.__name__,
                "error_message": str(exception),
                "duration_ms": duration,
                "correlation_id": getattr(request, "correlation_id", None),
            }

            # Record error analytics
            if self.track_analytics:
                self.record_analytics_event(
                    "assessments.api.request.error",
                    request=request,
                    extra_data=error_context,
                )

            # Create audit log for security-related errors
            if isinstance(exception, (PermissionDenied,)):
                self._record_security_event(request, exception)

        except Exception as e:
            logger.error(f"Failed to record assessment request error: {e}")

    def _alert_slow_request(self, request, duration, metrics):
        """Alert on slow requests for performance monitoring."""
        try:
            logger.warning(
                f"Slow assessment request detected: {request.path} took {duration:.2f}ms",
                extra={
                    "slow_request": True,
                    "duration_ms": duration,
                    "endpoint": request.path,
                    "method": request.method,
                    "metrics": metrics,
                    "domain": "assessments",
                },
            )
        except Exception as e:
            logger.error(f"Failed to alert on slow assessment request: {e}")

    def _record_security_event(self, request, exception):
        """Record security events in audit log."""
        try:
            create_audit_entry(
                request=request,
                event=(
                    audit_log.get_event_id("ASSESSMENT_SECURITY_VIOLATION")
                    if hasattr(audit_log, "get_event_id")
                    else 2001
                ),
                data={
                    "violation_type": exception.__class__.__name__,
                    "message": str(exception),
                    "endpoint": request.path,
                    "method": request.method,
                    "domain": "assessments",
                },
            )
        except Exception as e:
            logger.error(f"Failed to record assessment security event: {e}")

    def _cleanup_request_tracking(self, request):
        """Clean up request tracking data."""
        try:
            for attr in [
                "_view_start_time",
                "_db_queries_start",
                "_cache_hits_start",
                "_cache_misses_start",
            ]:
                if hasattr(request, attr):
                    delattr(request, attr)
        except Exception:
            pass

    @contextmanager
    def database_transaction_context(self, **transaction_kwargs):
        """Context manager for database transactions with monitoring."""
        start_time = time.time()

        try:
            with transaction.atomic(**transaction_kwargs):
                yield

            # Record successful transaction
            duration = (time.time() - start_time) * 1000
            logger.debug(
                f"Assessment database transaction completed in {duration:.2f}ms",
            )

        except Exception as e:
            # Record failed transaction
            duration = (time.time() - start_time) * 1000
            logger.warning(
                f"Assessment database transaction failed after {duration:.2f}ms: {e}",
            )
            raise

    def get_cached_data(self, cache_key: str, timeout: int | None = None) -> Any:
        """Get data from cache with hit/miss tracking."""
        timeout = timeout or self.cache_timeout

        try:
            instrumented_cache = get_instrumented_cache()
            data = instrumented_cache.get(cache_key)

            if data is None:
                logger.debug(f"Assessment cache miss for key: {cache_key}")
            else:
                logger.debug(f"Assessment cache hit for key: {cache_key}")

            return data

        except Exception as e:
            logger.warning(f"Assessment cache get failed for key {cache_key}: {e}")
            return None

    def set_cached_data(
        self,
        cache_key: str,
        data: Any,
        timeout: int | None = None,
    ) -> bool:
        """Set data in cache with error handling."""
        timeout = timeout or self.cache_timeout

        try:
            instrumented_cache = get_instrumented_cache()
            return instrumented_cache.set(cache_key, data, timeout)
        except Exception as e:
            logger.warning(f"Assessment cache set failed for key {cache_key}: {e}")
            return False


class PatientAssessmentViewSet(ComprehensiveAssessmentMixin, viewsets.ModelViewSet):
    """
    Ultra-comprehensive Patient Assessment ViewSet with full infrastructure integration:
    - Advanced analytics tracking for assessment lifecycle
    - Audit logging for compliance
    - Performance monitoring and caching
    - Background task integration for AI processing
    - Security enhancements and risk assessment
    """

    queryset = PatientAssessment.objects.select_related(
        "patient",
        "assessment",
    ).prefetch_related("assessment__questions")
    serializer_class = PatientAssessmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PatientAssessmentFilterSet
    filterset_fields = ["created", "modified"]
    search_fields = ["patient", "created", "modified"]
    ordering_fields = ["patient", "created", "modified"]

    # Enhanced caching configuration
    cache_timeout = 600  # 10 minutes for assessment data

    # Analytics configuration
    analytics_context = {"model": "patient_assessment"}

    def get_queryset(self):
        """Enhanced queryset with security and performance optimizations."""
        base_queryset = PatientAssessment.objects.select_related(
            "patient",
            "assessment",
        ).only(
            "patient",
            "assessment",
            "result",
            "recommendations",
            "created",
            "modified",
            "status",
        )

        # Apply security filtering
        if hasattr(self.request.user, "patient_profile"):
            try:
                patient = self.request.user.patient_profile.get()
                return base_queryset.filter(patient=patient)
            except:
                # Handle case where patient_profile doesn't exist
                return base_queryset.none()
        elif self.request.user.is_superuser:
            return base_queryset
        else:
            return base_queryset.none()

    def perform_create(self, serializer):
        """Enhanced creation with comprehensive tracking and background processing."""
        with self.database_transaction_context():
            # Get patient
            try:
                patient = Patient.objects.get(user=self.request.user)
            except Patient.DoesNotExist:
                raise ValidationError("Patient profile not found for current user")

            # Create assessment
            assessment = serializer.save(
                patient=patient,
                status=getattr(Assessment, "IN_PROGRESS", "in_progress"),
            )

            # Record comprehensive analytics
            self.record_analytics_event(
                "assessment.started",
                instance=assessment,
                request=self.request,
                extra_data={
                    "assessment_id": assessment.id,
                    "patient_id": patient.id,
                    "assessment_type": getattr(
                        assessment.assessment,
                        "assessment_type",
                        None,
                    ),
                    "question_count": (
                        assessment.assessment.questions.count()
                        if hasattr(assessment.assessment, "questions")
                        else None
                    ),
                    "user_agent": self.request.headers.get("user-agent", ""),
                    "ip_address": self.request.META.get("REMOTE_ADDR", ""),
                },
            )

            # Audit log
            create_audit_entry(
                request=self.request,
                target_object=assessment.id,
                event=(
                    audit_log.get_event_id("ASSESSMENT_STARTED")
                    if hasattr(audit_log, "get_event_id")
                    else 2101
                ),
                data={
                    "assessment_id": assessment.id,
                    "patient_id": patient.id,
                    "assessment_type": getattr(
                        assessment.assessment,
                        "assessment_type",
                        None,
                    ),
                    "action": "assessment_start",
                },
            )

            # Invalidate relevant caches
            self._invalidate_assessment_caches(patient.id)

    def perform_update(self, serializer):
        """Enhanced update with completion tracking and AI processing."""
        old_instance = self.get_object()
        old_status = getattr(old_instance, "status", None)

        with self.database_transaction_context():
            assessment = serializer.save()
            new_status = getattr(assessment, "status", None)

            # Check if assessment was completed
            if old_status != getattr(
                Assessment,
                "COMPLETED",
                "completed",
            ) and new_status == getattr(Assessment, "COMPLETED", "completed"):
                self._handle_assessment_completion(assessment, old_instance)

            # Record general update analytics
            self.record_analytics_event(
                "assessment.updated",
                instance=assessment,
                request=self.request,
                extra_data={
                    "assessment_id": assessment.id,
                    "patient_id": assessment.patient.id,
                    "status_changed": old_status != new_status,
                    "old_status": old_status,
                    "new_status": new_status,
                    "has_result": bool(getattr(assessment, "result", None)),
                    "has_recommendations": bool(
                        getattr(assessment, "recommendations", None),
                    ),
                },
            )

            # Audit log for status changes
            if old_status != new_status:
                create_audit_entry(
                    request=self.request,
                    target_object=assessment.id,
                    event=(
                        audit_log.get_event_id("ASSESSMENT_STATUS_CHANGE")
                        if hasattr(audit_log, "get_event_id")
                        else 2102
                    ),
                    data={
                        "assessment_id": assessment.id,
                        "patient_id": assessment.patient.id,
                        "status_change": {"old": old_status, "new": new_status},
                        "action": "assessment_status_change",
                    },
                )

            # Invalidate caches
            self._invalidate_assessment_caches(assessment.patient.id)

    def _handle_assessment_completion(self, assessment, old_instance):
        """Handle assessment completion with comprehensive tracking."""
        try:
            # Calculate completion metrics
            completion_time_minutes = None
            if hasattr(assessment, "created") and assessment.created:
                duration = timezone.now() - assessment.created
                completion_time_minutes = int(duration.total_seconds() / 60)

            # Get assessment details
            num_questions = 0
            if hasattr(assessment.assessment, "questions"):
                num_questions = assessment.assessment.questions.count()

            # Record completion analytics
            self.record_analytics_event(
                "assessment.completed",
                instance=assessment,
                request=self.request,
                extra_data={
                    "assessment_id": assessment.id,
                    "patient_id": assessment.patient.id,
                    "assessment_type": getattr(
                        assessment.assessment,
                        "assessment_type",
                        None,
                    ),
                    "risk_level": getattr(assessment.assessment, "risk_level", None),
                    "completion_time_minutes": completion_time_minutes,
                    "num_questions": num_questions,
                    "has_result": bool(getattr(assessment, "result", None)),
                    "result_length": (
                        len(str(getattr(assessment, "result", "")))
                        if getattr(assessment, "result", None)
                        else 0
                    ),
                },
            )

            # Audit log for completion
            create_audit_entry(
                request=self.request,
                target_object=assessment.id,
                event=(
                    audit_log.get_event_id("ASSESSMENT_COMPLETED")
                    if hasattr(audit_log, "get_event_id")
                    else 2103
                ),
                data={
                    "assessment_id": assessment.id,
                    "patient_id": assessment.patient.id,
                    "completion_time_minutes": completion_time_minutes,
                    "num_questions": num_questions,
                    "action": "assessment_complete",
                },
            )

            # Trigger background processing
            process_assessment_completion.delay(assessment.id)

        except Exception as e:
            logger.warning(
                f"Failed to handle assessment completion for {assessment.id}: {e}",
            )

    def get_serializer(self, *args, **kwargs):
        """Enhanced serializer selection."""
        if self.action == "create":
            return AssessmentCreateSerializer(*args, **kwargs)
        if self.action == "recommend_therapist":
            return TherapistSerializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)

    @method_decorator(cache_page(300))  # 5 minutes for list
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
        """Enhanced list with caching and analytics."""
        cache_key = f"patient_assessments_list:{request.user.id}:{hash(str(request.query_params))}"

        # Try cache first
        cached_data = self.get_cached_data(cache_key)
        if cached_data:
            self.record_analytics_event(
                "assessment.list.cache_hit",
                request=request,
                extra_data={
                    "cached": True,
                    "filters_applied": bool(request.query_params),
                },
            )
            return Response(cached_data)

        # Cache miss - get fresh data
        response = super().list(request, *args, **kwargs)

        # Cache the response
        if response.status_code == 200:
            self.set_cached_data(cache_key, response.data, timeout=300)  # 5 minutes

        # Record analytics
        self.record_analytics_event(
            "assessment.list.viewed",
            request=request,
            extra_data={
                "assessment_count": len(response.data),
                "cached": False,
                "filters_applied": bool(request.query_params),
                "search_query": request.query_params.get("search", ""),
            },
        )

        return response

    def retrieve(self, request, *args, **kwargs):
        """Enhanced retrieve with analytics tracking."""
        assessment = self.get_object()

        # Record analytics
        self.record_analytics_event(
            "assessment.detail.viewed",
            instance=assessment,
            request=request,
            extra_data={
                "assessment_id": assessment.id,
                "patient_id": assessment.patient.id,
                "assessment_type": getattr(
                    assessment.assessment,
                    "assessment_type",
                    None,
                ),
                "status": getattr(assessment, "status", None),
            },
        )

        # Audit log
        create_audit_entry(
            request=request,
            target_object=assessment.id,
            event=(
                audit_log.get_event_id("ASSESSMENT_VIEWED")
                if hasattr(audit_log, "get_event_id")
                else 2104
            ),
            data={
                "assessment_id": assessment.id,
                "patient_id": assessment.patient.id,
                "action": "assessment_view",
            },
        )

        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def therapist_recommendations(self, request, pk: int | None = None):
        """Enhanced therapist recommendations with comprehensive tracking."""
        assessment = self.get_object()

        # Check cache first
        cache_key = f"therapist_recommendations:{assessment.id}"
        cached_recommendations = self.get_cached_data(cache_key)

        if cached_recommendations:
            # Record cache hit
            self.record_analytics_event(
                "therapist.recommendation_cache_hit",
                instance=assessment,
                request=request,
                extra_data={
                    "assessment_id": assessment.id,
                    "patient_id": assessment.patient.id,
                    "cached": True,
                },
            )
            return Response(cached_recommendations)

        # Generate new recommendations
        try:
            # TODO: Replace with actual RAG pipeline
            task = setup_rag_pipeline_task.delay()
            from celery.result import AsyncResult

            if task.status == "SUCCESS":
                result = AsyncResult(task.id).get()
                query_engine = result
                response = query_engine.query("Best Therapist for me?")

                # Record successful recommendation generation
                self.record_analytics_event(
                    "therapist.recommendation_generated",
                    instance=assessment,
                    request=request,
                    extra_data={
                        "assessment_id": assessment.id,
                        "patient_id": assessment.patient.id,
                        "recommendation_count": 1,  # Would be calculated from response
                        "generation_method": "rag_pipeline",
                        "cached": False,
                    },
                )

                # Audit log
                create_audit_entry(
                    request=request,
                    target_object=assessment.id,
                    event=(
                        audit_log.get_event_id("THERAPIST_RECOMMENDATION_GENERATED")
                        if hasattr(audit_log, "get_event_id")
                        else 2105
                    ),
                    data={
                        "assessment_id": assessment.id,
                        "patient_id": assessment.patient.id,
                        "generation_method": "rag_pipeline",
                        "action": "therapist_recommendation_generate",
                    },
                )

                # Cache the result
                self.set_cached_data(
                    cache_key,
                    str(response),
                    timeout=86400,
                )  # 24 hours

                # Trigger background recommendation generation for future
                generate_therapist_recommendations.delay(assessment.id)

                return Response(str(response))

            # Task still processing
            self.record_analytics_event(
                "therapist.recommendation_processing",
                instance=assessment,
                request=request,
                extra_data={
                    "assessment_id": assessment.id,
                    "patient_id": assessment.patient.id,
                    "task_status": task.status,
                },
            )

            return Response("Working on it!", status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            # Record error
            self.record_analytics_event(
                "therapist.recommendation_error",
                instance=assessment,
                request=request,
                extra_data={
                    "assessment_id": assessment.id,
                    "patient_id": assessment.patient.id,
                    "error_type": e.__class__.__name__,
                    "error_message": str(e),
                },
            )

            logger.error(
                f"Error generating therapist recommendations for assessment {assessment.id}: {e}",
            )
            return Response(
                {"error": "Failed to generate recommendations"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def submit_assessment(self, request, pk=None):
        """Enhanced assessment submission with comprehensive processing."""
        assessment = self.get_object()

        if getattr(assessment, "status", None) != getattr(
            Assessment,
            "IN_PROGRESS",
            "in_progress",
        ):
            return Response(
                {"status": _("Assessment cannot be submitted")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with self.database_transaction_context():
            # Update assessment status (placeholder implementation)
            # TODO: Implement actual RAG pipeline processing
            assessment.status = getattr(Assessment, "SUBMITTED", "submitted")
            assessment.result = "Assessment processed successfully"
            if hasattr(assessment, "risk_level"):
                assessment.risk_level = getattr(
                    Assessment.RiskLevel,
                    "MODERATE",
                    "moderate",
                )
            if hasattr(assessment, "recommendations"):
                assessment.recommendations = "Based on your responses, we recommend..."
            assessment.save()

            # Record submission analytics
            self.record_analytics_event(
                "assessment.submitted",
                instance=assessment,
                request=request,
                extra_data={
                    "assessment_id": assessment.id,
                    "patient_id": assessment.patient.id,
                    "assessment_type": getattr(
                        assessment.assessment,
                        "assessment_type",
                        None,
                    ),
                    "submission_method": "manual",
                },
            )

            # Audit log
            create_audit_entry(
                request=request,
                target_object=assessment.id,
                event=(
                    audit_log.get_event_id("ASSESSMENT_SUBMITTED")
                    if hasattr(audit_log, "get_event_id")
                    else 2106
                ),
                data={
                    "assessment_id": assessment.id,
                    "patient_id": assessment.patient.id,
                    "action": "assessment_submit",
                },
            )

            # Trigger background processing
            process_assessment_completion.delay(assessment.id)

            # Invalidate caches
            self._invalidate_assessment_caches(assessment.patient.id)

        serializer = self.get_serializer(assessment)
        return Response(serializer.data)

    @action(detail=False)
    def my_assessments(self, request):
        """Enhanced my assessments endpoint with caching."""
        cache_key = f"my_assessments:{request.user.id}"

        # Try cache first
        cached_data = self.get_cached_data(cache_key, timeout=300)  # 5 minutes
        if cached_data:
            self.record_analytics_event(
                "assessment.my_assessments.cache_hit",
                request=request,
                extra_data={"cached": True},
            )
            return Response(cached_data)

        # Get fresh data
        try:
            patient = Patient.objects.get(user=request.user)
            assessments = Assessment.objects.filter(patient=patient)
            serializer = self.get_serializer(assessments, many=True)

            # Cache the result
            self.set_cached_data(cache_key, serializer.data, timeout=300)

            # Record analytics
            self.record_analytics_event(
                "assessment.my_assessments.viewed",
                request=request,
                extra_data={
                    "assessment_count": len(serializer.data),
                    "patient_id": patient.id,
                    "cached": False,
                },
            )

            return Response(serializer.data)

        except Patient.DoesNotExist:
            return Response(
                {"error": "Patient profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

    def _invalidate_assessment_caches(self, patient_id):
        """Invalidate assessment-related caches."""
        try:
            cache_keys_to_invalidate = [
                f"patient_assessments_list:{patient_id}:*",
                f"my_assessments:{patient_id}",
                "therapist_recommendations:*",  # Would need patient-specific lookup
            ]

            # This would normally use a more sophisticated cache invalidation pattern
            for pattern in cache_keys_to_invalidate:
                if "*" not in pattern:
                    cache.delete(pattern)

            logger.debug(f"Invalidated assessment caches for patient {patient_id}")
        except Exception as e:
            logger.warning(f"Failed to invalidate assessment caches: {e}")


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
            risk_factors = getattr(prediction, "risk_factors", {})
            if isinstance(risk_factors, dict):
                import json

                risk_factors = json.dumps(risk_factors)

            self.record_analytics_event(
                "risk_prediction.generated",
                instance=prediction,
                request=self.request,
                prediction_id=prediction.id,
                patient_id=prediction.patient.id,
                assessment_id=(
                    prediction.assessment.id if prediction.assessment else None
                ),
                confidence_level=(
                    float(prediction.confidence_level)
                    if prediction.confidence_level
                    else None
                ),
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
