from celery import shared_task
from django.conf import settings as django_settings

db = django_settings.DATABASES[django_settings.DATABASE_CONNECTION_DEFAULT_NAME]


@shared_task
def setup_rag_pipeline_task():
    """Celery task to initialize embedding model (and potentially LLM)."""
    from aura.core.services.recommendation import RAGSystem

    rag_system = RAGSystem()
    rag_system.setup_query_engine()

    django_settings.EMBEDDINGS_LOADED = True
    return rag_system
