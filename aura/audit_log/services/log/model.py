import datetime
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

DEFAULT_DATE = datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC)


@dataclass
class UserIpEvent:
    user_id: int = -1
    ip_address: str = "127.0.0.1"
    last_seen: datetime.datetime = DEFAULT_DATE
    country_code: str | None = None
    region_code: str | None = None


@dataclass
class AuditLogEvent:
    # 'datetime' is apparently reserved attribute name for dataclasses.
    date_added: datetime.datetime = DEFAULT_DATE
    event_id: int = -1
    actor_label: str | None = None
    actor_user_id: int | None = None
    actor_key_id: int | None = None
    ip_address: str | None = None
    target_object_id: int | None = None
    data: Mapping[str, Any] | None = None
    target_user_id: int | None = None
