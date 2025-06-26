from aura.utils.services import LazyServiceWrapper

from .attribute import Attribute
from .base import Analytics
from .event import Event
from .event_manager import default_manager
from .map import Map
from .mixins import AnalyticsRecordingMixin
from .config import get_analytics_config, configure_analytics_backend, is_analytics_production_ready

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

# Initialize backend using new configuration system
try:
    backend = configure_analytics_backend()
except Exception as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Failed to configure analytics backend: {e}")

    # Fallback to legacy configuration
    pubsub_options: dict[str, str] = {
        "project": "",
        "topic": ""
    }

    backend = LazyServiceWrapper(
        backend_base=Analytics,
        backend_path=_get_backend_path(_ANALYTICS_ALIASES["pubsub"]),
        options=pubsub_options,
    )

# Export main functions
record = backend.record if hasattr(backend, 'record') else lambda *args, **kwargs: None
record_event = backend.record_event if hasattr(backend, 'record_event') else lambda *args, **kwargs: None
register = default_manager.register
unregister = default_manager.unregister
setup = backend.setup if hasattr(backend, 'setup') else lambda: None
validate = backend.validate if hasattr(backend, 'validate') else lambda: True

# Additional utility functions
def get_backend_status():
    """Get current backend status and health information."""
    if hasattr(backend, 'get_backend_status'):
        return backend.get_backend_status()
    return {'status': 'unknown', 'backend': type(backend).__name__}

def get_live_metrics(**kwargs):
    """Get live metrics from the analytics backend."""
    if hasattr(backend, 'get_live_metrics'):
        return backend.get_live_metrics(**kwargs)
    elif hasattr(backend, 'get_metrics'):
        return backend.get_metrics(**kwargs)
    return {}

def get_events(**kwargs):
    """Retrieve events from the analytics backend."""
    if hasattr(backend, 'get_events'):
        return backend.get_events(**kwargs)
    return []

def cleanup_old_data(days_to_keep: int = 7):
    """Clean up old analytics data."""
    if hasattr(backend, 'cleanup_old_data'):
        return backend.cleanup_old_data(days_to_keep)
    elif hasattr(backend, 'cleanup_old_events'):
        return backend.cleanup_old_events(days_to_keep)
    return 0

def force_health_check():
    """Force a health check on all backends."""
    if hasattr(backend, 'force_health_check'):
        return backend.force_health_check()
    return {'status': 'health_check_not_supported'}
