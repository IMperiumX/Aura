from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "aura.core"

    def ready(self):
        import aura.core.schema  # noqa: F401
