import hashlib
import logging
import time
import uuid

import psutil
from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest

from aura.core.request_middleware import get_request


class RequestContextFilter(logging.Filter):
    """
    Advanced request context filter that enriches log records with comprehensive
    request metadata, user context, performance metrics, and security information.

    This filter implements enterprise-grade logging practices including:
    - Correlation ID propagation
    - User context injection
    - Performance metrics tracking
    - Security context logging
    - Geographic and device information
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.process = psutil.Process()

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Enriches log records with comprehensive context information.
        """
        request: WSGIRequest | None = get_request()

        # Generate or retrieve correlation ID
        correlation_id = self._get_correlation_id(request)
        record.correlation_id = correlation_id
        record.request_id = correlation_id  # Backward compatibility

        if request:
            # Request metadata
            record.method = getattr(request, "method", "UNKNOWN")
            record.path = getattr(request, "path", "UNKNOWN")
            record.query_string = (
                request.GET.urlencode() if hasattr(request, "GET") else ""
            )
            record.content_type = (
                request.content_type if hasattr(request, "content_type") else ""
            )

            # User context
            self._add_user_context(record, request)

            # Security context
            self._add_security_context(record, request)

            # Performance context
            self._add_performance_context(record, request)

            # Geographic context
            self._add_geographic_context(record, request)

        else:
            # Out-of-request context (Celery, management commands, etc.)
            self._add_system_context(record)

        # System metrics
        self._add_system_metrics(record)

        # Environment context
        record.environment = getattr(settings, "ENVIRONMENT", "unknown")
        record.service_name = getattr(settings, "SERVICE_NAME", "aura")
        record.version = getattr(settings, "VERSION", "unknown")

        return True

    def _get_correlation_id(self, request: WSGIRequest | None) -> str:
        """
        Generates or retrieves correlation ID with proper propagation.
        """
        if request:
            # Check for existing correlation ID in headers (from upstream services)
            correlation_id = (
                request.headers.get("x-correlation-id")
                or request.headers.get("x-request-id")
                or request.headers.get("x-trace-id")
            )

            if not correlation_id:
                # Generate new correlation ID if not present
                if not hasattr(request, "correlation_id"):
                    request.correlation_id = uuid.uuid4().hex
                correlation_id = request.correlation_id
            else:
                # Store for later use
                request.correlation_id = correlation_id

            return correlation_id
        else:
            return f"system-{uuid.uuid4().hex[:8]}"

    def _add_user_context(
        self,
        record: logging.LogRecord,
        request: WSGIRequest,
    ) -> None:
        """
        Adds comprehensive user context to log records.
        """
        if hasattr(request, "user") and request.user.is_authenticated:
            record.user_id = str(request.user.pk)
            record.username = getattr(request.user, "username", "") or getattr(
                request.user,
                "email",
                "",
            )
            record.user_type = getattr(request.user, "user_type", "unknown")
            record.is_staff = getattr(request.user, "is_staff", False)
            record.is_superuser = getattr(request.user, "is_superuser", False)
        else:
            record.user_id = "anonymous"
            record.username = "anonymous"
            record.user_type = "anonymous"
            record.is_staff = False
            record.is_superuser = False

        # Session context
        if hasattr(request, "session"):
            record.session_key = request.session.session_key or "no-session"
            record.session_age = time.time() - request.session.get(
                "_session_init_timestamp_",
                time.time(),
            )
        else:
            record.session_key = "no-session"
            record.session_age = 0

    def _add_security_context(
        self,
        record: logging.LogRecord,
        request: WSGIRequest,
    ) -> None:
        """
        Adds security-related context for threat detection and compliance.
        """
        # IP Address information
        record.client_ip = self._get_client_ip(request)
        record.forwarded_for = request.headers.get("x-forwarded-for", "")
        record.real_ip = request.headers.get("x-real-ip", "")

        # User Agent and Device information
        user_agent = request.headers.get("user-agent", "")
        record.user_agent = user_agent
        record.user_agent_hash = hashlib.md5(user_agent.encode()).hexdigest()[:16]

        # Security headers
        record.referer = request.headers.get("referer", "")
        record.origin = request.headers.get("origin", "")
        record.host = request.headers.get("host", "")

        # Request size (for potential DoS detection)
        content_length_str = request.headers.get("content-length", "0")
        try:
            record.content_length = int(content_length_str) if content_length_str else 0
        except (ValueError, TypeError):
            record.content_length = 0

        # Authentication method
        record.auth_method = self._detect_auth_method(request)

    def _add_performance_context(
        self,
        record: logging.LogRecord,
        request: WSGIRequest,
    ) -> None:
        """
        Adds performance metrics for monitoring and optimization.
        """
        # Request timing
        if hasattr(request, "_request_start_time"):
            record.request_duration = time.time() - request._request_start_time
        else:
            request._request_start_time = time.time()
            record.request_duration = 0

        # Database query tracking
        if hasattr(request, "_db_queries_count"):
            record.db_queries = request._db_queries_count
        else:
            record.db_queries = 0

        # Cache hit/miss tracking
        record.cache_hits = getattr(request, "_cache_hits", 0)
        record.cache_misses = getattr(request, "_cache_misses", 0)

    def _add_geographic_context(
        self,
        record: logging.LogRecord,
        request: WSGIRequest,
    ) -> None:
        """
        Adds geographic context using GeoIP data.
        """
        client_ip = self._get_client_ip(request)

        # Use Django's GeoIP2 if configured
        try:
            from django.contrib.gis.geoip2 import GeoIP2

            g = GeoIP2()
            geo_data = g.city(client_ip)
            record.country_code = geo_data.get("country_code", "")
            record.country_name = geo_data.get("country_name", "")
            record.city = geo_data.get("city", "")
            record.region = geo_data.get("region", "")
            record.timezone = geo_data.get("time_zone", "")
        except Exception:
            # Fallback if GeoIP is not configured
            record.country_code = ""
            record.country_name = ""
            record.city = ""
            record.region = ""
            record.timezone = ""

    def _add_system_context(self, record: logging.LogRecord) -> None:
        """
        Adds system context for out-of-request logging (Celery, management commands).
        """
        record.method = "SYSTEM"
        record.path = "SYSTEM"
        record.query_string = ""
        record.content_type = ""
        record.user_id = "system"
        record.username = "system"
        record.user_type = "system"
        record.is_staff = False
        record.is_superuser = False
        record.session_key = "system"
        record.session_age = 0
        record.client_ip = "127.0.0.1"
        record.user_agent = "system"
        record.user_agent_hash = "system"
        record.auth_method = "system"

    def _add_system_metrics(self, record: logging.LogRecord) -> None:
        """
        Adds system performance metrics.
        """
        try:
            # Memory usage
            memory_info = self.process.memory_info()
            record.memory_rss = memory_info.rss
            record.memory_vms = memory_info.vms
            record.memory_percent = self.process.memory_percent()

            # CPU usage
            record.cpu_percent = self.process.cpu_percent()

            # System load
            record.system_load = (
                psutil.getloadavg()[0] if hasattr(psutil, "getloadavg") else 0
            )

        except Exception:
            # Fallback values if psutil fails
            record.memory_rss = 0
            record.memory_vms = 0
            record.memory_percent = 0
            record.cpu_percent = 0
            record.system_load = 0

    def _get_client_ip(self, request: WSGIRequest) -> str:
        """
        Extracts the real client IP address from request headers.
        """
        # Check various headers for the real IP
        ip_headers = [
            "HTTP_X_FORWARDED_FOR",
            "HTTP_X_REAL_IP",
            "HTTP_CF_CONNECTING_IP",  # Cloudflare
            "HTTP_X_CLUSTER_CLIENT_IP",
            "HTTP_FORWARDED",
            "REMOTE_ADDR",
        ]

        for header in ip_headers:
            ip = request.META.get(header)
            if ip:
                # Handle comma-separated IPs (X-Forwarded-For)
                if "," in ip:
                    ip = ip.split(",")[0].strip()
                if ip and ip != "unknown":
                    return ip

        return request.META.get("REMOTE_ADDR", "127.0.0.1")

    def _detect_auth_method(self, request: WSGIRequest) -> str:
        """
        Detects the authentication method used for the request.
        """
        if hasattr(request, "auth") and request.auth:
            return "token"
        elif "authorization" in request.headers:
            auth_header = request.headers["authorization"]
            if auth_header.startswith("Bearer"):
                return "jwt"
            elif auth_header.startswith("Token"):
                return "token"
            elif auth_header.startswith("Basic"):
                return "basic"
            else:
                return "custom"
        elif hasattr(request, "user") and request.user.is_authenticated:
            return "session"
        else:
            return "none"


