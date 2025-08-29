import logging
import time
from contextlib import contextmanager
from typing import Any

# Celery imports
from celery import shared_task

# Django imports
from django.core.cache import cache
from django.db import models
from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

# DRF imports
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

# Internal imports
from aura import analytics
from aura import audit_log
from aura.analytics.mixins import AnalyticsRecordingMixin
from aura.audit_log.utils import create_audit_entry
from aura.core.cache_instrumentation import get_instrumented_cache
from aura.mentalhealth.api.filters import TherapySessionFilter
from aura.mentalhealth.api.serializers import ChatbotInteractionSerializer
from aura.mentalhealth.api.serializers import DisorderSerializer
from aura.mentalhealth.api.serializers import TherapyApproachSerializer
from aura.mentalhealth.api.serializers import TherapySessionSerializer
from aura.mentalhealth.models import ChatbotInteraction
from aura.mentalhealth.models import Disorder
from aura.mentalhealth.models import TherapyApproach
from aura.mentalhealth.models import TherapySession
from aura.users.api.permissions import ReadOnly

logger = logging.getLogger(__name__)


# Background Tasks for Mental Health Processing
@shared_task(bind=True, name="mentalhealth.process_therapy_session")
def process_therapy_session(self, session_id):
    """Background task to process completed therapy sessions."""
    try:
        session = TherapySession.objects.get(id=session_id)

        # Analyze session notes for insights
        insights = analyze_session_notes(session.notes or "")

        # Calculate session effectiveness score
        effectiveness_score = calculate_session_effectiveness(session)

        # Update session with analysis results
        session.effectiveness_score = effectiveness_score
        session.ai_insights = insights
        session.save()

        # Record analytics
        analytics.record(
            "therapy_session.processed",
            session_id=session_id,
            effectiveness_score=effectiveness_score,
            insights_generated=len(insights),
            processing_duration=getattr(self.request, "duration", 0),
        )

        logger.info(
            f"Processed therapy session {session_id} with effectiveness score {effectiveness_score}",
        )
        return {
            "status": "success",
            "session_id": session_id,
            "effectiveness_score": effectiveness_score,
        }

    except Exception as e:
        logger.error(f"Failed to process therapy session {session_id}: {e}")
        raise


@shared_task(bind=True, name="mentalhealth.analyze_chatbot_interaction")
def analyze_chatbot_interaction(self, interaction_id):
    """Background task to analyze chatbot interactions."""
    try:
        interaction = ChatbotInteraction.objects.get(id=interaction_id)

        # Sentiment analysis of conversation
        sentiment_score = analyze_conversation_sentiment(interaction.conversation_data)

        # Extract topics and concerns
        topics = extract_conversation_topics(interaction.conversation_data)

        # Calculate user satisfaction prediction
        satisfaction_prediction = predict_user_satisfaction(interaction)

        # Record analytics
        analytics.record(
            "chatbot.interaction_analyzed",
            interaction_id=interaction_id,
            sentiment_score=sentiment_score,
            topics_identified=len(topics),
            satisfaction_prediction=satisfaction_prediction,
        )

        return {
            "status": "success",
            "interaction_id": interaction_id,
            "sentiment_score": sentiment_score,
            "topics": topics,
        }

    except Exception as e:
        logger.error(f"Failed to analyze chatbot interaction {interaction_id}: {e}")
        raise


@shared_task(bind=True, name="mentalhealth.generate_treatment_insights")
def generate_treatment_insights(self, patient_id):
    """Background task to generate treatment insights for a patient."""
    try:
        # Aggregate patient therapy sessions
        sessions = TherapySession.objects.filter(
            patient_id=patient_id,
            status="completed",
        )

        # Generate insights
        insights = {
            "total_sessions": sessions.count(),
            "avg_effectiveness": sessions.aggregate(
                avg_score=models.Avg("effectiveness_score"),
            )["avg_score"],
            "progress_trend": calculate_progress_trend(sessions),
            "recommended_adjustments": generate_treatment_recommendations(sessions),
        }

        # Cache insights
        cache_key = f"treatment_insights:{patient_id}"
        cache.set(cache_key, insights, timeout=86400)  # 24 hours

        # Record analytics
        analytics.record(
            "treatment.insights_generated",
            patient_id=patient_id,
            total_sessions=insights["total_sessions"],
            avg_effectiveness=insights["avg_effectiveness"],
        )

        return {"status": "success", "patient_id": patient_id, "insights": insights}

    except Exception as e:
        logger.error(
            f"Failed to generate treatment insights for patient {patient_id}: {e}",
        )
        raise


