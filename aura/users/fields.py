from typing import Any

from django.db import models
from django.db.models import ForeignKey
from django.db.models.fields.related_descriptors import ReverseOneToOneDescriptor


class FlexibleForeignKey(ForeignKey):
    """ """

    def __init__(self, *args: Any, **kwargs: Any):
        kwargs.setdefault("on_delete", models.CASCADE)
        super().__init__(*args, **kwargs)


# Based on AutoOneToOneField from django-annoying:
# https://github.com/skorokithakis/django-annoying/blob/master/annoying/fields.py


class AutoSingleRelatedObjectDescriptor(ReverseOneToOneDescriptor):
    """Descriptor for access to the object from its related class."""

    def __get__(self, instance, instance_type=None):
        try:
            return super().__get__(instance, instance_type)
        except self.related.related_model.DoesNotExist:
            obj = self.related.related_model(**{self.related.field.name: instance})
            obj.save()
            return obj


class AutoOneToOneField(models.OneToOneField):
    """OneToOneField that creates related object if it doesn't exist."""

    def contribute_to_related_class(self, cls, related):
        setattr(
            cls,
            related.get_accessor_name(),
            AutoSingleRelatedObjectDescriptor(related),
        )
