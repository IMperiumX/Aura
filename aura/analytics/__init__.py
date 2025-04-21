from aura import options
from aura.utils.services import LazyServiceWrapper

from .attribute import Attribute
from .base import Analytics
from .event import Event
from .event_manager import default_manager
from .map import Map

__all__ = (
    "Analytics",
    "Attribute",
    "Event",
    "Map",
    "record",
    "record_event",
    "setup",
)

_ANALYTICS_ALIASES = {
    "noop": "aura.analytics.Analytics",
    "pubsub": "aura.analytics.pubsub.PubSubAnalytics",
}


def _get_backend_path(path: str) -> str:
    return _ANALYTICS_ALIASES.get(path, path)


backend = LazyServiceWrapper(
    backend_base=Analytics,
    backend_path=_get_backend_path(options.get("analytics.backend")),
    options=options.get("analytics.options"),
)

record = backend.record
record_event = backend.record_event
register = default_manager.register
unregister = default_manager.unregister
setup = backend.setup
validate = backend.validate
