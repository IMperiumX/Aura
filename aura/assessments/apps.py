from django.apps import AppConfig


class AssessmentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "aura.assessments"

    def ready(self):
        import aura.core.schema  # noqa: F401
