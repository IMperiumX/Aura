from aura.utils.services import LazyServiceWrapper

from .attribute import Attribute
from .base import Analytics
from .config import configure_analytics_backend
from .config import get_analytics_config
from .config import is_analytics_production_ready
from .event import Event
from .event_manager import default_manager
from .map import Map
from .mixins import AnalyticsRecordingMixin

__all__ = (
    "Analytics",
    "AnalyticsRecordingMixin",
    "Attribute",
    "Event",
    "Map",
    "record",
    "record_event",
    "setup",
    "get_analytics_config",
    "configure_analytics_backend",
    "is_analytics_production_ready",
)

# Legacy aliases for backwards compatibility
_ANALYTICS_ALIASES: dict[str, str] = {
    "noop": "aura.analytics.Analytics",
    "pubsub": "aura.analytics.pubsub.PubSubAnalytics",
    "database": "aura.analytics.backends.database.DatabaseAnalytics",
    "redis": "aura.analytics.backends.redis_backend.RedisAnalytics",
    "multi": "aura.analytics.backends.multi_backend.MultiBackendAnalytics",
}


def _get_backend_path(path: str) -> str:
    return _ANALYTICS_ALIASES.get(path, path)


# Lazy backend initialization to avoid database access during app startup
_backend = None


def _get_backend():
    """Lazy initialization of analytics backend."""
    global _backend
    if _backend is None:
        try:
            _backend = configure_analytics_backend()
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to configure analytics backend: {e}")

            # Fallback to legacy configuration
            pubsub_options: dict[str, str] = {
                "project": "",
                "topic": "",
            }

            _backend = LazyServiceWrapper(
                backend_base=Analytics,
                backend_path=_get_backend_path(_ANALYTICS_ALIASES["pubsub"]),
                options=pubsub_options,
            )
    return _backend


# Export main functions with lazy backend access
def record(*args, **kwargs):
    backend = _get_backend()
    if hasattr(backend, "record"):
        return backend.record(*args, **kwargs)
    return None


def record_event(*args, **kwargs):
    backend = _get_backend()
    if hasattr(backend, "record_event"):
        return backend.record_event(*args, **kwargs)
    return None


def setup():
    backend = _get_backend()
    if hasattr(backend, "setup"):
        return backend.setup()
    return None


def validate():
    backend = _get_backend()
    if hasattr(backend, "validate"):
        return backend.validate()
    return True


# Registry functions (these don't need lazy loading)
register = default_manager.register
unregister = default_manager.unregister


# Additional utility functions with lazy backend access
def get_backend_status():
    """Get current backend status and health information."""
    backend = _get_backend()
    if hasattr(backend, "get_backend_status"):
        return backend.get_backend_status()
    return {"status": "unknown", "backend": type(backend).__name__}


def get_live_metrics(**kwargs):
    """Get live metrics from the analytics backend."""
    backend = _get_backend()
    if hasattr(backend, "get_live_metrics"):
        return backend.get_live_metrics(**kwargs)
    elif hasattr(backend, "get_metrics"):
        return backend.get_metrics(**kwargs)
    return {}


def get_events(**kwargs):
    """Retrieve events from the analytics backend."""
    backend = _get_backend()
    if hasattr(backend, "get_events"):
        return backend.get_events(**kwargs)
    return []


def cleanup_old_data(days_to_keep: int = 7):
    """Clean up old analytics data."""
    backend = _get_backend()
    if hasattr(backend, "cleanup_old_data"):
        return backend.cleanup_old_data(days_to_keep)
    elif hasattr(backend, "cleanup_old_events"):
        return backend.cleanup_old_events(days_to_keep)
    return 0


def force_health_check():
    """Force a health check on all backends."""
    backend = _get_backend()
    if hasattr(backend, "force_health_check"):
        return backend.force_health_check()
    return {"status": "health_check_not_supported"}
