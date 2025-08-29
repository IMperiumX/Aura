from django.apps import AppConfig


class PatientflowConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "aura.patientflow"
    verbose_name = "Patient Flow Board"

    def ready(self):
        import aura.patientflow.signals  # noqa
