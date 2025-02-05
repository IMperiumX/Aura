from aura.audit_log import events
from aura.audit_log.manager import AuditLogEvent
from aura.audit_log.manager import AuditLogEventManager

default_manager = AuditLogEventManager()
# Register the AuditLogEvent objects to the `default_manager`
default_manager.add(
    AuditLogEvent(
        event_id=1,
        name="PATIENT_CREATE",
        api_name="patient.create",
        template="created member {email}",
    ),
)

default_manager.add(events.MonitorAddAuditLogEvent())