class SamplingFilter(logging.Filter):
    """
    Intelligent sampling filter to prevent log storms and manage log volume.

    Features:
    - Adaptive sampling based on log frequency
    - Rate limiting per logger/level combination
    - Circuit breaker pattern for high-frequency loggers
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sample_rates = {
            logging.CRITICAL: 1.0,  # Always log critical
            logging.ERROR: 1.0,  # Always log errors
            logging.WARNING: 0.8,  # Sample 80% of warnings
            logging.INFO: 0.5,  # Sample 50% of info
            logging.DEBUG: 0.1,  # Sample 10% of debug
        }
        self.rate_limits = {}  # Track rate limits per logger
        self.circuit_breakers = {}  # Track circuit breaker state

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Applies intelligent sampling and rate limiting.
        """
        logger_key = f"{record.name}:{record.levelno}"
        current_time = time.time()

        # Check circuit breaker
        if self._is_circuit_open(logger_key, current_time):
            return False

        # Apply rate limiting
        if not self._check_rate_limit(logger_key, current_time):
            self._update_circuit_breaker(logger_key, current_time)
            return False

        # Apply sampling
        sample_rate = self.sample_rates.get(record.levelno, 1.0)
        if sample_rate < 1.0:
            import random

            if random.random() > sample_rate:
                return False

        return True

    def _check_rate_limit(self, logger_key: str, current_time: float) -> bool:
        """
        Implements token bucket rate limiting.
        """
        if logger_key not in self.rate_limits:
            self.rate_limits[logger_key] = {
                "tokens": 10,  # Initial tokens
                "last_update": current_time,
                "max_tokens": 10,
                "refill_rate": 1,  # Tokens per second
            }

        bucket = self.rate_limits[logger_key]
        time_passed = current_time - bucket["last_update"]

        # Refill tokens
        bucket["tokens"] = min(
            bucket["max_tokens"],
            bucket["tokens"] + time_passed * bucket["refill_rate"],
        )
        bucket["last_update"] = current_time

        # Check if we have tokens
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True

        return False

    def _is_circuit_open(self, logger_key: str, current_time: float) -> bool:
        """
        Implements circuit breaker pattern for logging.
        """
        if logger_key not in self.circuit_breakers:
            return False

        breaker = self.circuit_breakers[logger_key]

        # Circuit is not open if opened_at is None (circuit hasn't been opened yet)
        if breaker["opened_at"] is None:
            return False

        # Check if circuit should be closed
        if current_time - breaker["opened_at"] > breaker["timeout"]:
            del self.circuit_breakers[logger_key]
            return False

        return True

    def _update_circuit_breaker(self, logger_key: str, current_time: float) -> None:
        """
        Updates circuit breaker state based on rate limit violations.
        """
        if logger_key not in self.circuit_breakers:
            self.circuit_breakers[logger_key] = {
                "violations": 1,
                "opened_at": None,
                "timeout": 60,  # 1 minute timeout
            }
        else:
            breaker = self.circuit_breakers[logger_key]
            breaker["violations"] += 1

            # Open circuit if too many violations
            if breaker["violations"] > 100 and not breaker["opened_at"]:
                breaker["opened_at"] = current_time


