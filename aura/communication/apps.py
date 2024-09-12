from django.apps import AppConfig


class CommunicationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "aura.communication"

    def ready(self):
        import aura.core.schema  # noqa: F401
