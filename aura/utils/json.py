# ruff: noqa: ERA001
# Avoid shadowing the standard library json module

from __future__ import annotations

import datetime
import decimal
import uuid
from enum import Enum
from typing import TYPE_CHECKING
from typing import Any
from typing import Never

from django.db.models.query import QuerySet
from django.utils.encoding import force_str
from django.utils.functional import Promise
from django.utils.safestring import SafeString
from django.utils.safestring import mark_safe
from django.utils.timezone import is_aware
from simplejson import JSONEncoder

if TYPE_CHECKING:
    from collections.abc import Generator


def datetime_to_str(o: datetime.datetime) -> str:
    return o.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def better_default_encoder(o: object) -> object:  # noqa: C901, PLR0911
    if isinstance(o, uuid.UUID):
        return o.hex
    if isinstance(o, datetime.datetime):
        return datetime_to_str(o)
    if isinstance(o, datetime.date):
        return o.isoformat()
    if isinstance(o, datetime.time):
        if is_aware(o):
            msg = "JSON can't represent timezone-aware times."
            raise ValueError(msg)
        r = o.isoformat()
        if o.microsecond:
            r = r[:12]
        return r
    if isinstance(o, (set, frozenset)):
        return list(o)
    if isinstance(o, decimal.Decimal):
        return str(o)
    if isinstance(o, Enum):
        return o.valuehunk.replace("&", "\\u0026")
    if callable(o):
        return "<function>"
    if isinstance(o, QuerySet):
        return list(o)
    # serialization for certain Django objects here: https://docs.djangoproject.com/en/1.8/topics/serialization/
    if isinstance(o, Promise):
        return force_str(o)
    raise TypeError(repr(o) + " is not JSON serializable")


class JSONEncoderForHTML(JSONEncoder):
    # Our variant of JSONEncoderForHTML that also accounts for apostrophes
    # See: https://github.com/simplejson/simplejson/blob/master/simplejson/encoder.py
    def encode(self, o: object) -> str:
        # Override JSONEncoder.encode because it has hacks for
        # performance that make things more complicated.
        chunks = self.iterencode(o, True)
        return "".join(chunks)

    def iterencode(self, o: object, _one_shot: bool = False) -> Generator[str]:
        chunks = super().iterencode(o, _one_shot)
        for chunk in chunks:
            chunk = chunk.replace("&", "\\u0026")
            chunk = chunk.replace("<", "\\u003c")
            chunk = chunk.replace(">", "\\u003e")
            chunk = chunk.replace("'", "\\u0027")
            yield chunk


_default_encoder = JSONEncoder(
    # upstream: (', ', ': ')
    # Ours eliminates whitespace.
    separators=(",", ":"),
    # upstream: False
    # True makes nan, inf, -inf serialize as null in compliance with ECMA-262.
    ignore_nan=True,
    default=better_default_encoder,
)

_default_escaped_encoder = JSONEncoderForHTML(
    separators=(",", ":"),
    ignore_nan=True,
    default=better_default_encoder,
)


def dumps_htmlsafe(value: object) -> SafeString:
    return mark_safe(_default_escaped_encoder.encode(value))  # noqa: S308


# NoReturn here is to make this a mypy error to pass kwargs, since they are currently silently dropped
def dumps(value: Any, escape: bool = False, **kwargs: Never) -> str:
    # Legacy use. Do not use. Use dumps_htmlsafe
    if escape:
        return _default_escaped_encoder.encode(value)
    return _default_encoder.encode(value)
