"""
## TODOs
- Implementing more sophisticated recommendation algorithms based on
    - [x] Patient profiles and related models.
    - [x] vector similarity search for Postgres
    - [x] Custom Querysets
    - [ ] machine learning models.
- Incorporating user feedback on recommendations to improve future suggestions.
"""

# import re

# from llama_index import Document, download_loader
# from llama_index.embeddings import HuggingFaceEmbedding

# You would cache this
# EMBED_MODEL = HuggingFaceEmbedding(
#     model_name="WhereIsAI/UAE-Large-V1",
#     embed_batch_size=10,  # open-source embedding model
# )


class RecommendationEngine:
    def get_therapist_recommendations(self, health_assessment):
        from pgvector.django import CosineDistance

        from aura.users.models import Therapist

        return Therapist.objects.annotate(
            similarity=CosineDistance("embedding", health_assessment.embedding),
        ).order_by("-similarity")

    def find_best_match(self, health_assessment):
        return self.get_therapist_recommendations(health_assessment).first()

    # @classmethod
    # def get_mental_health_recommendations(cls, health_assessment):
    #     from aura.assessments.models import HealthAssessment, HealthRiskPrediction

    #     if (
    #         health_assessment.assessment_type
    #         != HealthAssessment.AssessmentType.MENTAL_HEALTH
    #     ):
    #         return []

    #     risk_level = health_assessment.risk_level
    #     responses = health_assessment.responses

    #     # Get base recommendations based on risk level
    #     recommendations = HealthRiskPrediction.objects.filter(risk_level=risk_level)

    #     # Personalize recommendations based on assessment responses
    #     return [rec for rec in recommendations if cls._is_relevant(rec, responses)]

    # @staticmethod
    # def _is_relevant(recommendation, responses):
    #     # Implement logic to determine if a recommendation is relevant
    #     # based on the user's responses
    #     # This is a simplified example and
    #     return (
    #         "anxiety" in responses
    #         and "anxiety" in recommendation.category.lower()
    #         or "depression" in responses
    #         and "depression" in recommendation.category.lower()
    #     )

    # @staticmethod
    # def find_best_match(assessment):
    #     # TODO: Refactor with llama_index.HuggingFaceEmbedding
    #     import numpy as np
    #     from sklearn.metrics.pairwise import cosine_similarity

    #     from aura.users.models import Therapist

    #     therapists = Therapist.objects.all()
    #     assessment_embedding = np.array(assessment.embedding).reshape(1, -1)

    #     best_match = None
    #     highest_similarity = -1

    #     for therapist in therapists:
    #         therapist_embedding = np.array(therapist.embedding).reshape(1, -1)
    #         similarity = cosine_similarity(assessment_embedding, therapist_embedding)[
    #             0
    #         ][0]

    #         if similarity > highest_similarity:
    #             highest_similarity = similarity
    #             best_match = therapist

    #     return best_match

    # def fetch_documents_from_storage(self, query: str) -> list[Document]:
    #     # Prep documents - fetch from DB
    #     from django.conf import settings
    #     db_url = settings.DATABASES["default"]

    #     DatabaseReader = download_loader("DatabaseReader")
    #     reader = DatabaseReader(
    #         scheme="postgresql",  # Database Scheme
    #         host=db_url["HOST"],  # Database Host
    #         port=db_url["PORT"],  # Database Port
    #         user=db_url["USER"],  # Database User
    #         password=db_url["PASSWORD"],  # Database Password
    #         dbname=db_url["NAME"],  # Database Name
    #     )
    #     return reader.load_data(query=query)

    # def save_embeddings(self, documents: list[Document]) -> None:
    #     query = f"""
    #     SELECT e.episode_number, e.title, t.content
    #     FROM transcriber_episode e
    #     LEFT JOIN transcriber_transcript t ON e.id = t.episode_id;
    #     """
    #     documents = self.fetch_documents_from_storage(query=query)
    #     for document in documents:
    #         match = re.match(r"^(\d{1,3})", document.text)
    #         if match:
    #             episode_number = int(
    #                 match.group(1)
    #             )  # Convert to int for exact matching

    #         # Fetch the episode using get() for a single object
    #         # episode = Episode.objects.get(episode_number=episode_number)

    #         # transcript = classmethod.objects.get(episode=episode)

    #         # # Generate and save the embedding
    #         # embedding = EMBED_MODEL.get_text_embedding(document.text)
    #         # transcript.embedding = embedding

    #         # #XXX: We will make further use of these embeddings next.
    #         # transcript.save()

    # def setup_pgvector_store(self):
    #     from urllib.parse import urlparse

    #     from llama_index.vector_stores import PGVectorStore

    #     from django.conf import settings

    #     # settings are omitted for brevity, but a Postgres URL looks like this:
    #     # postgresql://postgres:ff@localhost:5432/aura

    #     db_url = settings.DATABASES["default"]
    #     parsed_url = urlparse(db_url)
    #     vector_store = PGVectorStore.from_params(
    #         database=db_configs["NAME"],
    #         host=db_configs["HOST"],
    #         password=db_configs["PASSWORD"],
    #         port=db_configs["PORT"],
    #         user=db_configs["USER"],
    #         table_name="assessment_embeddings", #XXX: Update if needed prefixed with `data_` => (data_podcast_embeddings)
    #         embed_dim=settings.EMBEDDING_MODEL_DIMENSIONS,  # Must match your embedding model
    #     )

    # def _provide_context(self):
    #     from llama_index.llms import LlamaCPP
    #     from llama_index.embeddings import HuggingFaceEmbedding
    #     from llama_index import set_global_tokenizer, ServiceContext
    #     from transformers import AutoTokenizer

    #     llm = LlamaCPP(
    #                 model_path="path/to/your/GGUF/model",  # Download the GGUF from hugging face
    #                 context_window=30000,  # Tune to your model - Mixtral 8x7b is a beast.
    #                 max_new_tokens=1024,
    #                 model_kwargs={"n_gpu_layers": 1},  # >=1 means using GPU. 0 means using CPU.
    #                 verbose=True,
    #             )

    #     embed_model = HuggingFaceEmbedding(
    #         model_name="WhereIsAI/UAE-Large-V1", embed_batch_size=10  # open-source embedding model
    #     )

    #     # set_global_tokenizer to be compatible with the open-source LLM.
    #     set_global_tokenizer(
    #         AutoTokenizer.from_pretrained(f"mistralai/Mixtral-8x7B-Instruct-v0.1").encode)  # must match your LLM

    #     service_context = ServiceContext.from_defaults(
    #         llm=llm,
    #         embed_model=embed_model,
    #         system_prompt="You are a bot that answers questions in English.",
    #     )

    # def recommend_therapist(self):
    #     from llama_index import (
    #         ServiceContext,
    #         VectorStoreIndex,
    #         StorageContext,
    #         Document,
    #     )
    #     from llama_index.vector_stores import PGVectorStore

    #     def generate_vector_store_index(
    #         vector_store: PGVectorStore,
    #         documents: list[Document],
    #         service_context: ServiceContext,
    #     ) -> VectorStoreIndex:
    #         storage_context = StorageContext.from_defaults(vector_store=vector_store)
    #         return VectorStoreIndex.from_documents(
    #             documents,
    #             storage_context=storage_context,
    #             service_context=service_context,
    #             show_progress=True,
    #         )

    #     index = generate_vector_store_index(
    #         documents=documents,  # We fetched these in step 3
    #         service_context=service_context,  # We prepped this in step 6
    #         vector_store=vector_store,  # We prepped this in step 5
    #     )
    #     query_engine = index.as_query_engine(
    #         similarity_top_k=3,
    #     )
    #     response = query_engine.query(f"Who is Dylan Patel?")
