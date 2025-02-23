"""
## TODOs
- Implementing more sophisticated recommendation algorithms
  moving beyond simple keyword matching or even basic similarity search to a system that can
  intelligently match patients and therapists based on a variety of factors.
    - [x] Custom Querysets: gives a fine-grained control over how you fetch data from the database.
    - [x] vector similarity search for Postgres
    - [x] Using all the relevant information from related models to inform the matching process.
    - [X] RAG(core): Using the pgvector extension in PostgreSQL to perform efficient
        similarity searches based on the embeddings
        of the patient assessments and therapist profiles.
    - [x] Building a RAG pipeline
        - [x] Retrieval: Finding relevant documents (in this case, therapist profiles) based on the patient's information.
        - [x] Generation: Using an LLM (Llama.cpp) to generate a tailored recommendation, taking into account the retrieved information.
    - [x] Using pre-trained Llama.cpp model and HuggingFaceEmbedding
- Incorporating user feedback on recommendations to improve future suggestions.
  Feedback helps to fine-tune the matching algorithm over time.
  Helps address the "cold start" problem.
"""

from django.conf import settings as django_settings
from llama_index.core import Settings
from llama_index.core import StorageContext
from llama_index.core import VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.vector_stores.types import BasePydanticVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.llama_cpp import LlamaCPP
from llama_index.readers.database import DatabaseReader
from llama_index.vector_stores.postgres import PGVectorStore
from rest_framework.response import Response

from aura.assessments.models import PatientAssessment
from aura.core.utils import _get_db_connection_params
from aura.core.utils import completion_to_prompt
from aura.core.utils import messages_to_prompt

CONTEXT_WINDOW = 8096
DEFAULT_DOCUMETNS_QUERY = str(
    PatientAssessment.objects.only(
        "result",
        "recommendations",
    ).query,
)
Settings.context_window = CONTEXT_WINDOW
Settings.text_splitter = SentenceSplitter(chunk_size=1024)


class RAGSystem:
    _embed_model = None
    _llm = None
    _vector_store: BasePydanticVectorStore | None = None
    _index: VectorStoreIndex | None = None
    _query_engine = None

    SIMILARITY_TOP_K = 3
    MAX_NEW_TOKENS = 384

    TABLE_NAME = "assessment_embeddings"

    @classmethod
    def _create_pg_vector_store(cls) -> PGVectorStore:
        """Creates and configures the PGVectorStore."""
        return PGVectorStore.from_params(
            **_get_db_connection_params(),
            table_name=cls.TABLE_NAME,  # XXX: data_{table_name}
            embed_dim=django_settings.EMBEDDING_MODEL_DIMENSIONS,
            hnsw_kwargs={  # Consider moving HNSW params to env vars or settings
                "hnsw_m": 16,
                "hnsw_ef_construction": 64,
                "hnsw_ef_search": 40,
                "hnsw_dist_method": "vector_cosine_ops",
            },
        )

    def setup_embed_model(self) -> HuggingFaceEmbedding:
        """Lazily initializes the embedding model."""
        if self._embed_model is None:
            self._embed_model = HuggingFaceEmbedding(
                model_name=django_settings.EMBED_MODEL_NAME,
            )
        Settings.embed_model = self._embed_model

    def setup_llm(self) -> LlamaCPP:
        """Lazily initializes the LlamaCPP LLM."""
        if self._llm is None:
            self._llm = LlamaCPP(
                model_url=django_settings.LLAMA_GGUFF_MODEL_URL,
                temperature=0.1,
                max_new_tokens=self.MAX_NEW_TOKENS,
                context_window=self.CONTEXT_WINDOW,
                generate_kwargs={},
                model_kwargs={
                    "n_gpu_layers": django_settings.USE_GPU,
                },
                messages_to_prompt=messages_to_prompt,
                completion_to_prompt=completion_to_prompt,
                verbose=True,
            )
        Settings.llm = self.llm

    def setup_vector_store(self) -> BasePydanticVectorStore:
        """Lazily initializes the PGVectorStore."""
        if self._vector_store is None:
            self._vector_store = self._create_pg_vector_store()

    def setup_index(self) -> VectorStoreIndex:
        """Lazily initializes the VectorStoreIndex."""
        if self._index is not None:
            return

        self.setup_vector_store()
        self.setup_embed_model()

        # Check if the table exists and has data
        if not self._vector_store.table_exists:
            # If table doesn't exists, we create the documents
            # Load data ONLY if the index is empty or doesn't exist.
            documents = self.load_data()
            storage_context = StorageContext.from_defaults(
                vector_store=self._vector_store,
            )
            self._index = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context,
                show_progress=True,
                embed_model=self._embed_model,  # Use the lazy getter.
            )
        else:  # The table exists, we assume it has content
            self._index = VectorStoreIndex.from_vector_store(
                vector_store=self._vector_store,
                show_progress=True,
            )

    def setup_query_engine(self):
        """Lazily initializes the query engine."""
        if self._query_engine is None:
            self._query_engine = self.setup_index().as_query_engine(
                similarity_top_k=self.SIMILARITY_TOP_K,
            )

    def load_data(self, query=None):
        """Loads data from the database using a raw SQL query."""
        query = query or DEFAULT_DOCUMETNS_QUERY
        # Using DatabaseReader with a raw SQL query.
        reader = DatabaseReader(**_get_db_connection_params())
        return reader.load_data(query=query)

    @property
    def embed_model(self) -> HuggingFaceEmbedding:
        """Get the embedding model."""
        return self._embed_model

    @property
    def llm(self) -> LlamaCPP:
        """Get the LlamaCPP model."""
        return self._llm

    @property
    def vector_store(self) -> BasePydanticVectorStore:
        """Get the vector store."""
        return self._vector_store

    @property
    def index(self) -> VectorStoreIndex:
        """Get the vector store index."""
        return self._index

    @property
    def query_engine(self):
        """Get the query engine."""
        return self._query_engine
