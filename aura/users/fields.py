from typing import Any

from django.db import models
from django.db.models import ForeignKey
from django.db.models.fields.related_descriptors import \
    ReverseOneToOneDescriptor
from django.db.transaction import atomic


class FlexibleForeignKey(ForeignKey):
    """ """

    def __init__(self, *args: Any, **kwargs: Any):
        kwargs.setdefault("on_delete", models.CASCADE)
        super().__init__(*args, **kwargs)


# Based on AutoOneToOneField from django-annoying:
# https://github.com/skorokithakis/django-annoying/blob/master/annoying/fields.py
class AutoSingleRelatedObjectDescriptor(ReverseOneToOneDescriptor):
    """
    The descriptor that handles the object creation for an AutoOneToOneField.
    """

    def __get__(self, instance, instance_type=None):
        model = getattr(self.related, "related_model", self.related.model)

        try:
            return super().__get__(instance, instance_type)
        except model.DoesNotExist:
            with atomic():
                # Using get_or_create instead() of save() or create()
                # as it better handles race conditions
                obj, _ = model.objects.get_or_create(
                    **{self.related.field.name: instance},
                )

            # Update Django's cache, otherwise first 2 calls to obj.relobj
            # will return 2 different in-memory objects
            self.related.set_cached_value(instance, obj)
            self.related.field.set_cached_value(obj, instance)
            return obj


class AutoOneToOneField(models.OneToOneField):
    """OneToOneField that creates related object if it doesn't exist."""

    def contribute_to_related_class(self, cls, related):
        setattr(
            cls,
            related.get_accessor_name(),
            AutoSingleRelatedObjectDescriptor(related),
        )
