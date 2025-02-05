from __future__ import annotations

import contextlib
import datetime
import logging
import typing

from django.db import IntegrityError
from django.db import router
from django.db import transaction
from django.db.transaction import Atomic
from django.db.transaction import get_connection

from aura.audit_log.services.log.service import LogService
from aura.users.models import User
from aura.users.userip import UserIP

if typing.TYPE_CHECKING:
    from aura.audit_log.services.log.model import AuditLogEvent
    from aura.audit_log.services.log.model import UserIpEvent

logger = logging.getLogger("aura.audit_log_service")


@contextlib.contextmanager
def enforce_constraints(transaction: Atomic):
    """
    Nested transaction in Django do not check constraints by default, meaning IntegrityErrors can 'float' to callers
    of functions that happen to wrap with additional transaction scopes.  Using this context manager around a transaction
    will force constraints to be checked at the end of that transaction (or savepoint) even if it happens to be nested,
    allowing you to handle the IntegrityError correctly.
    """
    with transaction:
        yield
        get_connection(transaction.using or "default").check_constraints()


class DatabaseBackedLogService(LogService):
    def record_audit_log(self, *, event: AuditLogEvent) -> None:
        from aura.core.models import AuditLogEntry

        entry = AuditLogEntry.from_event(event)
        try:
            with enforce_constraints(
                transaction.atomic(router.db_for_write(AuditLogEntry)),
            ):
                entry.save()
        except Exception as e:
            logger.exception(
                "Failed to save audit log entry: %s",
                extra={"event": event},
            )
            if isinstance(e, IntegrityError):
                error_message = str(e)
                if '"auth_user"' in error_message:
                    # It is possible that a user existed at the time of serialization but was deleted by the time of consumption
                    # in which case we follow the database's SET NULL on delete handling.
                    if event.actor_user_id:
                        event.actor_user_id = None
                    if event.target_user_id:
                        event.target_user_id = None
                    return self.record_audit_log(event=event)

    def record_user_ip(self, *, event: UserIpEvent) -> None:
        UserIP.objects.create_or_update(
            user_id=event.user_id,
            ip_address=event.ip_address,
            values={
                "last_seen": event.last_seen,
                "country_code": event.country_code,
                "region_code": event.region_code,
            },
        )
        User.objects.filter(
            id=event.user_id,
            last_active__lt=(event.last_seen - datetime.timedelta(minutes=1)),
        ).update(last_active=event.last_seen)

    def find_last_log(
        self,
        *,
        target_object_id: int | None,
        event: int,
        data: dict[str, str] | None = None,
    ) -> AuditLogEvent | None:
        from aura.core.models import AuditLogEntry

        last_entry_q = AuditLogEntry.objects.filter(
            target_object=target_object_id,
            event=event,
        )
        if data:
            last_entry_q = last_entry_q.filter(data=data)
        last_entry: AuditLogEntry | None = last_entry_q.last()

        if last_entry is None:
            return None

        return last_entry.as_event()