# Helper functions for background tasks
def analyze_session_notes(notes: str) -> list[str]:
    """Analyze therapy session notes for insights."""
    try:
        # Placeholder for NLP analysis
        insights = [
            "Patient showed improved emotional regulation",
            "Stress management techniques were well-received",
            "Recommended continued focus on anxiety management",
        ]
        return insights
    except Exception:
        return []


def calculate_session_effectiveness(session) -> float:
    """Calculate effectiveness score for therapy session."""
    try:
        # Placeholder calculation based on various factors
        base_score = 7.5

        # Adjust based on session duration
        if hasattr(session, "duration_minutes"):
            if session.duration_minutes >= 45:
                base_score += 0.5
            elif session.duration_minutes < 30:
                base_score -= 0.5

        # Adjust based on notes quality
        if session.notes and len(session.notes) > 100:
            base_score += 0.3

        return min(max(base_score, 1.0), 10.0)  # Clamp between 1-10
    except Exception:
        return 7.0  # Default score


def analyze_conversation_sentiment(conversation_data: str) -> float:
    """Analyze sentiment of chatbot conversation."""
    try:
        # Placeholder for sentiment analysis
        return 0.6  # Slightly positive
    except Exception:
        return 0.5  # Neutral


def extract_conversation_topics(conversation_data: str) -> list[str]:
    """Extract main topics from conversation."""
    try:
        # Placeholder for topic extraction
        return ["anxiety", "stress_management", "coping_strategies"]
    except Exception:
        return []


def predict_user_satisfaction(interaction) -> float:
    """Predict user satisfaction with chatbot interaction."""
    try:
        # Placeholder for ML prediction
        return 0.8  # High satisfaction
    except Exception:
        return 0.5  # Neutral


def calculate_progress_trend(sessions) -> str:
    """Calculate patient progress trend."""
    try:
        if sessions.count() < 2:
            return "insufficient_data"

        # Simple trend calculation
        recent_avg = (
            sessions.order_by("-created")[:3].aggregate(
                avg=models.Avg("effectiveness_score"),
            )["avg"]
            or 0
        )

        older_avg = (
            sessions.order_by("-created")[3:6].aggregate(
                avg=models.Avg("effectiveness_score"),
            )["avg"]
            or 0
        )

        if recent_avg > older_avg + 0.5:
            return "improving"
        elif recent_avg < older_avg - 0.5:
            return "declining"
        else:
            return "stable"
    except Exception:
        return "unknown"


def generate_treatment_recommendations(sessions) -> list[str]:
    """Generate treatment recommendations based on session history."""
    try:
        recommendations = []

        if sessions.count() > 10:
            recommendations.append("Consider transitioning to bi-weekly sessions")

        avg_effectiveness = (
            sessions.aggregate(avg=models.Avg("effectiveness_score"))["avg"] or 0
        )
        if avg_effectiveness < 6.0:
            recommendations.append("Review current therapeutic approach")

        return recommendations
    except Exception:
        return []


class EnhancedMentalHealthThrottle(UserRateThrottle):
    """Enhanced rate throttling for mental health endpoints."""

    def throttle_failure(self):
        """Record throttling events for mental health analytics."""
        try:
            request = getattr(self, "request", None)
            if request:
                analytics.record(
                    "mentalhealth.api.throttled",
                    endpoint=request.path,
                    method=request.method,
                    user_id=request.user.id if request.user.is_authenticated else None,
                    throttle_type=self.__class__.__name__,
                )
        except Exception as e:
            logger.warning(f"Failed to record mental health throttle event: {e}")
        return super().throttle_failure()


