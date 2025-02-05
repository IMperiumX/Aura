import abc

from aura.core.services.base import Service

from .model import AuditLogEvent
from .model import UserIpEvent


class LogService(Service):
    key = "log"

    @classmethod
    def get_local_implementation(cls) -> Service:
        return impl_by_db()

    @abc.abstractmethod
    def record_audit_log(self, *, event: AuditLogEvent) -> None:
        pass

    @abc.abstractmethod
    def record_user_ip(self, *, event: UserIpEvent) -> None:
        pass

    @abc.abstractmethod
    def find_last_log(
        self,
        *,
        target_object_id: int | None,
        event: int,
        data: dict[str, str] | None = None,
    ) -> AuditLogEvent | None:
        pass


def impl_by_db() -> LogService:
    from .impl import DatabaseBackedLogService

    return DatabaseBackedLogService()


log_service = LogService.create_delegation()
