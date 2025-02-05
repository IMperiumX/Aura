# flake8: noqa
# Avoid shadowing the standard library json module

from __future__ import annotations

import datetime
import decimal
import typing
import uuid
from enum import Enum
from typing import IO
from typing import Any
from typing import Never
from typing import TypeVar

import rapidjson
from django.db.models.query import QuerySet
from django.utils.encoding import force_str
from django.utils.functional import Promise
from django.utils.timezone import is_aware
from simplejson import JSONEncoder
from simplejson import _default_decoder  # type: ignore[attr-defined]

if typing.TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Collection
    from collections.abc import Generator
    from collections.abc import Mapping

TKey = TypeVar("TKey")
TValue = TypeVar("TValue")


def datetime_to_str(o: datetime.datetime) -> str:
    return o.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def better_default_encoder(o: object) -> object:
    if isinstance(o, uuid.UUID):
        return o.hex
    elif isinstance(o, datetime.datetime):
        return datetime_to_str(o)
    elif isinstance(o, datetime.date):
        return o.isoformat()
    elif isinstance(o, datetime.time):
        if is_aware(o):
            msg = "JSON can't represent timezone-aware times."
            raise ValueError(msg)
        r = o.isoformat()
        if o.microsecond:
            r = r[:12]
        return r
    elif isinstance(o, (set, frozenset)):
        return list(o)
    elif isinstance(o, decimal.Decimal):
        return str(o)
    elif isinstance(o, Enum):
        return o.value
    elif callable(o):
        return "<function>"
    elif isinstance(o, QuerySet):
        return list(o)
    # serialization for certain Django objects here: https://docs.djangoproject.com/en/1.8/topics/serialization/
    elif isinstance(o, Promise):
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
    # eliminates whitespace.
    separators=(",", ":"),
    # upstream: False # noqa: ERA001
    # True makes nan, inf, -inf serialize as null in compliance with ECMA-262.
    ignore_nan=True,
    default=better_default_encoder,
)

_default_escaped_encoder = JSONEncoderForHTML(
    separators=(",", ":"),
    ignore_nan=True,
    default=better_default_encoder,
)


# Never here is to make this a mypy error to pass kwargs, since they are currently silently dropped
def dump(value: Any, fp: IO[str], **kwargs: Never) -> None:
    for chunk in _default_encoder.iterencode(value):
        fp.write(chunk)


# Never here is to make this a mypy error to pass kwargs, since they are currently silently dropped
def dumps(value: Any, escape: bool = False, **kwargs: Never) -> str:
    if escape:
        return _default_escaped_encoder.encode(value)
    return _default_encoder.encode(value)


# Never here is to make this a mypy error to pass kwargs, since they are currently silently dropped
def load(fp: IO[str] | IO[bytes], **kwargs: Never) -> Any:
    return loads(fp.read())


# Never here is to make this a mypy error to pass kwargs, since they are currently silently dropped
def loads(value: str | bytes, use_rapid_json: bool = False, **kwargs: Never) -> Any:
    if use_rapid_json is True:
        return rapidjson.loads(value)
    return _default_decoder.decode(value)


def apply_key_filter(
    obj: Mapping[TKey, TValue],
    *,
    keep_keys: Collection[TKey] | None = None,
    key_filter: Callable[[TKey], bool] | None = None,
) -> dict[TKey, TValue]:
    """
    A version of the built-in `filter` function which works on dictionaries, returning a (filtered)
    shallow copy of the original.

    If `keep_keys` is given, any key-value pair whose key isn't in `keep_keys` will be excluded from
    the result.

    If a `key_filter` function is given, any key-value pair for which `key_filter(key)` is False
    will be excluded from the result.

    If both are given, `keep_keys` takes precedence. If neither is given, an unfiltered shallow copy
    of the original is returned.
    """

    if keep_keys:
        key_filter = lambda key: key in keep_keys
    elif not keep_keys and not key_filter:
        key_filter = lambda _key: True

    # `key_filter` can't be None by now, but mypy still thinks it might
    assert key_filter

    return {key: obj[key] for key in obj if key_filter(key)}