class SecurityFilter(logging.Filter):
    """
    Security-focused filter for PII scrubbing, threat detection, and compliance.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pii_patterns = [
            # Credit card numbers
            r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            # Social Security Numbers
            r"\b\d{3}-\d{2}-\d{4}\b",
            # Email addresses (partial masking)
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            # Phone numbers
            r"\b\d{3}-\d{3}-\d{4}\b",
        ]

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Scrubs PII from log messages and detects security events.
        """
        # Scrub PII from message
        if hasattr(record, "msg") and isinstance(record.msg, str):
            record.msg = self._scrub_pii(record.msg)

        # Detect security events
        self._detect_security_events(record)

        return True

    def _scrub_pii(self, message: str) -> str:
        """
        Removes or masks PII from log messages.
        """
        import re

        for pattern in self.pii_patterns:
            message = re.sub(pattern, "[REDACTED]", message)

        return message

    def _detect_security_events(self, record: logging.LogRecord) -> None:
        """
        Detects and flags potential security events.
        """
        security_indicators = [
            "authentication failed",
            "unauthorized access",
            "sql injection",
            "xss attempt",
            "csrf token missing",
            "rate limit exceeded",
        ]

        message = str(getattr(record, "msg", "")).lower()

        for indicator in security_indicators:
            if indicator in message:
                record.security_event = True
                record.threat_type = indicator.replace(" ", "_")
                break
        else:
            record.security_event = False
            record.threat_type = "none"


# Alias for backward compatibility
RequestIDFilter = RequestContextFilter
