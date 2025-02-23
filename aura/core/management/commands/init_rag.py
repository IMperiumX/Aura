from django.conf import settings
from django.core.management.base import BaseCommand

from aura.core.tasks import setup_rag_pipeline_task


class Command(BaseCommand):
    help = "Init celert task for embedding"

    def handle(self, *args, **options):
        if not settings.EMBEDDINGS_LOADED:
            setup_rag_pipeline_task.delay()
            self.stdout.write(self.style.SUCCESS("Embeddings setup task initiated"))
        else:
            self.stdout.write(self.style.SUCCESS("Embeddings already setup"))
