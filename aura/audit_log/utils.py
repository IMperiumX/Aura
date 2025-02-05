from logging import Logger
from typing import Any

from django.http.request import HttpRequest

from aura import audit_log
from aura.audit_log.services.log import log_service
from aura.core.models import AuditLogEntry


def create_audit_entry(
    request: HttpRequest,
    transaction_id: int | str | None = None,
    logger: Logger | None = None,
    **kwargs: Any,
) -> AuditLogEntry:
    from rest_framework.authtoken.models import Token

    user = kwargs.pop("actor", request.user if request.user.is_authenticated else None)
    api_key = (
        request.auth
        if hasattr(request, "auth") and isinstance(request.auth, Token)
        else None
    )
    ip_address = request.META.get("REMOTE_ADDR", None)

    entry = AuditLogEntry(
        actor_id=user.id if user else None,
        actor_key=api_key,
        ip_address=ip_address,
        **kwargs,
    )

    # Only create a real AuditLogEntry record if we are passing an event type
    # otherwise, we want to still log to our actual logging
    if entry.event is not None:
        log_service.record_audit_log(event=entry.as_event())

    extra = {
        "ip_address": entry.ip_address,
        "object_id": entry.target_object,
        "entry_id": entry.id,
        "actor_label": entry.actor_label,
    }
    if entry.actor_id:
        extra["actor_id"] = entry.actor_id
    if entry.actor_key_id:
        extra["actor_key_id"] = entry.actor_key_id
    if transaction_id is not None:
        extra["transaction_id"] = transaction_id

    if logger:
        # Only use the api_name for the logger message when the entry
        # is a real AuditLogEntry record
        if entry.event is not None:
            logger.info(audit_log.get(entry.event).api_name, extra=extra)
        else:
            logger.info(entry, extra=extra)

    return entry