class ComprehensiveMentalHealthMixin(AnalyticsRecordingMixin):
    """
    Comprehensive mixin for mental health viewsets with full infrastructure integration:
    - Advanced analytics tracking
    - Audit logging for compliance
    - Performance monitoring
    - Caching strategies
    - Security enhancements
    - Background task integration
    """

    # Caching configuration
    cache_timeout = 600  # 10 minutes default for mental health data
    cache_vary_headers = ["Authorization", "Accept-Language"]

    # Throttling configuration
    throttle_classes = [EnhancedMentalHealthThrottle]
    throttle_scope = "mentalhealth"

    # Analytics configuration
    track_analytics = True
    analytics_context = {"domain": "mental_health"}

    # Performance monitoring
    monitor_performance = True
    slow_query_threshold = 150  # ms (higher for complex mental health queries)

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
                "mentalhealth.api.request.started",
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
            logger.warning(f"Failed to record mental health request start: {e}")

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
                    "mentalhealth.api.request.completed",
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
            logger.warning(f"Failed to record mental health request success: {e}")

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
                    "mentalhealth.api.request.error",
                    request=request,
                    extra_data=error_context,
                )

            # Create audit log for security-related errors
            if isinstance(exception, (PermissionDenied,)):
                self._record_security_event(request, exception)

        except Exception as e:
            logger.error(f"Failed to record mental health request error: {e}")

    def _alert_slow_request(self, request, duration, metrics):
        """Alert on slow requests for performance monitoring."""
        try:
            logger.warning(
                f"Slow mental health request detected: {request.path} took {duration:.2f}ms",
                extra={
                    "slow_request": True,
                    "duration_ms": duration,
                    "endpoint": request.path,
                    "method": request.method,
                    "metrics": metrics,
                    "domain": "mental_health",
                },
            )
        except Exception as e:
            logger.error(f"Failed to alert on slow mental health request: {e}")

    def _record_security_event(self, request, exception):
        """Record security events in audit log."""
        try:
            create_audit_entry(
                request=request,
                event=(
                    audit_log.get_event_id("MENTAL_HEALTH_SECURITY_VIOLATION")
                    if hasattr(audit_log, "get_event_id")
                    else 1001
                ),
                data={
                    "violation_type": exception.__class__.__name__,
                    "message": str(exception),
                    "endpoint": request.path,
                    "method": request.method,
                    "domain": "mental_health",
                },
            )
        except Exception as e:
            logger.error(f"Failed to record mental health security event: {e}")

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
                f"Mental health database transaction completed in {duration:.2f}ms",
            )

        except Exception as e:
            # Record failed transaction
            duration = (time.time() - start_time) * 1000
            logger.warning(
                f"Mental health database transaction failed after {duration:.2f}ms: {e}",
            )
            raise

    def get_cached_data(self, cache_key: str, timeout: int | None = None) -> Any:
        """Get data from cache with hit/miss tracking."""
        timeout = timeout or self.cache_timeout

        try:
            instrumented_cache = get_instrumented_cache()
            data = instrumented_cache.get(cache_key)

            if data is None:
                logger.debug(f"Mental health cache miss for key: {cache_key}")
            else:
                logger.debug(f"Mental health cache hit for key: {cache_key}")

            return data

        except Exception as e:
            logger.warning(f"Mental health cache get failed for key {cache_key}: {e}")
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
            logger.warning(f"Mental health cache set failed for key {cache_key}: {e}")
            return False


