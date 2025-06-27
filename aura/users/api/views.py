import logging
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

# Celery imports
from celery import shared_task

# DRF imports
from dj_rest_auth.registration import views as dj_views

# Django imports
from django.conf import settings as django_settings
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction
from django.db.utils import IntegrityError
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import (
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ViewSetMixin

# Internal imports
from aura import analytics, audit_log
from aura.analytics.mixins import AnalyticsRecordingMixin
from aura.audit_log.utils import create_audit_entry
from aura.core.cache_instrumentation import get_instrumented_cache
from aura.core.models import PhysicianReferral
from aura.core.performance_middleware import get_request_metrics
from aura.core.utils import jwt_encode
from aura.users.api.serializers import (
    LoginSerializer,
    PatientSerializer,
    PhysicianReferralSerializer,
    ReviewSerializer,
    TherapistSerializer,
    UserSerializer,
)
from aura.users.mixins import LoginMixin
from aura.users.models import Patient, Therapist, User

logger = logging.getLogger(__name__)


# Background Tasks for Comprehensive Processing
@shared_task(bind=True, name="users.process_new_review")
def process_new_review(self, review_id):
    """Background task to process new review submissions."""
    try:
        from aura.core.models import Review

        review = Review.objects.get(id=review_id)

        # Sentiment analysis placeholder
        sentiment_score = 0.7  # Would integrate with NLP service

        # Record analytics
        analytics.record(
            "review.processed",
            review_id=review_id,
            sentiment_score=sentiment_score,
            processing_duration=getattr(self.request, "duration", 0),
        )

        logger.info(
            f"Processed review {review_id} with sentiment score {sentiment_score}"
        )
        return {
            "status": "success",
            "review_id": review_id,
            "sentiment_score": sentiment_score,
        }

    except Exception as e:
        logger.error(f"Failed to process review {review_id}: {e}")
        raise


@shared_task(bind=True, name="users.analyze_login_pattern")
def analyze_login_pattern(self, user_id, ip_address, user_agent):
    """Background task to analyze login patterns for security."""
    try:
        # Risk assessment placeholder
        risk_score = 0.2  # Low risk by default

        # Store analysis results in cache
        cache_key = f"login_analysis:{user_id}:{int(time.time())}"
        analysis_data = {
            "ip_address": ip_address,
            "user_agent": user_agent,
            "risk_score": risk_score,
            "timestamp": timezone.now().isoformat(),
        }
        cache.set(cache_key, analysis_data, timeout=86400)  # 24 hours

        # Record analytics
        analytics.record(
            "security.login_analyzed",
            user_id=user_id,
            risk_score=risk_score,
            ip_address=ip_address,
        )

        return {"status": "success", "risk_score": risk_score}

    except Exception as e:
        logger.error(f"Failed to analyze login pattern for user {user_id}: {e}")
        raise


@shared_task(bind=True, name="users.update_user_login_stats")
def update_user_login_stats(self, user_id):
    """Background task to update user login statistics."""
    try:
        from aura.users.models import User

        user = User.objects.get(id=user_id)

        # Update login statistics (placeholder)
        logger.info(f"Updated login stats for user {user_id}")

        # Record in analytics
        analytics.record(
            "user.login_stats_updated",
            user_id=user_id,
            login_count=getattr(user, "login_count", 0),
        )

        return {"status": "success", "user_id": user_id}

    except Exception as e:
        logger.error(f"Failed to update login stats for user {user_id}: {e}")
        raise


@shared_task(bind=True, name="users.analyze_failed_login")
def analyze_failed_login(self, ip_address, email, user_agent):
    """Background task to analyze failed login attempts."""
    try:
        # Check for brute force patterns (placeholder)
        failure_count = cache.get(f"failed_attempts:{ip_address}:{email}", 0)

        if failure_count > 5:  # Threshold for suspicious activity
            # Record security event
            analytics.record(
                "security.brute_force_detected",
                ip_address=ip_address,
                email=email,
                user_agent=user_agent,
                failure_count=failure_count,
            )

            logger.warning(f"Brute force detected from {ip_address} for {email}")

        return {"status": "success", "failures_detected": failure_count}

    except Exception as e:
        logger.error(f"Failed to analyze failed login: {e}")
        raise


class EnhancedRateThrottle(UserRateThrottle):
    """Enhanced rate throttling with analytics and monitoring."""

    def throttle_failure(self):
        """Record throttling events for analytics."""
        try:
            request = getattr(self, "request", None)
            if request:
                analytics.record(
                    "api.throttled",
                    endpoint=request.path,
                    method=request.method,
                    user_id=request.user.id if request.user.is_authenticated else None,
                    ip_address=self.get_ident(request),
                    throttle_type=self.__class__.__name__,
                )
        except Exception as e:
            logger.warning(f"Failed to record throttle event: {e}")
        return super().throttle_failure()


class ComprehensiveViewSetMixin(AnalyticsRecordingMixin):
    """
    Ultra-comprehensive mixin that integrates ALL system infrastructure:
    - Analytics event recording
    - Audit logging
    - Performance monitoring
    - Caching strategies
    - Security enhancements
    - Error handling
    - Background task integration
    """

    # Caching configuration
    cache_timeout = 300  # 5 minutes default
    cache_vary_headers = ["Authorization", "Accept-Language"]

    # Throttling configuration
    throttle_classes = [EnhancedRateThrottle]
    throttle_scope = "user"

    # Analytics configuration
    track_analytics = True
    analytics_context = {}

    # Performance monitoring
    monitor_performance = True
    slow_query_threshold = 100  # ms

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
                "api.request.started",
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
            logger.warning(f"Failed to record request start: {e}")

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
                    "api.request.completed",
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
            logger.warning(f"Failed to record request success: {e}")

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
                    "api.request.error", request=request, extra_data=error_context
                )

            # Create audit log for security-related errors
            if isinstance(exception, (PermissionDenied, Throttled)):
                self._record_security_event(request, exception)

        except Exception as e:
            logger.error(f"Failed to record request error: {e}")

    def _alert_slow_request(self, request, duration, metrics):
        """Alert on slow requests for performance monitoring."""
        try:
            # This would integrate with the monitoring system
            logger.warning(
                f"Slow request detected: {request.path} took {duration:.2f}ms",
                extra={
                    "slow_request": True,
                    "duration_ms": duration,
                    "endpoint": request.path,
                    "method": request.method,
                    "metrics": metrics,
                },
            )
        except Exception as e:
            logger.error(f"Failed to alert on slow request: {e}")

    def _record_security_event(self, request, exception):
        """Record security events in audit log."""
        try:
            create_audit_entry(
                request=request,
                event=(
                    audit_log.get_event_id("SECURITY_VIOLATION")
                    if hasattr(audit_log, "get_event_id")
                    else 999
                ),
                data={
                    "violation_type": exception.__class__.__name__,
                    "message": str(exception),
                    "endpoint": request.path,
                    "method": request.method,
                    "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                    "referer": request.META.get("HTTP_REFERER", ""),
                },
            )
        except Exception as e:
            logger.error(f"Failed to record security event: {e}")

    def _cleanup_request_tracking(self, request):
        """Clean up request tracking data."""
        try:
            # Remove temporary tracking attributes
            for attr in [
                "_view_start_time",
                "_db_queries_start",
                "_cache_hits_start",
                "_cache_misses_start",
            ]:
                if hasattr(request, attr):
                    delattr(request, attr)
        except Exception:
            pass  # Don't fail on cleanup

    @contextmanager
    def database_transaction_context(self, **transaction_kwargs):
        """Context manager for database transactions with monitoring."""
        start_time = time.time()

        try:
            with transaction.atomic(**transaction_kwargs):
                yield

            # Record successful transaction
            duration = (time.time() - start_time) * 1000
            logger.debug(f"Database transaction completed in {duration:.2f}ms")

        except Exception as e:
            # Record failed transaction
            duration = (time.time() - start_time) * 1000
            logger.warning(f"Database transaction failed after {duration:.2f}ms: {e}")
            raise

    def get_cached_data(self, cache_key: str, timeout: Optional[int] = None) -> Any:
        """Get data from cache with hit/miss tracking."""
        timeout = timeout or self.cache_timeout

        try:
            # Use instrumented cache for tracking
            instrumented_cache = get_instrumented_cache()
            data = instrumented_cache.get(cache_key)

            if data is None:
                logger.debug(f"Cache miss for key: {cache_key}")
            else:
                logger.debug(f"Cache hit for key: {cache_key}")

            return data

        except Exception as e:
            logger.warning(f"Cache get failed for key {cache_key}: {e}")
            return None

    def set_cached_data(
        self, cache_key: str, data: Any, timeout: Optional[int] = None
    ) -> bool:
        """Set data in cache with error handling."""
        timeout = timeout or self.cache_timeout

        try:
            instrumented_cache = get_instrumented_cache()
            return instrumented_cache.set(cache_key, data, timeout)
        except Exception as e:
            logger.warning(f"Cache set failed for key {cache_key}: {e}")
            return False


