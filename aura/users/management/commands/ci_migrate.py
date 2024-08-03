import click
from django.conf import settings
from django.core.management import call_command as dj_call_command
from django.core.management.base import (BaseCommand, CommandError,
                                         CommandParser)
from django.db import connections
from django.db.utils import ProgrammingError


def _check_history() -> None:
    connection = connections["default"]
    cursor = connection.cursor()
    try:
        # If this query fails because there are no tables we're good to go.
        cursor.execute("SELECT COUNT(*) FROM django_migrations")
        row = cursor.fetchone()
        if not row or row[0] == 0:
            return
    except ProgrammingError as e:
        # Having no migrations table is ok, as we're likely operating on a new install.
        if 'relation "django_migrations" does not exist' in str(e):
            return
        click.echo(f"Checking migration state failed with: {e}")
        msg = "Could not determine migration state. Aborting"
        raise click.ClickException(msg) from e


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def add_arguments(self, parser: CommandParser) -> None:
        # Named (optional) arguments
        parser.add_argument(
            "--noinput",
            action="store_true",
            default=False,
            help="Do not prompt the user for input of any kind.",
        )

    def handle(self, *args, **options):
        try:
            self._upgrade()
        except Exception as e:
            msg = f"ERROR HERE: {e}"
            raise CommandError(msg) from e
        self.stdout.write(self.style.SUCCESS("Successfully applied migrations"))

    def _upgrade(
        self,
    ) -> None:
        _check_history()

        for db_conn in settings.DATABASES:
            msg = f"Running migrations for {db_conn}"
            self.stdout.write(self.style.SUCCESS(msg))
            dj_call_command(
                "migrate",
                database=db_conn,
                traceback=True,
                verbosity=1,
            )
            dj_call_command(
                "showmigrations",
                database=db_conn,
                traceback=True,
                verbosity=1,
            )