class TherapyApproachViewSet(
    ComprehensiveMentalHealthMixin,
    viewsets.ReadOnlyModelViewSet,
):
    """
    Enhanced Therapy Approach ViewSet with comprehensive infrastructure integration.
    """

    queryset = TherapyApproach.objects.all()
    serializer_class = TherapyApproachSerializer
    permission_classes = [IsAuthenticated | ReadOnly]

    # Enhanced caching configuration
    cache_timeout = 1800  # 30 minutes for therapy approaches (stable data)

    # Analytics configuration
    analytics_context = {"model": "therapy_approach"}

    @method_decorator(cache_page(1800))  # 30 minutes
    def list(self, request, *args, **kwargs):
        """Enhanced list with caching and analytics."""
        cache_key = f"therapy_approaches_list:{request.user.id if request.user.is_authenticated else 'anon'}"

        # Try cache first
        cached_data = self.get_cached_data(cache_key)
        if cached_data:
            self.record_analytics_event(
                "therapy_approach.list.cache_hit",
                request=request,
                extra_data={"cached": True},
            )
            return Response(cached_data)

        # Cache miss - get fresh data
        response = super().list(request, *args, **kwargs)

        # Cache the response
        if response.status_code == 200:
            self.set_cached_data(cache_key, response.data)

        # Record analytics
        self.record_analytics_event(
            "therapy_approach.list.viewed",
            request=request,
            extra_data={"approach_count": len(response.data), "cached": False},
        )

        return response

    def retrieve(self, request, *args, **kwargs):
        """Enhanced retrieve with analytics tracking."""
        approach = self.get_object()

        # Record analytics
        self.record_analytics_event(
            "therapy_approach.detail.viewed",
            instance=approach,
            request=request,
            extra_data={"approach_id": approach.id},
        )

        # Audit log
        create_audit_entry(
            request=request,
            target_object=approach.id,
            event=(
                audit_log.get_event_id("THERAPY_APPROACH_VIEWED")
                if hasattr(audit_log, "get_event_id")
                else 1101
            ),
            data={"action": "therapy_approach_view", "approach_id": approach.id},
        )

        return super().retrieve(request, *args, **kwargs)


