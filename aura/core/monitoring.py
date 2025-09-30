"""
Comprehensive monitoring and logging system for the Aura platform.
Ready for ELK stack integration.
"""

import logging
import threading
import time
import traceback
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from .models import AuditLog
from .models import SystemMetrics

User = get_user_model()
logger = logging.getLogger(__name__)

# Thread local storage for request context
_request_context = threading.local()


class RequestContextMiddleware:
    """Middleware to store request context for logging"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Store request context
        _request_context.request = request
        _request_context.start_time = time.time()

        response = self.get_response(request)

        # Log request metrics
        duration = time.time() - _request_context.start_time
        self._log_request_metrics(request, response, duration)

        # Clear context
        _request_context.request = None
        _request_context.start_time = None

        return response

    def _log_request_metrics(self, request: HttpRequest, response, duration: float):
        """Log request performance metrics"""
        try:
            SystemMetricsLogger.log_request_metric(
                method=request.method,
                path=request.path,
                status_code=response.status_code,
                duration_ms=duration * 1000,
                user_id=str(request.user.id) if request.user.is_authenticated else None,
            )
        except Exception as e:
            logger.error(f"Failed to log request metrics: {e}")


class AuditLogger:
    """Comprehensive audit logging for compliance and security"""

    @staticmethod
    def log_user_action(
        user: User,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Log user actions for audit trail"""
        try:
            request = getattr(_request_context, "request", None)
            ip_address = "127.0.0.1"
            user_agent = ""
            session_key = ""

            if request:
                ip_address = get_client_ip(request)
                user_agent = request.headers.get("user-agent", "")[:500]
                session_key = request.session.session_key or ""

            with transaction.atomic():
                AuditLog.objects.create(
                    user=user,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    session_key=session_key,
                    details=details or {},
                )
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")

    @staticmethod
    def log_authentication_event(email: str, action: str, success: bool, details: dict[str, Any] | None = None):
        """Log authentication events"""
        try:
            request = getattr(_request_context, "request", None)
            ip_address = "127.0.0.1"
            user_agent = ""

            if request:
                ip_address = get_client_ip(request)
                user_agent = request.headers.get("user-agent", "")[:500]

            audit_details = {"email": email, "success": success, "timestamp": timezone.now().isoformat()}
            if details:
                audit_details.update(details)

            # For failed logins, don't link to user object for security
            user = None
            if success:
                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    pass

            AuditLog.objects.create(
                user=user,
                action="login" if success else "failed_login",
                resource_type="authentication",
                ip_address=ip_address,
                user_agent=user_agent,
                details=audit_details,
            )
        except Exception as e:
            logger.error(f"Failed to log authentication event: {e}")

    @staticmethod
    def log_profile_update(user: User, profile_type: str, changed_fields: list):
        """Log profile updates with field-level tracking"""
        AuditLogger.log_user_action(
            user=user,
            action="profile_update",
            resource_type=f"{profile_type}_profile",
            resource_id=str(user.id),
            details={
                "profile_type": profile_type,
                "changed_fields": changed_fields,
                "timestamp": timezone.now().isoformat(),
            },
        )

    @staticmethod
    def log_appointment_action(user: User, action: str, appointment_id: str, details: dict[str, Any]):
        """Log appointment-related actions"""
        AuditLogger.log_user_action(
            user=user,
            action=f"appointment_{action}",
            resource_type="appointment",
            resource_id=appointment_id,
            details=details,
        )

    @staticmethod
    def log_matching_action(user: User, action: str, details: dict[str, Any]):
        """Log matching algorithm actions"""
        AuditLogger.log_user_action(user=user, action=f"match_{action}", resource_type="matching", details=details)


class SystemMetricsLogger:
    """System performance and health metrics logging"""

    @staticmethod
    def log_request_metric(method: str, path: str, status_code: int, duration_ms: float, user_id: str | None = None):
        """Log HTTP request metrics"""
        try:
            SystemMetrics.objects.create(
                metric_name="http_request_duration",
                metric_value=duration_ms,
                metric_unit="milliseconds",
                metadata={"method": method, "path": path, "status_code": status_code, "user_id": user_id},
            )

            # Also log status code metrics
            SystemMetrics.objects.create(
                metric_name="http_response_status",
                metric_value=status_code,
                metric_unit="status_code",
                metadata={"method": method, "path": path, "duration_ms": duration_ms},
            )
        except Exception as e:
            logger.error(f"Failed to log request metrics: {e}")

    @staticmethod
    def log_database_query_metric(query_count: int, duration_ms: float):
        """Log database query performance"""
        try:
            SystemMetrics.objects.create(
                metric_name="database_query_count", metric_value=query_count, metric_unit="queries"
            )

            SystemMetrics.objects.create(
                metric_name="database_query_duration", metric_value=duration_ms, metric_unit="milliseconds"
            )
        except Exception:
            pass  # Don't log database errors when logging database metrics

    @staticmethod
    def log_matching_performance(duration_ms: float, match_count: int):
        """Log matching algorithm performance"""
        SystemMetrics.objects.create(
            metric_name="matching_duration",
            metric_value=duration_ms,
            metric_unit="milliseconds",
            metadata={"match_count": match_count},
        )

    @staticmethod
    def log_user_registration():
        """Log user registration event"""
        SystemMetrics.objects.create(metric_name="user_registrations", metric_value=1, metric_unit="registrations")

    @staticmethod
    def log_appointment_booking():
        """Log appointment booking event"""
        SystemMetrics.objects.create(metric_name="appointments_booked", metric_value=1, metric_unit="appointments")


