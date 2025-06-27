from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "aura.core"
    verbose_name = "Core"

    def ready(self):
        """Initialize core components when the app is ready."""
        # Import and patch cache instrumentation
        try:
            from aura.core.cache_instrumentation import patch_django_cache

            patch_django_cache()
        except ImportError:
            pass  # Cache instrumentation is optional
        import aura.core.schema  # noqa: F401