class TherapySessionViewSet(ComprehensiveMentalHealthMixin, viewsets.ModelViewSet):
    """
    Ultra-comprehensive Therapy Session ViewSet with full infrastructure integration.
    """

    queryset = TherapySession.objects.select_related(
        "patient",
        "therapist",
    ).prefetch_related("notes")
    serializer_class = TherapySessionSerializer
    filterset_class = TherapySessionFilter
    search_fields = ["summary", "notes"]
    ordering_fields = ["scheduled_at", "started_at", "ended_at"]
    permission_classes = [IsAuthenticated]

    # Enhanced caching configuration
    cache_timeout = 300  # 5 minutes for session data (dynamic)

    # Analytics configuration
    analytics_context = {"model": "therapy_session"}

    def get_queryset(self):
        """Secure queryset with proper filtering."""
        queryset = self.queryset

        # Apply security filters based on user permissions
        if not self.request.user.is_superuser:
            if hasattr(self.request.user, "therapist"):
                queryset = queryset.filter(therapist=self.request.user.therapist)
            elif hasattr(self.request.user, "patient"):
                queryset = queryset.filter(patient=self.request.user.patient)
            else:
                queryset = queryset.none()

        return queryset

    def perform_create(self, serializer):
        """Enhanced creation with comprehensive tracking."""
        with self.database_transaction_context():
            session = serializer.save()

            # Record analytics
            self.record_analytics_event(
                "therapy_session.created",
                instance=session,
                request=self.request,
                extra_data={
                    "session_id": session.id,
                    "therapist_id": (
                        session.therapist.id if hasattr(session, "therapist") else None
                    ),
                    "patient_id": (
                        session.patient.id if hasattr(session, "patient") else None
                    ),
                    "session_type": getattr(session, "session_type", None),
                    "scheduled_at": (
                        session.scheduled_at.isoformat()
                        if hasattr(session, "scheduled_at")
                        else None
                    ),
                },
            )

            # Audit log
            create_audit_entry(
                request=self.request,
                target_object=session.id,
                event=(
                    audit_log.get_event_id("THERAPY_SESSION_CREATE")
                    if hasattr(audit_log, "get_event_id")
                    else 1201
                ),
                data={
                    "session_id": session.id,
                    "therapist_id": (
                        session.therapist.id if hasattr(session, "therapist") else None
                    ),
                    "patient_id": (
                        session.patient.id if hasattr(session, "patient") else None
                    ),
                    "action": "therapy_session_create",
                },
            )

    def perform_update(self, serializer):
        """Enhanced update with status change tracking."""
        old_instance = self.get_object()
        old_status = getattr(old_instance, "status", None)

        with self.database_transaction_context():
            session = serializer.save()
            new_status = getattr(session, "status", None)

            # Track status changes
            if old_status != new_status and hasattr(TherapySession, "SessionStatus"):
                self._track_status_change(session, old_status, new_status)

            # Record general update analytics
            self.record_analytics_event(
                "therapy_session.updated",
                instance=session,
                request=self.request,
                extra_data={
                    "session_id": session.id,
                    "status_changed": old_status != new_status,
                    "old_status": old_status,
                    "new_status": new_status,
                },
            )

            # Audit log
            create_audit_entry(
                request=self.request,
                target_object=session.id,
                event=(
                    audit_log.get_event_id("THERAPY_SESSION_UPDATE")
                    if hasattr(audit_log, "get_event_id")
                    else 1202
                ),
                data={
                    "session_id": session.id,
                    "changes": {"status": {"old": old_status, "new": new_status}},
                    "action": "therapy_session_update",
                },
            )

    def _track_status_change(self, session, old_status, new_status):
        """Track specific status changes with detailed analytics."""
        try:
            if hasattr(TherapySession, "SessionStatus"):
                if new_status == getattr(
                    TherapySession.SessionStatus,
                    "ACCEPTED",
                    "accepted",
                ):
                    self.record_analytics_event(
                        "therapy_session.accepted",
                        instance=session,
                        request=self.request,
                        extra_data={
                            "session_id": session.id,
                            "therapist_id": (
                                session.therapist.id
                                if hasattr(session, "therapist")
                                else None
                            ),
                            "patient_id": (
                                session.patient.id
                                if hasattr(session, "patient")
                                else None
                            ),
                        },
                    )
                elif new_status == getattr(
                    TherapySession.SessionStatus,
                    "CANCELLED",
                    "cancelled",
                ):
                    self._track_session_cancellation(session)
                elif new_status == getattr(
                    TherapySession.SessionStatus,
                    "COMPLETED",
                    "completed",
                ):
                    self._track_session_completion(session)
        except Exception as e:
            logger.warning(f"Failed to track status change: {e}")

    def _track_session_cancellation(self, session):
        """Track session cancellation with detailed context."""
        try:
            notice_hours = None
            if (
                hasattr(session, "scheduled_at")
                and session.scheduled_at > timezone.now()
            ):
                notice_delta = session.scheduled_at - timezone.now()
                notice_hours = int(notice_delta.total_seconds() / 3600)

            self.record_analytics_event(
                "therapy_session.cancelled",
                instance=session,
                request=self.request,
                extra_data={
                    "session_id": session.id,
                    "therapist_id": (
                        session.therapist.id if hasattr(session, "therapist") else None
                    ),
                    "patient_id": (
                        session.patient.id if hasattr(session, "patient") else None
                    ),
                    "cancelled_by": "therapist",  # Could be enhanced to detect actual canceller
                    "notice_hours": notice_hours,
                    "reason": getattr(session, "cancellation_reason", None),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to track session cancellation: {e}")

    def _track_session_completion(self, session):
        """Track session completion with detailed analytics."""
        try:
            # Calculate duration if available
            duration_minutes = None
            if hasattr(session, "started_at") and hasattr(session, "ended_at"):
                if session.started_at and session.ended_at:
                    duration = session.ended_at - session.started_at
                    duration_minutes = int(duration.total_seconds() / 60)

            self.record_analytics_event(
                "therapy_session.completed",
                instance=session,
                request=self.request,
                extra_data={
                    "session_id": session.id,
                    "therapist_id": (
                        session.therapist.id if hasattr(session, "therapist") else None
                    ),
                    "patient_id": (
                        session.patient.id if hasattr(session, "patient") else None
                    ),
                    "session_type": getattr(session, "session_type", None),
                    "duration_minutes": duration_minutes,
                    "has_notes": bool(getattr(session, "notes", None)),
                    "has_summary": bool(getattr(session, "summary", None)),
                },
            )

            # Trigger background processing
            process_therapy_session.delay(session.id)

        except Exception as e:
            logger.warning(f"Failed to track session completion: {e}")

    @action(detail=True, methods=["post"])
    def start_session(self, request, pk=None):
        """Enhanced session start with comprehensive tracking."""
        session = self.get_object()

        if getattr(session, "started_at", None):
            return Response({"error": "Session already started"}, status=400)

        with self.database_transaction_context():
            session.started_at = timezone.now()
            if hasattr(session, "status") and hasattr(TherapySession, "SessionStatus"):
                session.status = getattr(
                    TherapySession.SessionStatus,
                    "IN_PROGRESS",
                    "in_progress",
                )
            session.save()

            # Calculate delay if any
            delay_minutes = None
            if (
                hasattr(session, "scheduled_at")
                and session.started_at > session.scheduled_at
            ):
                delay = session.started_at - session.scheduled_at
                delay_minutes = int(delay.total_seconds() / 60)

            # Record analytics
            self.record_analytics_event(
                "therapy_session.started",
                instance=session,
                request=request,
                extra_data={
                    "session_id": session.id,
                    "therapist_id": (
                        session.therapist.id if hasattr(session, "therapist") else None
                    ),
                    "patient_id": (
                        session.patient.id if hasattr(session, "patient") else None
                    ),
                    "session_type": getattr(session, "session_type", None),
                    "actual_start_time": session.started_at.isoformat(),
                    "scheduled_start_time": (
                        session.scheduled_at.isoformat()
                        if hasattr(session, "scheduled_at")
                        else None
                    ),
                    "delay_minutes": delay_minutes,
                },
            )

            # Audit log
            create_audit_entry(
                request=request,
                target_object=session.id,
                event=(
                    audit_log.get_event_id("THERAPY_SESSION_STARTED")
                    if hasattr(audit_log, "get_event_id")
                    else 1203
                ),
                data={
                    "session_id": session.id,
                    "started_at": session.started_at.isoformat(),
                    "delay_minutes": delay_minutes,
                    "action": "therapy_session_start",
                },
            )

        return Response({"status": "Session started"})

    @action(detail=True, methods=["post"])
    def complete_session(self, request, pk=None):
        """Enhanced session completion with comprehensive tracking."""
        session = self.get_object()

        if not getattr(session, "started_at", None):
            return Response({"error": "Session not started"}, status=400)

        if getattr(session, "ended_at", None):
            return Response({"error": "Session already completed"}, status=400)

        with self.database_transaction_context():
            session.ended_at = timezone.now()
            if hasattr(session, "status") and hasattr(TherapySession, "SessionStatus"):
                session.status = getattr(
                    TherapySession.SessionStatus,
                    "COMPLETED",
                    "completed",
                )
            session.save()

            # Calculate duration
            duration = session.ended_at - session.started_at
            duration_minutes = int(duration.total_seconds() / 60)

            # Record analytics
            self.record_analytics_event(
                "therapy_session.completed",
                instance=session,
                request=request,
                extra_data={
                    "session_id": session.id,
                    "therapist_id": (
                        session.therapist.id if hasattr(session, "therapist") else None
                    ),
                    "patient_id": (
                        session.patient.id if hasattr(session, "patient") else None
                    ),
                    "session_type": getattr(session, "session_type", None),
                    "duration_minutes": duration_minutes,
                    "has_notes": bool(getattr(session, "notes", None)),
                    "has_summary": bool(getattr(session, "summary", None)),
                },
            )

            # Audit log
            create_audit_entry(
                request=request,
                target_object=session.id,
                event=(
                    audit_log.get_event_id("THERAPY_SESSION_COMPLETED")
                    if hasattr(audit_log, "get_event_id")
                    else 1204
                ),
                data={
                    "session_id": session.id,
                    "duration_minutes": duration_minutes,
                    "completed_at": session.ended_at.isoformat(),
                    "action": "therapy_session_complete",
                },
            )

            # Trigger background processing
            process_therapy_session.delay(session.id)

        return Response({"status": "Session completed"})

    @action(detail=True, methods=["post"])
    def cancel_session(self, request, pk=None):
        """Enhanced session cancellation with comprehensive tracking."""
        session = self.get_object()
        reason = request.data.get("reason", "")

        with self.database_transaction_context():
            if hasattr(session, "status") and hasattr(TherapySession, "SessionStatus"):
                session.status = getattr(
                    TherapySession.SessionStatus,
                    "CANCELLED",
                    "cancelled",
                )
            if hasattr(session, "cancellation_reason"):
                session.cancellation_reason = reason
            session.save()

            # Calculate notice hours
            notice_hours = None
            if (
                hasattr(session, "scheduled_at")
                and session.scheduled_at > timezone.now()
            ):
                notice_delta = session.scheduled_at - timezone.now()
                notice_hours = int(notice_delta.total_seconds() / 3600)

            # Determine who cancelled
            cancelled_by = "therapist"  # Default assumption
            if hasattr(request.user, "patient_profile"):
                cancelled_by = "patient"

            # Record analytics
            self.record_analytics_event(
                "therapy_session.cancelled",
                instance=session,
                request=request,
                extra_data={
                    "session_id": session.id,
                    "therapist_id": (
                        session.therapist.id if hasattr(session, "therapist") else None
                    ),
                    "patient_id": (
                        session.patient.id if hasattr(session, "patient") else None
                    ),
                    "cancelled_by": cancelled_by,
                    "notice_hours": notice_hours,
                    "reason": reason,
                },
            )

            # Audit log
            create_audit_entry(
                request=request,
                target_object=session.id,
                event=(
                    audit_log.get_event_id("THERAPY_SESSION_CANCELLED")
                    if hasattr(audit_log, "get_event_id")
                    else 1205
                ),
                data={
                    "session_id": session.id,
                    "cancelled_by": cancelled_by,
                    "reason": reason,
                    "notice_hours": notice_hours,
                    "action": "therapy_session_cancel",
                },
            )

        return Response({"status": "Session cancelled"})


class ChatbotInteractionViewSet(ComprehensiveMentalHealthMixin, viewsets.ModelViewSet):
    """
    Enhanced Chatbot Interaction ViewSet with comprehensive infrastructure integration.
    """

    queryset = ChatbotInteraction.objects.select_related("patient")
    serializer_class = ChatbotInteractionSerializer
    permission_classes = [IsAuthenticated]

    # Enhanced caching configuration
    cache_timeout = 180  # 3 minutes for chatbot data (very dynamic)

    # Analytics configuration
    analytics_context = {"model": "chatbot_interaction"}

    def get_queryset(self):
        """Secure queryset with proper filtering."""
        queryset = self.queryset

        # Users can only see their own interactions
        if hasattr(self.request.user, "patient"):
            queryset = queryset.filter(patient=self.request.user.patient)
        elif not self.request.user.is_superuser:
            queryset = queryset.none()

        return queryset

    def perform_create(self, serializer):
        """Enhanced creation with comprehensive tracking."""
        with self.database_transaction_context():
            interaction = serializer.save()

            # Record analytics
            self.record_analytics_event(
                "chatbot.interaction",
                instance=interaction,
                request=self.request,
                extra_data={
                    "interaction_id": interaction.id,
                    "patient_id": (
                        interaction.patient.id
                        if hasattr(interaction, "patient")
                        else None
                    ),
                    "message_count": getattr(interaction, "message_count", 1),
                    "session_duration_seconds": getattr(
                        interaction,
                        "session_duration_seconds",
                        None,
                    ),
                    "satisfaction_score": getattr(
                        interaction,
                        "satisfaction_score",
                        None,
                    ),
                },
            )

            # Audit log
            create_audit_entry(
                request=self.request,
                target_object=interaction.id,
                event=(
                    audit_log.get_event_id("CHATBOT_INTERACTION_CREATE")
                    if hasattr(audit_log, "get_event_id")
                    else 1301
                ),
                data={
                    "interaction_id": interaction.id,
                    "patient_id": (
                        interaction.patient.id
                        if hasattr(interaction, "patient")
                        else None
                    ),
                    "action": "chatbot_interaction_create",
                },
            )

            # Trigger background analysis
            analyze_chatbot_interaction.delay(interaction.id)

    def perform_update(self, serializer):
        """Enhanced update with interaction analysis."""
        with self.database_transaction_context():
            interaction = serializer.save()

            # Record analytics for interaction updates
            self.record_analytics_event(
                "chatbot.interaction.updated",
                instance=interaction,
                request=self.request,
                extra_data={
                    "interaction_id": interaction.id,
                    "patient_id": (
                        interaction.patient.id
                        if hasattr(interaction, "patient")
                        else None
                    ),
                },
            )

            # Re-trigger analysis if significant changes
            analyze_chatbot_interaction.delay(interaction.id)


class DisorderViewSet(ComprehensiveMentalHealthMixin, viewsets.ModelViewSet):
    """
    Enhanced Disorder ViewSet with comprehensive infrastructure integration.
    """

    queryset = Disorder.objects.all()
    serializer_class = DisorderSerializer
    permission_classes = [IsAuthenticated | ReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["name"]

    # Enhanced caching configuration
    cache_timeout = 3600  # 1 hour for disorder data (stable reference data)

    # Analytics configuration
    analytics_context = {"model": "disorder"}

    @method_decorator(cache_page(3600))  # 1 hour
    def list(self, request, *args, **kwargs):
        """Enhanced list with comprehensive caching."""
        cache_key = f"disorders_list:{hash(str(request.query_params))}"

        # Try cache first
        cached_data = self.get_cached_data(cache_key)
        if cached_data:
            self.record_analytics_event(
                "disorder.list.cache_hit",
                request=request,
                extra_data={"cached": True},
            )
            return Response(cached_data)

        # Cache miss - get fresh data
        response = super().list(request, *args, **kwargs)

        # Cache the response
        if response.status_code == 200:
            self.set_cached_data(cache_key, response.data)

        # Record analytics
        self.record_analytics_event(
            "disorder.list.viewed",
            request=request,
            extra_data={
                "disorder_count": len(response.data),
                "cached": False,
                "filters_applied": bool(request.query_params),
            },
        )

        return response

    def retrieve(self, request, *args, **kwargs):
        """Enhanced retrieve with analytics tracking."""
        disorder = self.get_object()

        # Record analytics
        self.record_analytics_event(
            "disorder.detail.viewed",
            instance=disorder,
            request=request,
            extra_data={
                "disorder_id": disorder.id,
                "disorder_name": getattr(disorder, "name", None),
            },
        )

        return super().retrieve(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Enhanced creation for new disorders."""
        with self.database_transaction_context():
            disorder = serializer.save()

            # Record analytics
            self.record_analytics_event(
                "disorder.created",
                instance=disorder,
                request=self.request,
                extra_data={
                    "disorder_id": disorder.id,
                    "disorder_name": getattr(disorder, "name", None),
                    "created_by": self.request.user.id,
                },
            )

            # Audit log
            create_audit_entry(
                request=self.request,
                target_object=disorder.id,
                event=(
                    audit_log.get_event_id("DISORDER_CREATE")
                    if hasattr(audit_log, "get_event_id")
                    else 1401
                ),
                data={
                    "disorder_id": disorder.id,
                    "disorder_name": getattr(disorder, "name", None),
                    "action": "disorder_create",
                },
            )

            # Invalidate list caches
            self._invalidate_disorder_caches()

    def _invalidate_disorder_caches(self):
        """Invalidate disorder-related caches."""
        try:
            # This would normally use a more sophisticated cache invalidation pattern
            cache.delete_many(
                [
                    "disorders_list:*",  # Would need custom implementation for wildcard
                ],
            )
            logger.debug("Invalidated disorder caches")
        except Exception as e:
            logger.warning(f"Failed to invalidate disorder caches: {e}")
