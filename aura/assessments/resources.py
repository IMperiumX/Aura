from typing import TYPE_CHECKING

from import_export import fields
from import_export import resources
from import_export.widgets import ForeignKeyWidget
from import_export.widgets import ManyToManyWidget

from aura.mentalhealth.models import Disorder

if TYPE_CHECKING:
    from django.db.models import QuerySet


class AssessmentResource(resources.ModelResource):
    class Meta:
        model = "assessments.Assessment"


# use this approach instead of overriding `before_import_row()`
# as there is a flow in the import process https://github.com/django-import-export/django-import-export/pull/2029
# issue: https://github.com/django-import-export/django-import-export/issues/2027
# Related SO issue: https://stackoverflow.com/questions/79402682/django-import-export-import-foreign-keys-that-do-not-exist/79403936#79403936
class AuthorForeignKeyWidget(ForeignKeyWidget):
    def clean(self, value, row=None, **kwargs):
        try:
            val = super().clean(value)
        except Disorder.DoesNotExist:
            val = Disorder.objects.create(name=row.get("disorder", None))
        return val


# reference: https://github.com/django-import-export/django-import-export/issues/318#issuecomment-861813245
class ManyToManyWidgetWithCreation(ManyToManyWidget):
    """A many-to-many widget that creates any objects that don't already exist."""

    def __init__(self, model, field="pk", create=False, **kwargs):
        self.model = model
        self.field = field
        self.create = create
        super().__init__(model, field=field, **kwargs)

        def clean(self, value, **kwargs):
            # If no value was passed then we don't have anything to clean.

            if not value:
                return self.model.objects.none()

            # Call the super method. This will return a QuerySet containing any pre-existing objects.
            # Any missing objects will be

            cleaned_value: QuerySet = super().clean(value, **kwargs)

            # Value will be a string that is separated by `self.separator`.
            # Each entry in the list will be a reference to an object. If the object exists it will
            # appear in the cleaned_value results. If the number of objects in the cleaned_value
            # results matches the number of objects in the delimited list then all objects already
            # exist and we can just return those results.

            object_list = value.split(self.separator)

            if len(cleaned_value.all()) == len(object_list):
                return cleaned_value

            # If we are creating new objects then loop over each object in the list and
            # use get_or_create to, um, get or create the object.

            if self.create:
                for object_value in object_list:
                    _instance, _new = self.model.objects.get_or_create(
                        **{self.field: object_value},
                    )

            # Use `filter` to re-locate all the objects in the list.

            return self.model.objects.filter(
                **{f"{self.field}__in": object_list},
            )


class MyThingModelResource(resources.ModelResource):
    categories = fields.Field(
        column_name="categories",
        attribute="categories",
        widget=ManyToManyWidgetWithCreation(
            model=Disorder,
            field="name",
            separator="|",
            create=True,
        ),
        default="",
    )
