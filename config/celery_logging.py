from logging.config import dictConfig

from celery.signals import after_setup_logger
from django.conf import settings


@after_setup_logger.connect
def setup_celery_logging(**kwargs):
    """
    This function is connected to the `after_setup_logger` signal from Celery.
    It replaces the default Celery logger configuration with the one defined
    in the Django settings `LOGGING` dictionary.

    This ensures that Celery workers and the main Django application use a
    consistent, structured logging format, which is crucial for centralized
    log management and analysis in production environments.

    By using the `dictConfig`, we apply the entire logging configuration,
    including formatters, handlers, and filters, making Celery's output
    uniform with the rest of the system.
    """
    dictConfig(settings.LOGGING)
