"""
## TODOs
- Implementing more sophisticated recommendation algorithms based on
    - [x] Patient profiles and related models.
    - [x] vector similarity search for Postgres
    - [x] Custom Querysets
    - [x] machine learning models.
    - [x] Building a RAG pipeline
- Incorporating user feedback on recommendations to improve future suggestions.
"""

import re

from django.conf import settings
from llama_index.core import Document
from llama_index.core import Settings
from llama_index.core import StorageContext
from llama_index.core import VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.readers.database import DatabaseReader
from llama_index.vector_stores.postgres import PGVectorStore
from rest_framework.response import Response

# open-source
from transformers import AutoTokenizer

# change chunk size and overlap without changing the default splitter
Settings.chunk_size = 512
Settings.chunk_overlap = 20

CONTEXT_WINDOW = 3900
DATABASE = settings.DATABASES["default"]


class RecommendationEngine:
    """
    RAG pipeline

    get data into an LLM, and a component of more sophisticated agentic systems.

    Loading & Ingestion

    Indexing and Embedding

    Storing in a specialized database known as a Vector Store

    Querying: Every indexing strategy has a corresponding querying strategy, LLM improve the relevance, speed and accuracy of what you retrieve before returning it to you.

    Turning it into structured responses such as an API.
    """

    def get_therapist_recommendations(self, health_assessment):
        from pgvector.django import CosineDistance

        from aura.users.models import Therapist

        return Therapist.objects.annotate(
            similarity=CosineDistance("embedding", health_assessment.embedding),
        ).order_by("-similarity")

    def find_best_match(self, health_assessment):
        return self.get_therapist_recommendations(health_assessment).first()

    def fetch_documents_from_storage(self, query: str) -> list[Document]:
        reader = DatabaseReader(
            scheme="postgresql",
            host=DATABASE["HOST"],
            port=DATABASE["PORT"],
            user=DATABASE["USER"],
            password=DATABASE["PASSWORD"],
            dbname=DATABASE["NAME"],
        )
        return reader.load_data(query=query)

    def save_embeddings(self, documents: list[Document]) -> None:
        # TODO: post_save for intentded models
        from assessments.models import Assessment

        query = str(
            Assessment.objects.only(
                "responses",
                "result",
                "recommendations",
            ).query,
        )
        documents = self.fetch_documents_from_storage(query=query)
        for document in documents:
            assessment_id = re.search(r"\d+", document.text).group(0)

            assessment = Assessment.objects.get(pk=assessment_id)

            embedding = Settings.embed_model.get_text_embedding(document.text)
            assessment.embedding = embedding

            assessment.save()

    def setup_pgvector_store(self):
        return PGVectorStore.from_params(
            database=DATABASE["NAME"],
            host=DATABASE["HOST"],
            password=DATABASE["PASSWORD"],
            port=DATABASE["PORT"],
            user=DATABASE["USER"],
            table_name="assessment_embeddings",  # XXX: data_{table_name}
            embed_dim=settings.EMBEDDING_MODEL_DIMENSIONS,  # Must match your embedding model
        )

    def _provide_context(self):
        from llama_index.llms.llama_cpp import LlamaCPP
        from llama_index.llms.llama_cpp.llama_utils import completion_to_prompt
        from llama_index.llms.llama_cpp.llama_utils import messages_to_prompt

        Settings.text_splitter = SentenceSplitter(chunk_size=1024)

        llm = LlamaCPP(
            model_path=settings.LLAMA_GGUFF_MODEL_PATH,
            context_window=CONTEXT_WINDOW,  # Tune to your model - Mixtral 8x7b is a beast.
            max_new_tokens=256,
            # set to at least 1 to use GPU
            model_kwargs={"n_gpu_layers": settings.USE_GPU},
            verbose=True,
            # transform inputs into Llama2 format
            messages_to_prompt=messages_to_prompt,
            completion_to_prompt=completion_to_prompt,
        )
        Settings.llm = llm

        embed_model = HuggingFaceEmbedding(
            model_name=settings.EMBED_MODEL_NAME,
            embed_batch_size=10,
            cache_dir=settings.LLAMA_INDEX_CACHE_DIR,
        )
        Settings.embed_model = embed_model
        # compatible with the open-source LLM.
        Settings.tokenzier = AutoTokenizer.from_pretrained(
            settings.TOKENIZER_NAME,
        )

        Settings.context_window = CONTEXT_WINDOW

    def generate_vector_store_index(
        self,
        vector_store: PGVectorStore,
        documents: list[Document],
    ) -> VectorStoreIndex:
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        return VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            embed_model=Settings.embed_model,
            show_progress=True,
        )

    def recommend_therapist(self, k=3):
        from assessments.models import Assessment

        fields = (
            "responses",
            "result",
            "recommendations",
        )
        query = str(Assessment.objects.only(*fields).query)
        documents = self.fetch_documents_from_storage(query)

        vector_store = self.setup_pgvector_store()
        index = self.generate_vector_store_index(
            documents=documents,
            vector_store=vector_store,
        )

        query_engine = index.as_query_engine(
            similarity_top_k=k,
        )
        response = query_engine.query("Best Therapist for me?")
        return Response(response)
