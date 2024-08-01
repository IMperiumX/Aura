import contextlib

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "aura.users"
    verbose_name = _("Users")

    def ready(self):
        with contextlib.suppress(ImportError):
            import aura.users.signals  # noqa: F401
            from aura import \
                schema  # https://drf-spectacular.readthedocs.io/en/latest/blueprints.html
