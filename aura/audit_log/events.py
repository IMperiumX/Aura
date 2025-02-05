import typing

from aura.audit_log.manager import AuditLogEvent

if typing.TYPE_CHECKING:
    from aura.core.models import AuditLogEntry


class MonitorAddAuditLogEvent(AuditLogEvent):
    def __init__(self):
        super().__init__(
            event_id=120,
            name="MONITOR_ADD",
            api_name="monitor.add",
        )

    def render(self, audit_log_entry: "AuditLogEntry") -> str:
        entry_data = audit_log_entry.data
        name = entry_data.get("name")
        upsert = entry_data.get("upsert")

        return f'added{" upsert " if upsert else " "}monitor {name}'
