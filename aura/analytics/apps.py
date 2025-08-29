# ruff: noqa: PLC0415 F401

from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "aura.analytics"
    verbose_name = "Analytics"

    def ready(self):
        try:
            import aura.analytics.events
            import aura.analytics.signals
        except ImportError:
            pass
