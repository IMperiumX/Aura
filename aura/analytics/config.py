"""
Analytics configuration management with environment-based backend selection.
"""

import logging
import os
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class AnalyticsConfig:
    """
    Centralized configuration for analytics backends.

    Supports:
    - Environment-based configuration
    - Multiple backend configurations
    - Fallback strategies
    - Configuration validation
    - Health monitoring settings
    """

    DEFAULT_BACKENDS = {
        "development": {
            "primary": "database",
            "backends": [
                {
                    "name": "database",
                    "class": "aura.analytics.backends.database.DatabaseAnalytics",
                    "options": {
                        "table_name": "analytics_events_dev",
                        "enable_batching": False,  # Easier debugging
                        "batch_size": 10,
                    },
                },
            ],
        },
        "testing": {
            "primary": "noop",
            "backends": [
                {
                    "name": "noop",
                    "class": "aura.analytics.Analytics",  # Base class does nothing
                    "options": {},
                },
            ],
        },
        "staging": {
            "primary": "redis",
            "backends": [
                {
                    "name": "redis",
                    "class": "aura.analytics.backends.redis_backend.RedisAnalytics",
                    "options": {
                        "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/1"),
                        "stream_name": "analytics:events:staging",
                        "ttl_seconds": 86400 * 3,  # 3 days
                    },
                },
                {
                    "name": "database_fallback",
                    "class": "aura.analytics.backends.database.DatabaseAnalytics",
                    "options": {
                        "table_name": "analytics_events_staging",
                        "enable_batching": True,
                        "batch_size": 50,
                    },
                },
            ],
        },
        "production": {
            "primary": "pubsub",
            "backends": [
                {
                    "name": "pubsub",
                    "class": "aura.analytics.pubsub.PubSubAnalytics",
                    "options": {
                        "project": os.getenv("GOOGLE_CLOUD_PROJECT"),
                        "topic": "analytics-events",
                        "batch_max_messages": 1000,
                        "batch_max_latency": 0.05,
                    },
                },
                {
                    "name": "redis",
                    "class": "aura.analytics.backends.redis_backend.RedisAnalytics",
                    "options": {
                        "redis_url": os.getenv("REDIS_URL"),
                        "stream_name": "analytics:events:prod",
                        "ttl_seconds": 86400 * 7,  # 7 days
                    },
                },
                {
                    "name": "database_audit",
                    "class": "aura.analytics.backends.database.DatabaseAnalytics",
                    "options": {
                        "table_name": "analytics_events_audit",
                        "enable_batching": True,
                        "batch_size": 100,
                    },
                },
            ],
        },
    }

    def __init__(self, environment: str = None):
        self.environment = environment or self._detect_environment()
        self.config = self._load_configuration()
        self._validate_configuration()

    def _detect_environment(self) -> str:
        """Detect current environment from various sources."""
        # Check Django settings first
        if hasattr(settings, "ENVIRONMENT"):
            return settings.ENVIRONMENT

        # Check environment variables
        env = os.getenv("DJANGO_ENVIRONMENT", os.getenv("ENVIRONMENT"))
        if env:
            return env.lower()

        # Check DEBUG setting
        if hasattr(settings, "DEBUG"):
            return "development" if settings.DEBUG else "production"

        # Default fallback
        return "development"

    def _load_configuration(self) -> dict[str, Any]:
        """Load configuration for current environment."""
        # Try custom settings first
        custom_config = getattr(settings, "ANALYTICS_CONFIG", None)
        if custom_config:
            logger.info("Using custom analytics configuration")
            return custom_config

        # Use environment-specific defaults
        if self.environment in self.DEFAULT_BACKENDS:
            config = self.DEFAULT_BACKENDS[self.environment].copy()
            logger.info(f"Using default analytics configuration for {self.environment}")
            return config

        # Fallback to development config
        logger.warning(
            f"Unknown environment '{self.environment}', falling back to development config",
        )
        return self.DEFAULT_BACKENDS["development"].copy()

    def _validate_configuration(self) -> None:
        """Validate the loaded configuration."""
        if "backends" not in self.config:
            raise ImproperlyConfigured("Analytics configuration missing 'backends'")

        if not self.config["backends"]:
            raise ImproperlyConfigured(
                "Analytics configuration has no backends defined",
            )

        # Validate each backend
        for backend in self.config["backends"]:
            if "name" not in backend:
                raise ImproperlyConfigured("Backend configuration missing 'name'")

            if "class" not in backend:
                raise ImproperlyConfigured(
                    f"Backend '{backend['name']}' missing 'class'",
                )

        # Validate primary backend
        primary = self.config.get("primary")
        if primary:
            backend_names = [b["name"] for b in self.config["backends"]]
            if primary not in backend_names:
                raise ImproperlyConfigured(
                    f"Primary backend '{primary}' not found in backends list",
                )

        logger.info(f"Analytics configuration validated for {self.environment}")

    def get_backend_config(self) -> dict[str, Any]:
        """Get the complete backend configuration."""
        return self.config.copy()

    def get_backends_list(self) -> list[dict[str, Any]]:
        """Get list of backend configurations."""
        return self.config["backends"].copy()

    def get_primary_backend(self) -> str | None:
        """Get the primary backend name."""
        return self.config.get("primary")

    def get_multi_backend_config(self) -> dict[str, Any]:
        """Get configuration for multi-backend setup."""
        return {
            "backends": self.get_backends_list(),
            "primary_backend": self.get_primary_backend(),
            "enable_parallel": self.config.get("enable_parallel", True),
            "max_workers": self.config.get("max_workers", 3),
            "fallback_enabled": self.config.get("fallback_enabled", True),
            "health_check_interval": self.config.get("health_check_interval", 300),
        }

    def create_backend(self) -> "Analytics":
        """Create and return the configured analytics backend."""
        backends = self.get_backends_list()

        if len(backends) == 1:
            # Single backend
            backend_config = backends[0]
            return self._instantiate_backend(backend_config)
        else:
            # Multi-backend
            from aura.analytics.backends.multi_backend import MultiBackendAnalytics

            return MultiBackendAnalytics(**self.get_multi_backend_config())

    def _instantiate_backend(self, backend_config: dict[str, Any]) -> "Analytics":
        """Instantiate a single backend from configuration."""
        backend_class = backend_config["class"]
        options = backend_config.get("options", {})

        # Import the backend class
        if isinstance(backend_class, str):
            module_path, class_name = backend_class.rsplit(".", 1)
            module = __import__(module_path, fromlist=[class_name])
            backend_class = getattr(module, class_name)

        return backend_class(**options)

    def validate_environment_requirements(self) -> dict[str, bool]:
        """Validate that environment requirements are met."""
        requirements = {}

        for backend in self.get_backends_list():
            backend_name = backend["name"]
            backend_class = backend["class"]
            options = backend.get("options", {})

            if "pubsub" in backend_class.lower():
                # PubSub requirements
                requirements[f"{backend_name}_gcp_project"] = bool(
                    options.get("project"),
                )
                requirements[f"{backend_name}_gcp_credentials"] = bool(
                    os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                    or os.getenv("GOOGLE_CLOUD_PROJECT"),
                )

            elif "redis" in backend_class.lower():
                # Redis requirements
                redis_url = options.get("redis_url") or os.getenv("REDIS_URL")
                requirements[f"{backend_name}_redis_url"] = bool(redis_url)

            elif "database" in backend_class.lower():
                # Database requirements (usually always available)
                requirements[f"{backend_name}_database"] = True

        return requirements

    def get_missing_requirements(self) -> list[str]:
        """Get list of missing environment requirements."""
        requirements = self.validate_environment_requirements()
        return [req for req, met in requirements.items() if not met]

    def is_production_ready(self) -> bool:
        """Check if configuration is ready for production use."""
        missing = self.get_missing_requirements()

        if missing:
            logger.warning(f"Analytics not production ready. Missing: {missing}")
            return False

        # Additional production checks
        if self.environment == "production":
            backends = self.get_backends_list()

            # Should have at least 2 backends for redundancy
            if len(backends) < 2:
                logger.warning(
                    "Production should have multiple backends for redundancy",
                )
                return False

            # Should have PubSub for real-time processing
            has_pubsub = any("pubsub" in b["class"].lower() for b in backends)
            if not has_pubsub:
                logger.warning("Production should include PubSub backend")
                return False

        return True

    def get_health_check_config(self) -> dict[str, Any]:
        """Get health check configuration."""
        return {
            "enabled": self.config.get("health_checks_enabled", True),
            "interval": self.config.get("health_check_interval", 300),
            "timeout": self.config.get("health_check_timeout", 10),
            "alert_on_failure": self.config.get("alert_on_health_failure", True),
            "max_failures": self.config.get("max_health_failures", 3),
        }

    def get_metrics_config(self) -> dict[str, Any]:
        """Get metrics collection configuration."""
        return {
            "enabled": self.config.get("metrics_enabled", True),
            "retention_days": self.config.get("metrics_retention_days", 30),
            "aggregation_intervals": self.config.get(
                "aggregation_intervals",
                ["hour", "day"],
            ),
            "real_time_updates": self.config.get("real_time_updates", True),
        }


# Global configuration instance
_config = None


def get_analytics_config(environment: str = None) -> AnalyticsConfig:
    """Get the global analytics configuration instance."""
    global _config

    if _config is None or (environment and environment != _config.environment):
        _config = AnalyticsConfig(environment)

    return _config


def configure_analytics_backend() -> "Analytics":
    """Configure and return the analytics backend based on current settings."""
    config = get_analytics_config()
    return config.create_backend()


def is_analytics_production_ready() -> bool:
    """Quick check if analytics is ready for production."""
    try:
        config = get_analytics_config()
        return config.is_production_ready()
    except Exception as e:
        logger.error(f"Failed to check analytics production readiness: {e}")
        return False