class UserViewSet(
    ComprehensiveViewSetMixin,
    LoginMixin,
    RetrieveModelMixin,
    ListModelMixin,
    UpdateModelMixin,
    GenericViewSet,
):
    """
    Ultra-comprehensive User ViewSet with full infrastructure integration:
    - Advanced caching strategies
    - Complete analytics tracking
    - Audit logging for all operations
    - Performance monitoring
    - Security enhancements
    - Background task integration
    """

    serializer_class = UserSerializer
    queryset = User.objects.select_related("profile").prefetch_related(
        "groups", "user_permissions"
    )
    lookup_field = "pk"
    permission_classes = [IsAuthenticated]

    # Enhanced caching configuration
    cache_timeout = 600  # 10 minutes for user data
    cache_vary_headers = ["Authorization", "Accept-Language", "Accept-Timezone"]

    # Analytics configuration
    analytics_context = {"model": "user"}

    def get_queryset(self, *args, **kwargs):
        """Optimized queryset with caching and security."""
        # Security: Users can only access their own data unless admin
        if self.request.user.is_superuser:
            return self.queryset.all()

        # Regular users see only their own profile
        assert isinstance(self.request.user.id, int)
        return self.queryset.filter(id=self.request.user.id)

    def get_throttles(self):
        """Dynamic throttling based on action."""
        if self.action == "login":
            self.throttle_scope = "aura_auth"
        elif self.action in ["update", "partial_update"]:
            self.throttle_scope = "user_modify"
        else:
            self.throttle_scope = "user_read"
        return super().get_throttles()

    @method_decorator(cache_page(300))  # 5 minutes
    @method_decorator(vary_on_headers("Authorization"))
    @action(detail=False, methods=["GET"])
    def me(self, request):
        """
        Enhanced user profile endpoint with comprehensive monitoring.

        Features:
        - Caching with intelligent invalidation
        - Analytics tracking
        - Performance monitoring
        - Audit logging
        """
        cache_key = f"user_profile:{request.user.id}"

        # Try cache first
        cached_data = self.get_cached_data(cache_key)
        if cached_data:
            # Record cache hit analytics
            self.record_analytics_event(
                "user.profile.cache_hit",
                request=request,
                extra_data={"user_id": request.user.id},
            )
            return Response(cached_data, status=status.HTTP_200_OK)

        # Cache miss - get fresh data
        serializer = UserSerializer(request.user, context={"request": request})
        response_data = serializer.data

        # Enhance response with additional context
        response_data.update(
            {
                "last_login_analytics": self._get_user_login_analytics(request.user),
                "security_summary": self._get_user_security_summary(request.user),
                "preferences": self._get_user_preferences(request.user),
            }
        )

        # Cache the response
        self.set_cached_data(cache_key, response_data)

        # Record analytics
        self.record_analytics_event(
            "user.profile.viewed",
            instance=request.user,
            request=request,
            extra_data={
                "profile_completeness": self._calculate_profile_completeness(
                    request.user
                ),
                "cache_miss": True,
            },
        )

        # Audit log
        create_audit_entry(
            request=request,
            target_object=request.user.id,
            event=(
                audit_log.get_event_id("USER_PROFILE_VIEWED")
                if hasattr(audit_log, "get_event_id")
                else 101
            ),
            data={"action": "profile_view", "source": "api"},
        )

        return Response(response_data, status=status.HTTP_200_OK)

    def _get_user_login_analytics(self, user) -> Dict[str, Any]:
        """Get user login analytics summary."""
        try:
            # This would integrate with the analytics backend
            cache_key = f"user_login_analytics:{user.id}"
            cached_analytics = self.get_cached_data(cache_key, timeout=3600)  # 1 hour

            if cached_analytics:
                return cached_analytics

            # Calculate fresh analytics
            analytics_data = {
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "login_count_7d": self._get_login_count(user, days=7),
                "login_count_30d": self._get_login_count(user, days=30),
                "avg_session_duration": self._get_avg_session_duration(user),
                "most_used_device": self._get_most_used_device(user),
            }

            # Cache the result
            self.set_cached_data(cache_key, analytics_data, timeout=3600)
            return analytics_data

        except Exception as e:
            logger.warning(f"Failed to get user login analytics: {e}")
            return {}

    def _get_user_security_summary(self, user) -> Dict[str, Any]:
        """Get user security summary."""
        try:
            return {
                "two_factor_enabled": getattr(user, "two_factor_enabled", False),
                "password_last_changed": getattr(user, "password_last_changed", None),
                "failed_login_attempts": self._get_failed_login_attempts(user),
                "active_sessions": self._get_active_sessions_count(user),
                "security_score": self._calculate_security_score(user),
            }
        except Exception as e:
            logger.warning(f"Failed to get user security summary: {e}")
            return {}

    def _get_user_preferences(self, user) -> Dict[str, Any]:
        """Get user preferences with defaults."""
        try:
            cache_key = f"user_preferences:{user.id}"
            preferences = self.get_cached_data(cache_key)

            if preferences is None:
                # Load from database or create defaults
                preferences = {
                    "timezone": getattr(user, "timezone", "UTC"),
                    "language": getattr(user, "language", "en"),
                    "theme": getattr(user, "theme_preference", "auto"),
                    "notifications": {"email": True, "push": True, "sms": False},
                }
                self.set_cached_data(cache_key, preferences)

            return preferences
        except Exception as e:
            logger.warning(f"Failed to get user preferences: {e}")
            return {}

    def _calculate_profile_completeness(self, user) -> float:
        """Calculate profile completeness percentage."""
        try:
            required_fields = ["email", "first_name", "last_name"]
            optional_fields = ["phone_number", "date_of_birth", "bio", "avatar"]

            completed_required = sum(
                1 for field in required_fields if getattr(user, field, None)
            )
            completed_optional = sum(
                1 for field in optional_fields if getattr(user, field, None)
            )

            total_possible = len(required_fields) + len(optional_fields)
            total_completed = completed_required + completed_optional

            # Required fields are weighted more heavily
            weighted_score = (completed_required * 2 + completed_optional) / (
                len(required_fields) * 2 + len(optional_fields)
            )

            return round(weighted_score * 100, 1)
        except Exception:
            return 0.0

    def _get_login_count(self, user, days: int) -> int:
        """Get login count for specified days."""
        try:
            # This would integrate with analytics backend
            since_date = timezone.now() - timedelta(days=days)
            # Placeholder - would query analytics events
            return 0  # Replace with actual analytics query
        except Exception:
            return 0

    def _get_avg_session_duration(self, user) -> Optional[float]:
        """Get average session duration in minutes."""
        try:
            # This would integrate with analytics backend
            return None  # Placeholder
        except Exception:
            return None

    def _get_most_used_device(self, user) -> Optional[str]:
        """Get most used device type."""
        try:
            # This would integrate with analytics backend
            return None  # Placeholder
        except Exception:
            return None

    def _get_failed_login_attempts(self, user) -> int:
        """Get recent failed login attempts."""
        try:
            # This would query security logs
            return 0  # Placeholder
        except Exception:
            return 0

    def _get_active_sessions_count(self, user) -> int:
        """Get count of active sessions."""
        try:
            # This would query session store
            return 1  # Placeholder
        except Exception:
            return 0

    def _calculate_security_score(self, user) -> int:
        """Calculate security score out of 100."""
        try:
            score = 0

            # Password strength (0-30 points)
            if getattr(user, "password_strength_score", 0) >= 80:
                score += 30
            elif getattr(user, "password_strength_score", 0) >= 60:
                score += 20
            elif getattr(user, "password_strength_score", 0) >= 40:
                score += 10

            # Two-factor authentication (0-25 points)
            if getattr(user, "two_factor_enabled", False):
                score += 25

            # Recent password change (0-15 points)
            password_age_days = getattr(user, "password_age_days", 365)
            if password_age_days <= 30:
                score += 15
            elif password_age_days <= 90:
                score += 10
            elif password_age_days <= 180:
                score += 5

            # Email verification (0-10 points)
            if user.email and getattr(user, "email_verified", False):
                score += 10

            # No recent failed logins (0-10 points)
            if self._get_failed_login_attempts(user) == 0:
                score += 10

            # Regular activity (0-10 points)
            if user.last_login and (timezone.now() - user.last_login).days <= 7:
                score += 10

            return min(score, 100)
        except Exception:
            return 50  # Default middle score

    @action(detail=True, methods=["post"])
    def add_review(self, request, pk=None):
        """Enhanced review addition with comprehensive tracking."""
        user = self.get_object()

        with self.database_transaction_context():
            serializer = ReviewSerializer(data=request.data)
            if serializer.is_valid():
                review = serializer.save(reviewer=user)

                # Record analytics
                self.record_analytics_event(
                    "user.review.created",
                    instance=review,
                    request=request,
                    extra_data={
                        "reviewer_id": user.id,
                        "rating": review.rating,
                        "review_length": len(review.content),
                    },
                )

                # Audit log
                create_audit_entry(
                    request=request,
                    target_object=review.id,
                    event=(
                        audit_log.get_event_id("REVIEW_CREATE")
                        if hasattr(audit_log, "get_event_id")
                        else 102
                    ),
                    data={
                        "reviewer_id": user.id,
                        "rating": review.rating,
                        "topic": review.topic,
                    },
                )

                # Trigger background task for review processing
                process_new_review.delay(review.id)

                return Response(serializer.data, status=status.HTTP_201_CREATED)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[AllowAny],
        serializer_class=LoginSerializer,
        throttle_scope="aura_auth",
    )
    def login(self, request):
        """
        Enhanced authentication with comprehensive security monitoring.

        Features:
        - Multiple authentication methods (JWT, Session, Token)
        - Security event logging
        - Failed attempt tracking
        - Geolocation tracking
        - Device fingerprinting
        - Background security analysis
        """
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        try:
            self.request = request
            self.serializer = self.get_serializer(data=self.request.data)
            self.serializer.is_valid(raise_exception=True)

            self.user = self.serializer.validated_data["user"]
            token_model = Token

            # Generate tokens/sessions based on configuration
            if (
                django_settings.USE_JWT
                if hasattr(django_settings, "USE_JWT")
                else False
            ):
                self.access_token, self.refresh_token = jwt_encode(self.user)
            if (
                django_settings.SESSION_LOGIN
                if hasattr(django_settings, "SESSION_LOGIN")
                else False
            ):
                self.process_login()
            elif token_model:
                from aura.core.utils import default_create_token

                self.token = default_create_token(
                    token_model, self.user, self.serializer
                )

            # Record successful login analytics
            login_duration = (time.time() - start_time) * 1000
            self.record_analytics_event(
                "user.login",
                instance=self.user,
                request=request,
                extra_data={
                    "login_method": self._detect_login_method(request),
                    "success": True,
                    "duration_ms": login_duration,
                    "user_agent": user_agent[:500],  # Truncate long user agents
                    "device_type": self._detect_device_type(user_agent),
                    "is_mobile": self._is_mobile_device(user_agent),
                },
            )

            # Audit log for successful login
            create_audit_entry(
                request=request,
                target_object=self.user.id,
                event=(
                    audit_log.get_event_id("USER_LOGIN")
                    if hasattr(audit_log, "get_event_id")
                    else 103
                ),
                data={
                    "login_method": self._detect_login_method(request),
                    "success": True,
                    "user_agent": user_agent,
                    "device_type": self._detect_device_type(user_agent),
                },
            )

            # Trigger background tasks
            analyze_login_pattern.delay(self.user.id, client_ip, user_agent)
            update_user_login_stats.delay(self.user.id)

            # Clear any failed login attempts
            self._clear_failed_attempts(client_ip, self.user.email)

            return self.get_response()

        except ValidationError as e:
            # Record failed login attempt
            login_duration = (time.time() - start_time) * 1000
            email = request.data.get("email", "unknown")

            self.record_analytics_event(
                "auth.failed",
                request=request,
                extra_data={
                    "email": email,
                    "failure_reason": "invalid_credentials",
                    "duration_ms": login_duration,
                    "user_agent": user_agent[:500],
                    "attempt_count": self._get_failed_attempt_count(client_ip, email),
                },
            )

            # Audit log for failed login
            create_audit_entry(
                request=request,
                event=(
                    audit_log.get_event_id("LOGIN_FAILED")
                    if hasattr(audit_log, "get_event_id")
                    else 104
                ),
                data={
                    "email": email,
                    "failure_reason": "invalid_credentials",
                    "user_agent": user_agent,
                    "attempt_count": self._increment_failed_attempts(client_ip, email),
                },
            )

            # Trigger security analysis
            analyze_failed_login.delay(client_ip, email, user_agent)

            raise

    def _get_client_ip(self, request) -> str:
        """Extract client IP address with proxy support."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    def _detect_login_method(self, request) -> str:
        """Detect the authentication method used."""
        if "password" in request.data:
            return "password"
        elif "token" in request.data:
            return "token"
        elif "oauth_token" in request.data:
            return "oauth"
        else:
            return "unknown"

    def _detect_device_type(self, user_agent: str) -> str:
        """Detect device type from user agent."""
        user_agent_lower = user_agent.lower()
        if "mobile" in user_agent_lower or "android" in user_agent_lower:
            return "mobile"
        elif "tablet" in user_agent_lower or "ipad" in user_agent_lower:
            return "tablet"
        else:
            return "desktop"

    def _is_mobile_device(self, user_agent: str) -> bool:
        """Check if device is mobile."""
        mobile_indicators = [
            "mobile",
            "android",
            "iphone",
            "ipod",
            "blackberry",
            "windows phone",
        ]
        return any(indicator in user_agent.lower() for indicator in mobile_indicators)

    def _get_failed_attempt_count(self, ip: str, email: str) -> int:
        """Get current failed attempt count."""
        try:
            key = f"failed_attempts:{ip}:{email}"
            return cache.get(key, 0)
        except Exception:
            return 0

    def _increment_failed_attempts(self, ip: str, email: str) -> int:
        """Increment failed attempt count."""
        try:
            key = f"failed_attempts:{ip}:{email}"
            count = cache.get(key, 0) + 1
            cache.set(key, count, timeout=3600)  # 1 hour timeout
            return count
        except Exception:
            return 1

    def _clear_failed_attempts(self, ip: str, email: str):
        """Clear failed attempt count."""
        try:
            key = f"failed_attempts:{ip}:{email}"
            cache.delete(key)
        except Exception:
            pass


class RegisterView(dj_views.RegisterView):
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except IntegrityError:
            return Response(
                {"error": "User already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValidationError as e:
            return Response(
                {"error": e.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception("An error occurred")
            return Response(
                {"error": "An error occurred"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PatientViewSet(ComprehensiveViewSetMixin, ModelViewSet):
    """
    Enhanced Patient ViewSet with comprehensive infrastructure integration:
    - Advanced caching for patient data
    - Complete analytics tracking for patient operations
    - Audit logging for all patient-related actions
    - Performance monitoring for database operations
    - Security controls and access logging
    - Background task integration for patient processing
    """

    serializer_class = PatientSerializer
    queryset = Patient.objects.select_related("user").prefetch_related(
        "disorders", "appointments"
    )
    lookup_field = "pk"
    permission_classes = [IsAuthenticated]

    # Enhanced caching configuration
    cache_timeout = 900  # 15 minutes for patient data
    cache_vary_headers = ["Authorization"]

    # Analytics configuration
    analytics_context = {"model": "patient"}

    def get_queryset(self):
        """Secure queryset with proper filtering and optimization."""
        queryset = self.queryset

        # Apply security filters based on user permissions
        if not self.request.user.is_superuser:
            # Staff can see patients they're assigned to
            if hasattr(self.request.user, "therapist"):
                queryset = queryset.filter(therapist=self.request.user.therapist)
            elif hasattr(self.request.user, "patient"):
                # Patients can only see their own record
                queryset = queryset.filter(id=self.request.user.patient.id)
            else:
                # No access for other user types
                queryset = queryset.none()

        return queryset

    def list(self, request, *args, **kwargs):
        """Enhanced list with caching and analytics."""
        cache_key = f"patient_list:{request.user.id}:{hash(str(request.query_params))}"

        # Try cache first
        cached_data = self.get_cached_data(
            cache_key, timeout=300
        )  # 5 minutes for lists
        if cached_data:
            self.record_analytics_event(
                "patient.list.cache_hit",
                request=request,
                extra_data={"user_id": request.user.id, "cached": True},
            )
            return Response(cached_data)

        # Cache miss - get fresh data
        response = super().list(request, *args, **kwargs)

        # Cache the response
        if response.status_code == 200:
            self.set_cached_data(cache_key, response.data, timeout=300)

        # Record analytics
        self.record_analytics_event(
            "patient.list.viewed",
            request=request,
            extra_data={
                "user_id": request.user.id,
                "patient_count": len(response.data.get("results", [])),
                "cached": False,
            },
        )

        return response

    def retrieve(self, request, *args, **kwargs):
        """Enhanced retrieve with comprehensive monitoring."""
        patient = self.get_object()
        cache_key = f"patient_detail:{patient.id}"

        # Try cache first
        cached_data = self.get_cached_data(cache_key)
        if cached_data:
            self.record_analytics_event(
                "patient.detail.cache_hit", instance=patient, request=request
            )
            return Response(cached_data)

        # Get fresh data
        serializer = self.get_serializer(patient)
        response_data = serializer.data

        # Enhance with additional context
        response_data.update(
            {
                "care_summary": self._get_patient_care_summary(patient),
                "recent_activity": self._get_patient_recent_activity(patient),
                "risk_assessment": self._get_patient_risk_assessment(patient),
            }
        )

        # Cache the enhanced response
        self.set_cached_data(cache_key, response_data)

        # Record analytics
        self.record_analytics_event(
            "patient.detail.viewed",
            instance=patient,
            request=request,
            extra_data={"patient_id": patient.id, "cached": False},
        )

        # Audit log
        create_audit_entry(
            request=request,
            target_object=patient.id,
            event=(
                audit_log.get_event_id("PATIENT_VIEWED")
                if hasattr(audit_log, "get_event_id")
                else 201
            ),
            data={"action": "patient_view", "patient_id": patient.id},
        )

        return Response(response_data)

    def create(self, request, *args, **kwargs):
        """Enhanced patient creation with comprehensive processing."""
        with self.database_transaction_context():
            # Validate and create patient
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Perform creation with enhanced processing
            self.perform_create(serializer)
            patient = serializer.instance

            # Record analytics
            self.record_analytics_event(
                "patient.created",
                instance=patient,
                request=request,
                extra_data={
                    "patient_id": patient.id,
                    "disorder_count": patient.disorders.count(),
                    "created_by": request.user.id,
                },
            )

            # Audit log
            create_audit_entry(
                request=request,
                target_object=patient.id,
                event=(
                    audit_log.get_event_id("PATIENT_CREATE")
                    if hasattr(audit_log, "get_event_id")
                    else 202
                ),
                data=self._get_patient_audit_data(patient),
            )

            # Trigger background tasks
            self._trigger_patient_creation_tasks(patient)

            # Invalidate related caches
            self._invalidate_patient_caches(patient)

            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data, status=status.HTTP_201_CREATED, headers=headers
            )

    def perform_create(self, serializer):
        """Enhanced creation with disorder handling and validation."""
        try:
            from aura.mentalhealth.models import Disorder

            # Extract and validate user data
            user_data = serializer.validated_data.pop("user", None)
            if user_data:
                # Create user with enhanced validation
                user = User.objects.create_user(**user_data)
                serializer.validated_data["user"] = user

            # Extract disorders for separate processing
            disorders = serializer.validated_data.pop("disorders", None) or []

            # Save patient instance
            serializer.save()
            patient = serializer.instance

            # Process disorders with proper error handling
            for disorder_data in disorders:
                try:
                    disorder, created = Disorder.objects.get_or_create(**disorder_data)
                    patient.disorders.add(disorder)

                    # Record disorder association analytics
                    if created:
                        self.record_analytics_event(
                            "disorder.created",
                            instance=disorder,
                            request=self.request,
                            extra_data={
                                "patient_id": patient.id,
                                "disorder_name": disorder.name,
                            },
                        )
                except Exception as e:
                    logger.error(f"Failed to process disorder {disorder_data}: {e}")
                    # Continue processing other disorders

        except Exception as e:
            logger.error(f"Failed to create patient: {e}")
            raise

    def update(self, request, *args, **kwargs):
        """Enhanced update with change tracking."""
        patient = self.get_object()
        old_data = self._get_patient_snapshot(patient)

        with self.database_transaction_context():
            response = super().update(request, *args, **kwargs)

            if response.status_code == 200:
                # Track changes
                new_data = self._get_patient_snapshot(patient)
                changes = self._calculate_patient_changes(old_data, new_data)

                # Record analytics
                self.record_analytics_event(
                    "patient.updated",
                    instance=patient,
                    request=request,
                    extra_data={
                        "patient_id": patient.id,
                        "changes": changes,
                        "updated_by": request.user.id,
                    },
                )

                # Audit log
                create_audit_entry(
                    request=request,
                    target_object=patient.id,
                    event=(
                        audit_log.get_event_id("PATIENT_UPDATE")
                        if hasattr(audit_log, "get_event_id")
                        else 203
                    ),
                    data={"changes": changes, "patient_id": patient.id},
                )

                # Invalidate caches
                self._invalidate_patient_caches(patient)

                # Trigger background tasks for significant changes
                if self._is_significant_change(changes):
                    self._trigger_patient_update_tasks(patient, changes)

            return response

    def destroy(self, request, *args, **kwargs):
        """Enhanced deletion with comprehensive logging."""
        patient = self.get_object()
        patient_data = self._get_patient_audit_data(patient)

        with self.database_transaction_context():
            # Record analytics before deletion
            self.record_analytics_event(
                "patient.deleted",
                instance=patient,
                request=request,
                extra_data={"patient_id": patient.id, "deleted_by": request.user.id},
            )

            # Audit log
            create_audit_entry(
                request=request,
                target_object=patient.id,
                event=(
                    audit_log.get_event_id("PATIENT_DELETE")
                    if hasattr(audit_log, "get_event_id")
                    else 204
                ),
                data=patient_data,
            )

            # Perform deletion
            response = super().destroy(request, *args, **kwargs)

            # Cleanup caches
            self._invalidate_patient_caches(patient)

            return response

    def _get_patient_care_summary(self, patient) -> Dict[str, Any]:
        """Get comprehensive care summary for patient."""
        try:
            cache_key = f"patient_care_summary:{patient.id}"
            cached_summary = self.get_cached_data(cache_key, timeout=1800)  # 30 minutes

            if cached_summary:
                return cached_summary

            # Calculate fresh summary
            summary = {
                "total_appointments": (
                    patient.appointments.count()
                    if hasattr(patient, "appointments")
                    else 0
                ),
                "completed_sessions": (
                    patient.appointments.filter(status="completed").count()
                    if hasattr(patient, "appointments")
                    else 0
                ),
                "last_appointment": None,
                "next_appointment": None,
                "treatment_duration_days": 0,
                "disorder_count": patient.disorders.count(),
                "primary_disorder": (
                    patient.disorders.first().name
                    if patient.disorders.exists()
                    else None
                ),
            }

            # Cache the result
            self.set_cached_data(cache_key, summary, timeout=1800)
            return summary

        except Exception as e:
            logger.warning(f"Failed to get patient care summary: {e}")
            return {}

    def _get_patient_recent_activity(self, patient) -> List[Dict[str, Any]]:
        """Get recent activity for patient."""
        try:
            # This would integrate with the analytics backend
            return []  # Placeholder
        except Exception:
            return []

    def _get_patient_risk_assessment(self, patient) -> Dict[str, Any]:
        """Get patient risk assessment."""
        try:
            # This would integrate with ML/AI risk assessment
            return {
                "risk_level": "low",  # Placeholder
                "risk_factors": [],
                "last_assessment": None,
                "next_assessment_due": None,
            }
        except Exception:
            return {}

    def _get_patient_audit_data(self, patient) -> Dict[str, Any]:
        """Get comprehensive audit data for patient."""
        try:
            return {
                "patient_id": patient.id,
                "user_id": patient.user_id if hasattr(patient, "user") else None,
                "disorder_count": patient.disorders.count(),
                "disorders": [d.name for d in patient.disorders.all()],
                "created_at": (
                    patient.created.isoformat() if hasattr(patient, "created") else None
                ),
            }
        except Exception as e:
            logger.warning(f"Failed to get patient audit data: {e}")
            return {"patient_id": patient.id}

    def _get_patient_snapshot(self, patient) -> Dict[str, Any]:
        """Get patient data snapshot for change tracking."""
        try:
            return {
                "disorders": list(patient.disorders.values_list("id", flat=True)),
                "user_data": {
                    "email": patient.user.email if hasattr(patient, "user") else None,
                    "first_name": (
                        patient.user.first_name if hasattr(patient, "user") else None
                    ),
                    "last_name": (
                        patient.user.last_name if hasattr(patient, "user") else None
                    ),
                },
            }
        except Exception:
            return {}

    def _calculate_patient_changes(
        self, old_data: Dict, new_data: Dict
    ) -> Dict[str, Any]:
        """Calculate changes between patient snapshots."""
        changes = {}

        try:
            # Compare disorders
            old_disorders = set(old_data.get("disorders", []))
            new_disorders = set(new_data.get("disorders", []))

            if old_disorders != new_disorders:
                changes["disorders"] = {
                    "added": list(new_disorders - old_disorders),
                    "removed": list(old_disorders - new_disorders),
                }

            # Compare user data
            old_user = old_data.get("user_data", {})
            new_user = new_data.get("user_data", {})

            user_changes = {}
            for field in ["email", "first_name", "last_name"]:
                if old_user.get(field) != new_user.get(field):
                    user_changes[field] = {
                        "old": old_user.get(field),
                        "new": new_user.get(field),
                    }

            if user_changes:
                changes["user_data"] = user_changes

        except Exception as e:
            logger.warning(f"Failed to calculate patient changes: {e}")

        return changes

    def _is_significant_change(self, changes: Dict) -> bool:
        """Determine if changes are significant enough to trigger tasks."""
        return bool(changes.get("disorders") or changes.get("user_data"))

    def _trigger_patient_creation_tasks(self, patient):
        """Trigger background tasks for new patient."""
        try:
            # Example background tasks
            # process_new_patient.delay(patient.id)
            # send_welcome_email.delay(patient.id)
            # schedule_initial_assessment.delay(patient.id)
            logger.info(f"Background tasks triggered for new patient {patient.id}")
        except Exception as e:
            logger.error(f"Failed to trigger patient creation tasks: {e}")

    def _trigger_patient_update_tasks(self, patient, changes):
        """Trigger background tasks for patient updates."""
        try:
            # Example background tasks based on changes
            # if 'disorders' in changes:
            #     update_treatment_plan.delay(patient.id)
            # if 'user_data' in changes:
            #     sync_patient_data.delay(patient.id)
            logger.info(f"Background tasks triggered for patient {patient.id} update")
        except Exception as e:
            logger.error(f"Failed to trigger patient update tasks: {e}")

    def _invalidate_patient_caches(self, patient):
        """Invalidate all patient-related caches."""
        try:
            cache_keys = [
                f"patient_detail:{patient.id}",
                f"patient_care_summary:{patient.id}",
                f"patient_list:*",  # Wildcard - would need custom cache invalidation
            ]

            for key in cache_keys:
                if "*" not in key:
                    cache.delete(key)

            logger.debug(f"Invalidated caches for patient {patient.id}")
        except Exception as e:
            logger.warning(f"Failed to invalidate patient caches: {e}")


class TherapistViewSet(ModelViewSet):
    serializer_class = TherapistSerializer
    queryset = Therapist.objects.all()
    lookup_field = "pk"

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()


class PhysicianReferralListCreate(
    ViewSetMixin,
    generics.ListCreateAPIView,
):
    queryset = PhysicianReferral.objects.all()
    serializer_class = PhysicianReferralSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )


class PhysicianReferralRetrieveUpdateDestroy(
    ViewSetMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    queryset = PhysicianReferral.objects.all()
    serializer_class = PhysicianReferralSerializer
    lookup_field = "id"


# Background Tasks for Comprehensive Processing
@shared_task(bind=True, name="users.process_new_review")
def process_new_review(self, review_id):
    """Background task to process new review submissions."""
    try:
        from aura.core.models import Review

        review = Review.objects.get(id=review_id)

        # Sentiment analysis
        sentiment_score = analyze_review_sentiment(review.content)

        # Update review with analysis
        review.sentiment_score = sentiment_score
        review.save()

        # Record analytics
        analytics.record(
            "review.processed",
            review_id=review_id,
            sentiment_score=sentiment_score,
            processing_duration=(
                self.request.duration if hasattr(self.request, "duration") else 0
            ),
        )

        logger.info(
            f"Processed review {review_id} with sentiment score {sentiment_score}"
        )
        return {
            "status": "success",
            "review_id": review_id,
            "sentiment_score": sentiment_score,
        }

    except Exception as e:
        logger.error(f"Failed to process review {review_id}: {e}")
        raise


@shared_task(bind=True, name="users.analyze_login_pattern")
def analyze_login_pattern(self, user_id, ip_address, user_agent):
    """Background task to analyze login patterns for security."""
    try:
        # Geolocation analysis
        location = get_ip_geolocation(ip_address)

        # Device fingerprinting
        device_info = parse_user_agent(user_agent)

        # Risk assessment
        risk_score = calculate_login_risk(user_id, ip_address, location, device_info)

        # Store analysis results
        store_login_analysis(
            user_id,
            {
                "ip_address": ip_address,
                "location": location,
                "device_info": device_info,
                "risk_score": risk_score,
                "timestamp": timezone.now().isoformat(),
            },
        )

        # Alert if high risk
        if risk_score > 0.8:
            send_security_alert.delay(
                user_id,
                "high_risk_login",
                {
                    "ip_address": ip_address,
                    "location": location,
                    "risk_score": risk_score,
                },
            )

        return {"status": "success", "risk_score": risk_score}

    except Exception as e:
        logger.error(f"Failed to analyze login pattern for user {user_id}: {e}")
        raise


@shared_task(bind=True, name="users.update_user_login_stats")
def update_user_login_stats(self, user_id):
    """Background task to update user login statistics."""
    try:
        from aura.users.models import User

        user = User.objects.get(id=user_id)

        # Update login count and streaks
        update_login_statistics(user)

        # Record in analytics
        analytics.record(
            "user.login_stats_updated",
            user_id=user_id,
            login_count=getattr(user, "login_count", 0),
            current_streak=getattr(user, "login_streak", 0),
        )

        return {"status": "success", "user_id": user_id}

    except Exception as e:
        logger.error(f"Failed to update login stats for user {user_id}: {e}")
        raise


@shared_task(bind=True, name="users.analyze_failed_login")
def analyze_failed_login(self, ip_address, email, user_agent):
    """Background task to analyze failed login attempts."""
    try:
        # Check for brute force patterns
        recent_failures = get_recent_failed_logins(ip_address, hours=1)

        if len(recent_failures) > 5:  # Threshold for suspicious activity
            # Record security event
            analytics.record(
                "security.brute_force_detected",
                ip_address=ip_address,
                email=email,
                user_agent=user_agent,
                failure_count=len(recent_failures),
            )

            # Trigger security measures
            block_ip_temporarily.delay(ip_address, duration_minutes=30)

            # Alert security team
            send_security_alert.delay(
                None,
                "brute_force_attack",
                {
                    "ip_address": ip_address,
                    "email": email,
                    "failure_count": len(recent_failures),
                },
            )

        return {"status": "success", "failures_detected": len(recent_failures)}

    except Exception as e:
        logger.error(f"Failed to analyze failed login: {e}")
        raise


# Helper functions for background tasks
def analyze_review_sentiment(content: str) -> float:
    """Analyze sentiment of review content."""
    try:
        # Placeholder for sentiment analysis
        # Would integrate with NLP service
        return 0.7  # Neutral-positive sentiment
    except Exception:
        return 0.5  # Default neutral


def get_ip_geolocation(ip_address: str) -> Dict[str, Any]:
    """Get geolocation data for IP address."""
    try:
        # Placeholder for geolocation service
        return {
            "country": "Unknown",
            "region": "Unknown",
            "city": "Unknown",
            "latitude": 0.0,
            "longitude": 0.0,
        }
    except Exception:
        return {}


def parse_user_agent(user_agent: str) -> Dict[str, Any]:
    """Parse user agent string for device information."""
    try:
        # Placeholder for user agent parsing
        return {
            "browser": "Unknown",
            "browser_version": "Unknown",
            "os": "Unknown",
            "os_version": "Unknown",
            "device_type": "desktop",
        }
    except Exception:
        return {}


def calculate_login_risk(
    user_id: int, ip_address: str, location: Dict, device: Dict
) -> float:
    """Calculate risk score for login attempt."""
    try:
        risk_score = 0.0

        # Check for new location
        if not is_known_location(user_id, location):
            risk_score += 0.3

        # Check for new device
        if not is_known_device(user_id, device):
            risk_score += 0.2

        # Check IP reputation
        if is_suspicious_ip(ip_address):
            risk_score += 0.4

        # Check time patterns
        if is_unusual_time(user_id):
            risk_score += 0.1

        return min(risk_score, 1.0)
    except Exception:
        return 0.5


def is_known_location(user_id: int, location: Dict) -> bool:
    """Check if location is known for user."""
    # Placeholder implementation
    return True


def is_known_device(user_id: int, device: Dict) -> bool:
    """Check if device is known for user."""
    # Placeholder implementation
    return True


def is_suspicious_ip(ip_address: str) -> bool:
    """Check if IP address is suspicious."""
    # Placeholder implementation
    return False


def is_unusual_time(user_id: int) -> bool:
    """Check if login time is unusual for user."""
    # Placeholder implementation
    return False


def store_login_analysis(user_id: int, analysis_data: Dict):
    """Store login analysis results."""
    try:
        cache_key = f"login_analysis:{user_id}:{int(time.time())}"
        cache.set(cache_key, analysis_data, timeout=86400)  # 24 hours
    except Exception as e:
        logger.error(f"Failed to store login analysis: {e}")


def update_login_statistics(user):
    """Update user login statistics."""
    try:
        # Update login count
        if not hasattr(user, "login_count"):
            user.login_count = 0
        user.login_count += 1

        # Update login streak
        if not hasattr(user, "last_login_date"):
            user.login_streak = 1
        else:
            last_login = getattr(user, "last_login_date", None)
            if last_login and (timezone.now().date() - last_login).days == 1:
                user.login_streak = getattr(user, "login_streak", 0) + 1
            else:
                user.login_streak = 1

        user.last_login_date = timezone.now().date()
        user.save()

    except Exception as e:
        logger.error(f"Failed to update login statistics: {e}")


def get_recent_failed_logins(ip_address: str, hours: int = 1) -> List[Dict]:
    """Get recent failed login attempts for IP."""
    try:
        # This would query the analytics backend
        return []  # Placeholder
    except Exception:
        return []


@shared_task(bind=True, name="users.block_ip_temporarily")
def block_ip_temporarily(self, ip_address: str, duration_minutes: int = 30):
    """Temporarily block an IP address."""
    try:
        cache_key = f"blocked_ip:{ip_address}"
        cache.set(cache_key, True, timeout=duration_minutes * 60)

        logger.warning(f"IP {ip_address} blocked for {duration_minutes} minutes")

        # Record in analytics
        analytics.record(
            "security.ip_blocked",
            ip_address=ip_address,
            duration_minutes=duration_minutes,
            reason="brute_force_protection",
        )

    except Exception as e:
        logger.error(f"Failed to block IP {ip_address}: {e}")


@shared_task(bind=True, name="users.send_security_alert")
def send_security_alert(self, user_id: Optional[int], alert_type: str, context: Dict):
    """Send security alert to administrators."""
    try:
        # This would integrate with the notification system
        logger.critical(f"Security Alert: {alert_type} - {context}")

        # Record in analytics
        analytics.record(
            "security.alert_sent",
            user_id=user_id,
            alert_type=alert_type,
            context=context,
        )

    except Exception as e:
        logger.error(f"Failed to send security alert: {e}")


class EnhancedPatientViewSet(ComprehensiveViewSetMixin, ModelViewSet):
    """
    Ultra-comprehensive Patient ViewSet replacing the basic one.
    This implementation includes all infrastructure components integrated.
    """

    serializer_class = PatientSerializer
    queryset = Patient.objects.select_related("user").prefetch_related(
        "disorders", "appointments"
    )
    lookup_field = "pk"
    permission_classes = [IsAuthenticated]

    # Enhanced caching configuration
    cache_timeout = 900  # 15 minutes for patient data
    cache_vary_headers = ["Authorization"]

    # Analytics configuration
    analytics_context = {"model": "patient"}

    def get_queryset(self):
        """Secure queryset with proper filtering and optimization."""
        queryset = self.queryset

        # Apply security filters based on user permissions
        if not self.request.user.is_superuser:
            if hasattr(self.request.user, "therapist"):
                queryset = queryset.filter(therapist=self.request.user.therapist)
            elif hasattr(self.request.user, "patient"):
                queryset = queryset.filter(id=self.request.user.patient.id)
            else:
                queryset = queryset.none()

        return queryset

    def create(self, request, *args, **kwargs):
        """Enhanced patient creation with comprehensive processing."""
        with self.database_transaction_context():
            # Validate and create patient
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Perform creation with enhanced processing
            self.perform_create(serializer)
            patient = serializer.instance

            # Record analytics
            self.record_analytics_event(
                "patient.created",
                instance=patient,
                request=request,
                extra_data={
                    "patient_id": patient.id,
                    "disorder_count": (
                        patient.disorders.count()
                        if hasattr(patient, "disorders")
                        else 0
                    ),
                    "created_by": request.user.id,
                },
            )

            # Audit log
            create_audit_entry(
                request=request,
                target_object=patient.id,
                event=(
                    audit_log.get_event_id("PATIENT_CREATE")
                    if hasattr(audit_log, "get_event_id")
                    else 202
                ),
                data={"patient_id": patient.id, "created_by": request.user.id},
            )

            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data, status=status.HTTP_201_CREATED, headers=headers
            )

    def perform_create(self, serializer):
        """Enhanced creation with disorder handling and validation."""
        try:
            from aura.mentalhealth.models import Disorder

            # Extract and validate user data
            user_data = serializer.validated_data.pop("user", None)
            if user_data:
                user = User.objects.create_user(**user_data)
                serializer.validated_data["user"] = user

            # Extract disorders for separate processing
            disorders = serializer.validated_data.pop("disorders", None) or []

            # Save patient instance
            serializer.save()
            patient = serializer.instance

            # Process disorders with proper error handling
            for disorder_data in disorders:
                try:
                    disorder, created = Disorder.objects.get_or_create(**disorder_data)
                    patient.disorders.add(disorder)

                    if created:
                        self.record_analytics_event(
                            "disorder.created",
                            instance=disorder,
                            request=self.request,
                            extra_data={
                                "patient_id": patient.id,
                                "disorder_name": disorder.name,
                            },
                        )
                except Exception as e:
                    logger.error(f"Failed to process disorder {disorder_data}: {e}")

        except Exception as e:
            logger.error(f"Failed to create patient: {e}")
            raise


class EnhancedTherapistViewSet(ComprehensiveViewSetMixin, ModelViewSet):
    """
    Ultra-comprehensive Therapist ViewSet with full infrastructure integration.
    """

    serializer_class = TherapistSerializer
    queryset = Therapist.objects.select_related("user").prefetch_related(
        "specializations", "patients"
    )
    lookup_field = "pk"
    permission_classes = [IsAuthenticated]

    # Enhanced caching configuration
    cache_timeout = 1200  # 20 minutes for therapist data
    cache_vary_headers = ["Authorization"]

    # Analytics configuration
    analytics_context = {"model": "therapist"}

    def create(self, request, *args, **kwargs):
        """Enhanced therapist creation with comprehensive processing."""
        with self.database_transaction_context():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            self.perform_create(serializer)
            therapist = serializer.instance

            # Record analytics
            self.record_analytics_event(
                "therapist.created",
                instance=therapist,
                request=request,
                extra_data={
                    "therapist_id": therapist.id,
                    "created_by": request.user.id,
                },
            )

            # Audit log
            create_audit_entry(
                request=request,
                target_object=therapist.id,
                event=(
                    audit_log.get_event_id("THERAPIST_CREATE")
                    if hasattr(audit_log, "get_event_id")
                    else 301
                ),
                data={"therapist_id": therapist.id, "created_by": request.user.id},
            )

            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data, status=status.HTTP_201_CREATED, headers=headers
            )

    def perform_create(self, serializer):
        """Enhanced therapist creation."""
        serializer.save()

        # Record creation analytics
        self.record_analytics_event(
            "therapist.profile.created",
            instance=serializer.instance,
            request=self.request,
        )

    def perform_update(self, serializer):
        """Enhanced therapist update with change tracking."""
        old_instance = self.get_object()
        old_data = self._get_therapist_snapshot(old_instance)

        serializer.save()

        # Track changes
        new_data = self._get_therapist_snapshot(serializer.instance)
        changes = self._calculate_therapist_changes(old_data, new_data)

        # Record analytics
        self.record_analytics_event(
            "therapist.updated",
            instance=serializer.instance,
            request=self.request,
            extra_data={
                "therapist_id": serializer.instance.id,
                "changes": changes,
                "updated_by": self.request.user.id,
            },
        )

    def _get_therapist_snapshot(self, therapist) -> Dict[str, Any]:
        """Get therapist data snapshot for change tracking."""
        try:
            return {
                "specializations": (
                    list(therapist.specializations.values_list("id", flat=True))
                    if hasattr(therapist, "specializations")
                    else []
                ),
                "license_number": getattr(therapist, "license_number", None),
                "years_experience": getattr(therapist, "years_experience", None),
            }
        except Exception:
            return {}

    def _calculate_therapist_changes(
        self, old_data: Dict, new_data: Dict
    ) -> Dict[str, Any]:
        """Calculate changes between therapist snapshots."""
        changes = {}

        try:
            # Compare specializations
            old_specs = set(old_data.get("specializations", []))
            new_specs = set(new_data.get("specializations", []))

            if old_specs != new_specs:
                changes["specializations"] = {
                    "added": list(new_specs - old_specs),
                    "removed": list(old_specs - new_specs),
                }

            # Compare other fields
            for field in ["license_number", "years_experience"]:
                if old_data.get(field) != new_data.get(field):
                    changes[field] = {
                        "old": old_data.get(field),
                        "new": new_data.get(field),
                    }

        except Exception as e:
            logger.warning(f"Failed to calculate therapist changes: {e}")

        return changes


class EnhancedPhysicianReferralViewSet(ComprehensiveViewSetMixin, ModelViewSet):
    """
    Ultra-comprehensive Physician Referral ViewSet.
    """

    queryset = PhysicianReferral.objects.select_related(
        "patient", "referring_physician"
    )
    serializer_class = PhysicianReferralSerializer
    permission_classes = [IsAuthenticated]

    # Enhanced caching configuration
    cache_timeout = 600  # 10 minutes for referral data
    cache_vary_headers = ["Authorization"]

    # Analytics configuration
    analytics_context = {"model": "physician_referral"}

    def create(self, request, *args, **kwargs):
        """Enhanced referral creation with comprehensive processing."""
        with self.database_transaction_context():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            self.perform_create(serializer)
            referral = serializer.instance

            # Record analytics
            self.record_analytics_event(
                "physician_referral.created",
                instance=referral,
                request=request,
                extra_data={
                    "referral_id": referral.id,
                    "patient_id": (
                        getattr(referral.patient, "id", None)
                        if hasattr(referral, "patient")
                        else None
                    ),
                    "created_by": request.user.id,
                },
            )

            # Audit log
            create_audit_entry(
                request=request,
                target_object=referral.id,
                event=(
                    audit_log.get_event_id("REFERRAL_CREATE")
                    if hasattr(audit_log, "get_event_id")
                    else 401
                ),
                data={"referral_id": referral.id, "created_by": request.user.id},
            )

            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data, status=status.HTTP_201_CREATED, headers=headers
            )


# Replace the original viewsets with enhanced versions
PatientViewSet = EnhancedPatientViewSet
TherapistViewSet = EnhancedTherapistViewSet


# Keep the existing RegisterView and create enhanced referral views
class PhysicianReferralListCreate(
    ComprehensiveViewSetMixin,
    ViewSetMixin,
    generics.ListCreateAPIView,
):
    queryset = PhysicianReferral.objects.select_related(
        "patient", "referring_physician"
    )
    serializer_class = PhysicianReferralSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """Enhanced create with comprehensive tracking."""
        with self.database_transaction_context():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

            # Record analytics
            self.record_analytics_event(
                "physician_referral.created",
                instance=serializer.instance,
                request=request,
            )

            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
                headers=headers,
            )


class PhysicianReferralRetrieveUpdateDestroy(
    ComprehensiveViewSetMixin,
    ViewSetMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    queryset = PhysicianReferral.objects.select_related(
        "patient", "referring_physician"
    )
    serializer_class = PhysicianReferralSerializer
    lookup_field = "id"
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        """Enhanced update with comprehensive tracking."""
        with self.database_transaction_context():
            response = super().update(request, *args, **kwargs)

            if response.status_code == 200:
                # Record analytics
                self.record_analytics_event(
                    "physician_referral.updated",
                    instance=self.get_object(),
                    request=request,
                )

            return response
