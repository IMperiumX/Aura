import datetime

from aura.users.models import User
from aura.users.userip import UserIP
from aura.users.userip import UserIpEvent


class DatabaseBackedLogService:
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


log_service = DatabaseBackedLogService()
