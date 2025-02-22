#!/usr/bin/env python3

import argparse
import logging
import os
import sys
import time
from pathlib import Path

import django
from django.core import management
from django.db.utils import OperationalError

BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR / "aura"


os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jumpserver.settings")
django.setup()

logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


def check_database_connection():
    for i in range(60):
        msg = f"Check database connection: {i}"
        logging.info(msg)
        try:
            management.call_command("check", "--database", "default")
        except OperationalError:
            logging.info("Database not setup, retry")
        except Exception:
            logging.exception("Unexpect error occur")
        else:
            logging.info("Database connect success")
            return
        time.sleep(1)
    logging.error("Connection database failed, exit")
    sys.exit(10)


def collect_static():
    logging.info("Collect static files")
    try:
        management.call_command(
            "collectstatic",
            "--no-input",
            "-c",
            verbosity=0,
            interactive=False,
        )
        logging.info("Collect static files done")
    except Exception:
        logging.exception("Collect static files failed")


def perform_db_migrate():
    logging.info("Check database structure change ...")
    logging.info("Migrate model change to database ...")

    try:
        management.call_command("migrate")
    except Exception:
        logging.exception("Perform migrate failed")
        raise


def upgrade_db():
    collect_static()
    perform_db_migrate()


def prepare():
    check_database_connection()
    upgrade_db()


def start_services():
    services = args.services if isinstance(args.services, list) else [args.services]
    if action == "start" and {"all", "web"} & set(services):
        prepare()

    start_args = []
    if args.daemon:
        start_args.append("--daemon")
    if args.force:
        start_args.append("--force")
    if args.worker:
        start_args.extend(["--worker", str(args.worker)])
    else:
        worker = os.environ.get("CORE_WORKER")
        if isinstance(worker, str) and worker.isdigit():
            start_args.extend(["--worker", worker])

    try:
        management.call_command(action, *services, *start_args)
    except KeyboardInterrupt:
        logging.info("Cancel ...")
        time.sleep(2)
    except Exception as exc:
        msg = f"Start service error {services}: {exc}"
        logging.exception(msg)
        time.sleep(2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""
        Aura service control tools;

        Example: \r\n

        %(prog)s start all -d;
        """,
    )
    parser.add_argument(
        "action",
        type=str,
        choices=("start", "stop", "restart", "status", "upgrade_db", "collect_static"),
        help="Action to run",
    )
    parser.add_argument(
        "services",
        type=str,
        default="all",
        nargs="*",
        choices=("all", "web", "task"),
        help="The service to start",
    )
    parser.add_argument("-d", "--daemon", nargs="?", const=True)
    parser.add_argument("-w", "--worker", type=int, nargs="?")
    parser.add_argument("-f", "--force", nargs="?", const=True)

    args = parser.parse_args()

    action = args.action
    start_services()
