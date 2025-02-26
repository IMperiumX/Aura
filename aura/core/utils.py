from __future__ import annotations

import base64
import typing
import zlib
from pathlib import Path

from django.conf import settings
from django.utils.module_loading import import_string

if typing.TYPE_CHECKING:
    from collections.abc import Callable
DB_CONFIG = settings.DATABASES[settings.DATABASE_CONNECTION_DEFAULT_NAME]


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
    serializer = import_string(
        "rest_framework_simplejwt.serializers.TokenObtainPairSerializer",
    )
    refresh = serializer.get_token(user)
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


def _get_db_connection_params():
    """Centralized database connection parameter retrieval."""
    return {
        "scheme": "postgresql",
        "dbname": DB_CONFIG["NAME"],
        "user": DB_CONFIG["USER"],
        "password": DB_CONFIG["PASSWORD"],
        "host": DB_CONFIG["HOST"],
        "port": DB_CONFIG["PORT"],
    }


def messages_to_prompt(messages):
    prompt = ""
    for message in messages:
        if message.role == "system":
            prompt += f"<|system|>\n{message.content}</s>\n"
        elif message.role == "user":
            prompt += f"<|user|>\n{message.content}</s>\n"
        elif message.role == "assistant":
            prompt += f"<|assistant|>\n{message.content}</s>\n"

    # ensure we start with a system prompt, insert blank if needed
    if not prompt.startswith("<|system|>\n"):
        prompt = "<|system|>\n</s>\n" + prompt

    # add final assistant prompt
    prompt = prompt + "<|assistant|>\n"

    return prompt


def completion_to_prompt(completion):
    return f"<|system|>\n</s>\n<|user|>\n{completion}</s>\n<|assistant|>\n"
