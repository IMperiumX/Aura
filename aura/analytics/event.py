from __future__ import annotations

from base64 import b64encode
from typing import TYPE_CHECKING
from uuid import uuid1

from django.utils import timezone

from aura.analytics.attribute import Attribute
from aura.analytics.utils import get_data

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Mapping
    from collections.abc import Sequence
    from typing import Any


class Event:
    __slots__ = ["data", "datetime", "uuid"]

    # This MUST be overridden by child classes.
    type = None

    # These should be overridden by child classes.
    attributes: Sequence[Attribute] = ()

    def __init__(
        self, type: Any | None = None, datetime: dt.datetime | None = None, **items: Any
    ) -> None:
        self.uuid = uuid1()
        self.datetime = datetime or timezone.now()
        self.type = self._get_type(type)  # noqa: PLE0237 type: ignore[misc]
        self.data = get_data(self.attributes, items)

    def _get_type(self, _type: Any | None = None) -> Any:
        """
        The Event's `type` can either be passed in as a parameter or set as a
        property on a child class.
        """
        if _type is not None:
            return _type

        if self.type is None:
            msg = "Event is missing type"
            raise ValueError(msg)

        return self.type

    def serialize(self) -> Mapping[str, Any]:
        return {
            "uuid": b64encode(self.uuid.bytes),
            "timestamp": self.datetime.timestamp(),
            "type": self.type,
            "data": self.data,
        }

    @classmethod
    def from_instance(cls, instance: Any, **kwargs: Any) -> Event:
        return cls(
            **{
                attr.name: kwargs.get(attr.name, getattr(instance, attr.name, None))
                for attr in cls.attributes
            },
        )
