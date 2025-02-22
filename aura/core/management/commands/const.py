import logging
import sys

from apps.jumpserver.const import CONFIG
from django.conf import settings

try:
    from apps.aura import const

    __version__ = const.VERSION
except ImportError:
    logging.exception("Not found __version__: ")
    logging.info("Python is: ")
    logging.info(sys.executable)
    __version__ = "Unknown"
    sys.exit(1)

HTTP_HOST = CONFIG.HTTP_BIND_HOST or "127.0.0.1"
HTTP_PORT = CONFIG.HTTP_LISTEN_PORT or 8080
WS_PORT = CONFIG.WS_LISTEN_PORT or 8082
DEBUG = CONFIG.DEBUG or False
BASE_DIR = settings.BASE_DIR
LOG_DIR = BASE_DIR / "data/logs"
APPS_DIR = BASE_DIR / "apps"
TMP_DIR = BASE_DIR / "tmp"
