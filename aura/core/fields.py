import logging
import pickle

from django.db.models import Model
from django.db.models import TextField

from aura.core import json
from aura.core.utils import decompress

__all__ = ("GzippedDictField",)

logger = logging.getLogger("aura")


class GzippedDictField(TextField):
    """
    Slightly different from a JSONField in the sense that the default
    value is a dictionary.
    """

    def contribute_to_class(
        self,
        cls: type[Model],
        name: str,
        private_only: bool = False,
    ) -> None:
        """
        Add a descriptor for backwards compatibility
        with previous Django behavior.
        """
        super().contribute_to_class(cls, name, private_only=private_only)

    def to_python(self, value):
        try:
            if not value:
                return {}
            return json.loads(value)
        except (ValueError, TypeError):
            if isinstance(value, str) and value:
                try:
                    value = pickle.loads(decompress(value))  # noqa: S301
                except Exception:
                    logger.exception()
                    return {}
            elif not value:
                return {}
            return value

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def get_prep_value(self, value):
        if not value and self.null:
            # save ourselves some storage
            return None
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        if value is None and self.null:
            return None
        return json.dumps(value)

    def value_to_string(self, obj):
        return self.get_prep_value(self.value_from_object(obj))
