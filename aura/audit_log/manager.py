from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aura.core.models import AuditLogEntry


class DuplicateAuditLogEventError(Exception):
    pass


class AuditLogEventNotRegisteredError(Exception):
    pass


"""
The audit log system records changes made and displays them in settings.

To add a new audit log event:

1. Create a new instance of AuditLogEvent. You'll need an event_id, name, api_name,
   and optional template.

   Note: The template uses AuditLogEntry.data fields to construct a simple audit
   log message. For more complicated messages, subclass AuditLogEvent in events.py
   and override the render function.

2. Register the AuditLogEvent using `default_manager.add()`.

    default_manager.add(
        AuditLogEvent(
            event_id=1,
            name="MEMBER_INVITE",
            api_name="member.invite",
            template="invited member {email}",
        )
    )

3. Record your AuditLogEvent.

    self.create_audit_entry(
        request=request,
        target_object=member.id,
        data={"email": "email@gmail.com"},
        event=audit_log.get_event_id(MEMBER_INVITE),
    )
"""


@dataclass(init=False)
class AuditLogEvent:
    # Unique event ID (ex. 1)
    event_id: int

    # Unique event name (ex. MEMBER_INVITE)
    name: str

    # Unique event api name (ex. member.invite)
    api_name: str

    # Simple template for rendering the audit log message using
    # the AuditLogEntry.data fields. For more complicated messages,
    # subclass AuditLogEvent and override the render method.
    template: str | None = None

    def __init__(self, event_id, name, api_name, template=None):
        self.event_id = event_id
        self.name = name
        self.api_name = api_name
        self.template = template

    def render(self, audit_log_entry: AuditLogEntry):
        if not self.template:
            return ""
        return self.template.format(**audit_log_entry.data)


class AuditLogEventManager:
    def __init__(self) -> None:
        self._event_registry: dict[str, AuditLogEvent] = {}
        self._event_id_lookup: dict[int, AuditLogEvent] = {}
        self._api_name_lookup: dict[str, AuditLogEvent] = {}

    def add(self, audit_log_event: AuditLogEvent) -> None:
        if (
            audit_log_event.name in self._event_registry
            or audit_log_event.event_id in self._event_id_lookup
            or audit_log_event.api_name in self._api_name_lookup
        ):
            msg = f"Duplicate audit log: {audit_log_event.name} with ID {audit_log_event.event_id} and api name {audit_log_event.api_name}"
            raise DuplicateAuditLogEventError(msg)

        self._event_registry[audit_log_event.name] = audit_log_event
        self._event_id_lookup[audit_log_event.event_id] = audit_log_event
        self._api_name_lookup[audit_log_event.api_name] = audit_log_event

    def get(self, event_id: int) -> AuditLogEvent:
        if event_id not in self._event_id_lookup:
            msg = f"Event ID {event_id} does not exist"
            raise AuditLogEventNotRegisteredError(msg)
        return self._event_id_lookup[event_id]

    def get_event_id(self, name: str) -> int:
        if name not in self._event_registry:
            msg = f"Event {name} does not exist"
            raise AuditLogEventNotRegisteredError(msg)
        return self._event_registry[name].event_id

    def get_event_id_from_api_name(self, api_name: str) -> int | None:
        if api_name not in self._api_name_lookup:
            return None
        return self._api_name_lookup[api_name].event_id

    def get_api_names(self) -> list[str]:
        return list(self._api_name_lookup)
