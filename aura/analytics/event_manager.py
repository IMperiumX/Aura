__all__ = ("EventManager", "default_manager")

from typing import TYPE_CHECKING
from typing import Any

from aura.analytics.event import Event

if TYPE_CHECKING:
    from collections.abc import MutableMapping


class EventManager:
    def __init__(self) -> None:
        self._event_types: MutableMapping[Any, type[Event]] = {}

    def register(self, event_cls: type[Event]) -> None:
        event_type = event_cls.type
        if event_type in self._event_types:
            assert self._event_types[event_type] == event_cls
        else:
            self._event_types[event_type] = event_cls

    def get(self, type: str) -> type[Event]:
        return self._event_types[type]

    def unregister(self, event_cls: type[Event]) -> None:
        event_type = event_cls.type
        if event_type in self._event_types:
            del self._event_types[event_type]


default_manager = EventManager()
