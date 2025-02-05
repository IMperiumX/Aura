import datetime
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils import timezone

from aura.core.geo import geo_by_addr
from aura.core.utils import sane_repr
from aura.users.models import User

DEFAULT_DATE = datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC)


class UserIP(models.Model):
    # There is an absolutely massive number of `UserIP` models.
    # only someone interested in backing up every bit of data could want

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    country_code = models.CharField(max_length=16, null=True)  # noqa: DJ001
    region_code = models.CharField(max_length=16, null=True)  # noqa: DJ001
    first_seen = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = (("user", "ip_address"),)

    __repr__ = sane_repr("user_id", "ip_address")

    def __str__(self) -> str:
        return f"{self.user_id} {self.ip_address}"

    @classmethod
    def log(cls, user: User, ip_address: str) -> None:
        # Only log once every 5 minutes for the same user/ip_address pair
        # since this is hit pretty frequently by all API calls in the UI, etc.
        cache_key = f"userip.log:{user.id}:{ip_address}"
        if not cache.get(cache_key):
            _perform_log(user, ip_address)
            cache.set(cache_key, 1, 300)


@dataclass
class UserIpEvent:
    user_id: int = -1
    ip_address: str = "127.0.0.1"
    last_seen: datetime.datetime = DEFAULT_DATE
    country_code: str | None = None
    region_code: str | None = None


def _perform_log(user: User, ip_address: str) -> None:
    from aura.audit_log.services.log import log_service

    try:
        geo = geo_by_addr(ip_address)
    except Exception:  # noqa: BLE001
        geo = None

    event = UserIpEvent(
        user_id=user.id,
        ip_address=ip_address,
        last_seen=timezone.now(),
    )

    if geo:
        event.country_code = geo["country_code"]
        event.region_code = geo["region"]

    log_service.record_user_ip(event=event)