class SecurityLogger:
    """Security-focused logging for threat detection"""

    @staticmethod
    def log_suspicious_activity(user: User | None, activity_type: str, severity: str, details: dict[str, Any]):
        """Log suspicious activities for security analysis"""
        try:
            request = getattr(_request_context, "request", None)
            ip_address = "127.0.0.1"
            user_agent = ""

            if request:
                ip_address = get_client_ip(request)
                user_agent = request.headers.get("user-agent", "")[:500]

            security_details = {
                "activity_type": activity_type,
                "severity": severity,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "timestamp": timezone.now().isoformat(),
            }
            security_details.update(details)

            AuditLog.objects.create(
                user=user,
                action="security_event",
                resource_type="security",
                ip_address=ip_address,
                user_agent=user_agent,
                details=security_details,
            )

            # Also log to application logger for immediate alerting
            logger.warning(
                f"Security Event [{severity}]: {activity_type}",
                extra={"user_id": str(user.id) if user else None, "ip_address": ip_address, "details": details},
            )
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")

    @staticmethod
    def log_rate_limit_exceeded(user: User | None, endpoint: str, limit: str):
        """Log rate limit violations"""
        SecurityLogger.log_suspicious_activity(
            user=user,
            activity_type="rate_limit_exceeded",
            severity="medium",
            details={"endpoint": endpoint, "limit": limit},
        )

    @staticmethod
    def log_invalid_token_usage(user: User | None, token_type: str):
        """Log invalid token usage attempts"""
        SecurityLogger.log_suspicious_activity(
            user=user, activity_type="invalid_token_usage", severity="high", details={"token_type": token_type}
        )


class StructuredLogger:
    """Structured logging for ELK stack integration"""

    @staticmethod
    def get_structured_logger(name: str) -> logging.Logger:
        """Get a structured logger configured for ELK stack"""
        logger = logging.getLogger(name)
        return logger

    @staticmethod
    def log_business_event(event_type: str, user_id: str | None = None, **kwargs):
        """Log business events in structured format"""
        logger = StructuredLogger.get_structured_logger("aura.business")

        event_data = {"event_type": event_type, "timestamp": timezone.now().isoformat(), "user_id": user_id, **kwargs}

        logger.info(f"Business Event: {event_type}", extra={"structured_data": event_data})

    @staticmethod
    def log_error(
        error_type: str, message: str, exception: Exception | None = None, user_id: str | None = None, **kwargs
    ):
        """Log errors in structured format"""
        logger = StructuredLogger.get_structured_logger("aura.errors")

        error_data = {
            "error_type": error_type,
            "message": message,
            "timestamp": timezone.now().isoformat(),
            "user_id": user_id,
            **kwargs,
        }

        if exception:
            error_data["exception"] = str(exception)
            error_data["traceback"] = traceback.format_exc()

        logger.error(f"Error: {error_type} - {message}", extra={"structured_data": error_data})


def get_client_ip(request: HttpRequest) -> str:
    """Get client IP address from request"""
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "127.0.0.1")
    return ip


# Decorator for logging function calls
def log_function_call(action: str, resource_type: str):
    """Decorator to automatically log function calls"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            request = getattr(_request_context, "request", None)
            user = request.user if request and request.user.is_authenticated else None

            start_time = time.time()
            try:
                result = func(*args, **kwargs)

                if user:
                    AuditLogger.log_user_action(
                        user=user,
                        action=action,
                        resource_type=resource_type,
                        details={
                            "function": func.__name__,
                            "duration_ms": (time.time() - start_time) * 1000,
                            "success": True,
                        },
                    )

                return result
            except Exception as e:
                if user:
                    AuditLogger.log_user_action(
                        user=user,
                        action=f"{action}_failed",
                        resource_type=resource_type,
                        details={
                            "function": func.__name__,
                            "duration_ms": (time.time() - start_time) * 1000,
                            "error": str(e),
                            "success": False,
                        },
                    )
                raise

        return wrapper

    return decorator
