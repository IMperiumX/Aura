from aura.core.management.commands.const import *

from .base import BaseService

__all__ = ["GunicornService"]


class GunicornService(BaseService):
    def __init__(self, **kwargs):
        self.worker = kwargs["worker_gunicorn"]
        super().__init__(**kwargs)

    @property
    def cmd(self):
        print("\n- YUSUF Start Gunicorn WSGI HTTP Server")

        log_format = '%(h)s %(t)s %(L)ss "%(r)s" %(s)s %(b)s '
        bind = f"{HTTP_HOST}:{HTTP_PORT}"

        cmd = [
            "gunicorn",
            "jumpserver.asgi:application",
            "-b",
            bind,
            "-k",
            "uvicorn.workers.UvicornWorker",
            "-w",
            str(self.worker),
            "--max-requests",
            "10240",
            "--max-requests-jitter",
            "2048",
            "--graceful-timeout",
            "30",
            "--access-logformat",
            log_format,
        ]
        if DEBUG:
            cmd.append("--reload")
        return cmd

    @property
    def cwd(self):
        return APPS_DIR

    def start_other(self):
        from terminal.startup import CoreTerminal

        core_terminal = CoreTerminal()
        # core_terminal.start_heartbeat_thread()
