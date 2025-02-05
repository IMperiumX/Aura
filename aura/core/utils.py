from __future__ import annotations

import base64
import typing
import zlib
from pathlib import Path

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

if typing.TYPE_CHECKING:
    from collections.abc import Callable


def sane_repr(*attrs: str) -> Callable[[object], str]:
    """

    :param *attrs: str:

    """
    if "id" not in attrs and "pk" not in attrs:
        attrs = ("id", *attrs)

    def _repr(self: object) -> str:
        """

        :param self: object:
        :param self: object:
        :param self: object:

        """
        cls = type(self).__name__

        pairs = (f"{a}={getattr(self, a, None)!r}" for a in attrs)

        return "<{} at 0x{:x}: {}>".format(cls, id(self), ", ".join(pairs))

    return _repr


def default_create_token(token_model, user, serializer):
    token, _ = token_model.objects.get_or_create(user=user)
    return token


def jwt_encode(user):
    refresh = TokenObtainPairSerializer.get_token(user)
    return refresh.access_token, refresh


def get_upload_path(instance, filename):
    """
    Return the upload path for the file.
    """

    return Path(f"uploads/{instance.__class__.__name__}/{instance.pk}").mkdir(
        parents=True,
        exist_ok=True,
    )


def decompress(value: str) -> bytes:
    return zlib.decompress(base64.b64decode(value))
