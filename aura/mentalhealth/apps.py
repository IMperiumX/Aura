from django.apps import AppConfig


class MentalhealthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "aura.mentalhealth"

    def ready(self):
        import aura.core.schema  # noqa: F401
