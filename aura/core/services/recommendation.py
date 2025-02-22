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

# import logging
# import sys

# Uncomment to see debug logs
# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
# logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

# import textwrap

# import openai
# from django.conf import settings
# from llama_index.core import SimpleDirectoryReader
# from llama_index.core import StorageContext
# from llama_index.core import VectorStoreIndex
# from llama_index.vector_stores.postgres import PGVectorStore


# def generate_content(prompt: str):
#     from google import genai
#     from google.genai import types

#     client = genai.Client(api_key=settings.GEMINI_API_KEY)
#     chat = client.chats.create(
#         model="gemini-1.5-flash",
#         history=[
#             {
#                 "role": "user",
#                 "parts": ["test that"],
#             },
#             {
#                 "role": "model",
#                 "parts": ["Kosomak"],
#             },
#         ],
#     )

#     response = chat.send_message(message="Tell me a story in 100 words")
#     response = chat.send_message(message="What happened after that?")

#     # Create the model
#     response = client.models.generate_content(
#         model="gemini-1.5-flash",
#         contents="Tell me a story in 100 words.",
#         config=types.GenerateContentConfig(
#             system_instruction="you are a story teller for kids under 5 years old",
#             max_output_tokens=8192,
#             top_k=64,
#             top_p=0.95,
#             temperature=1,
#             response_mime_type="text/plain",
#             # stop_sequences=["\n"],
#             # seed=42,
#         ),
#     )

#     chat_session = model.start_chat(
#         history=[
#             {
#                 "role": "model",
#                 "parts": [
#                     'This YouTube video transcript discusses the limitations of current AI coding tools and the resulting opportunities for human developers. Here\'s a structured summary:\n\n**I. Initial Problem (0:00-0:50):**\n\n*   **Overwhelmed Codebase:** A developer describes a large, disorganized Python project (30+ files) that has become unmanageable.  Large Language Models (LLMs) like Claude struggle to understand the project\'s complexity, leading to incorrect optimizations, bug fixes, and even deletion of code.  The developer\'s lack of deep Python knowledge exacerbates the problem.\n*   **Failed Attempts:**  Using "cursor rules" (presumably referring to the Cursor code editor\'s features) to guide the AI hasn\'t resolved the issues.\n\n**II. Core Argument: AI Limitations and the "AI Gold Rush" (0:50-8:41):**\n\n*   **The "Madness of the Crowds":**  The speakers criticize the current hype surrounding AI in software development, fueled by social media and tech CEOs with vested interests in promoting AI.  They urge developers to conduct their own analysis and not blindly follow the hype.\n*   **Inference as a Feature and a Bug:**\n    *   **Inference:**  AI coding tools rely on *inference* (predicting the next code token based on statistical analysis of vast datasets).  This is presented as a fundamental limitation.\n    *   **The Myth of Exponential Improvement:**  The common belief is that larger models and datasets lead to exponentially better code quality. The speakers argue this is false.  Quality plateaus, and larger models are more prone to "hallucinations" (generating incorrect or irrelevant code).\n    *   **Circle of Experts (Mitigation Attempt):**  Some AI tools (like Dips) use a "circle of experts" approach – multiple specialized models for different tasks (e.g., JavaScript, math).  This attempts to address hallucinations.\n    *   **Legacy Code Generation:**  Training an AI on a specific codebase can lead to the generation of *more* legacy code, hindering adaptation to changing business needs and technology.  AI trained on a snapshot of the code cannot understand evolving real-world requirements.\n    *   **Statistical vs. Precise Answers:**  LLMs provide *statistical approximations*, which are computationally expensive and less reliable than precise solutions provided by tools like TypeScript (static typing) and IDE autocompletion.  Human developers excel at providing *precise* answers.\n* **The Bluff:** tech CEOs are exaggerating. The speakers state. The IT Market will need more developers.\n\n**III. Opportunities for Developers (8:41-End):**\n\n*   **Paralysis and Distraction:** Many developers are paralyzed by fear of AI or distracted by the "gold rush" of learning machine learning, neglecting to improve their core coding skills.\n*   **The Blockchain Analogy:**  This situation is compared to the blockchain hype, where many developers switched to blockchain development only to return to their original jobs when the bubble burst.\n*   **Getting Ahead:**  Developers who focus on honing their fundamental coding skills *now* will have a significant advantage in the future, as others are distracted or misled.\n*   **Do Your Own Analysis:**  The key message is to *not* blindly trust social media, tech CEOs, or the "crowd."  Developers should critically evaluate AI tools, understand their limitations, and focus on their own skills.  Human intelligence remains crucial.\n*   **Trust Yourself:** The speakers emphasize the importance of trusting one\'s own judgment and analysis, rather than relying on external sources.\n* **Conclusion:** AGI discussion is irrelvant while LLMs cannot properly handle 30 files.\n',
#                 ],
#             },
#             {
#                 "role": "user",
#                 "parts": [
#                     "analyse you prev answer and find any logical fallacies or missing information, etc.. and give a revised answer",
#                 ],
#             },
#             {
#                 "role": "model",
#                 "parts": [
#                     'Okay, let\'s analyze the previous summary and refine it.\n\n**Analysis of Previous Summary:**\n\n1.  **Missing Nuance on "Circle of Experts":** While the previous summary correctly identified the "circle of experts" as a mitigation technique, it didn\'t fully explore the limitations *within* that approach. The critique in the video goes beyond just legacy code; it implies that even specialized models within a circle can still suffer from the fundamental limitations of inference-based systems. The problem is that *any* model trained on a fixed dataset (even a specialized one) struggles to adapt to the *dynamic* nature of software development and business requirements.\n\n2.  **"Geometrically Expensive" Clarification:** The term "geometrically expensive" used in the transcript (and reflected in the summary) is a bit vague. It refers to the computational cost of inference. A more precise explanation is needed. The cost isn\'t just about the *size* of the model, but the *process* of traversing the weighted network for *every single predicted token*. This is inherently less efficient than, for example, static type checking.\n\n3.  **Overemphasis on "Precise" vs. "Statistical":** While the distinction is important, the previous summary might overstate the case. It\'s not that AI *never* provides useful suggestions; it\'s that the reliability and efficiency are significantly lower in complex, real-world codebases compared to established tools. The summary should better reflect the probabilistic nature of LLM outputs.\n\n4.  **Missing the "Validator" Point:** A crucial point from the transcript is that even with AI-generated code, a *human developer is still needed to validate* the output. This wasn\'t highlighted strongly enough in the previous summary. The AI acts as a suggestion tool, not a replacement for human judgment.\n\n5.  **Elon Musk/Twitter Example:** The previous summary included the Elon Musk/Twitter example, but didn\'t fully connect it back to the core argument. The point is that cutting engineering staff (as Musk did) and relying solely on AI (or the assumption of its capabilities) can lead to *decreased* product quality, proving that human developers are still essential.\n\n6.  **Slightly Overly Strong Conclusion:** While the original transcript\'s conclusion is strong, the previous summary\'s restatement ("AGI discussion is irrelevant while LLMs cannot properly handle 30 files") is a slight oversimplification. The point is that the current state of AI is *far* from achieving AGI, and the focus on AGI distracts from the real limitations and opportunities.\n\n**Revised Summary:**\n\nThis YouTube video transcript analyzes the current state of AI coding tools, argues against the hype surrounding them, and highlights the continued importance and opportunities for human developers.\n\n**I. The Problem: Large Codebases and AI Limitations (0:00-0:50):**\n\n*   **Unmanageable Project:** A developer describes a large, disorganized Python project (30+ files) that has become too complex for current LLMs (like Claude) to effectively assist with. This results in incorrect code modifications, bug fixes, and overall project degradation.\n*   **Failed Solutions:** Attempts to guide the AI using editor features ("cursor rules") have not resolved the underlying issues.\n\n**II. Core Argument: AI\'s Fundamental Flaws and the "AI Gold Rush" (0:50-8:41):**\n\n*   **The "AI Hype":** The speakers debunk the excessive optimism surrounding AI in software development, attributing it to social media influence and the self-interest of tech companies. They urge developers to critically evaluate AI\'s capabilities.\n*   **Inference: The Core Limitation:**\n    *   **Predictive, Not Deterministic:** AI coding tools rely on *inference*, predicting the next code token based on statistical probabilities derived from massive datasets. This is inherently different from the deterministic nature of traditional programming tools.\n    *   **The Plateau Effect:** Contrary to popular belief, increasing model size and data doesn\'t lead to exponentially better code. Quality improvements plateau, and larger models become more prone to generating incorrect or irrelevant code ("hallucinations").\n    *   **"Circle of Experts" - A Limited Solution:** Some AI tools use a "circle of experts" (multiple, specialized models for different coding tasks). While this *attempts* to reduce hallucinations, it doesn\'t solve the fundamental problem: models trained on fixed datasets (even specialized ones) struggle to adapt to the *dynamic* nature of software development and evolving business requirements.\n    *   **Legacy Code Trap:** Training an AI on a specific codebase risks generating *more* legacy code, as the AI is biased towards the existing (potentially outdated) patterns and cannot inherently understand the need for refactoring or adaptation to new technologies.\n    *   **Computational Inefficiency:** The inference process is computationally expensive. For each predicted token, the AI must traverse a vast, weighted network. This is significantly less efficient than traditional methods like static type checking (e.g., TypeScript) or IDE autocompletion, especially for large codebases.\n*   **The Bluff:** The video\'s presenters assert that tech CEOs are exaggerating AI\'s capabilities to sell their products, and the IT market needs *more* developers, not fewer.\n\n**III. Opportunities and Advice for Developers (8:41-End):**\n\n*   **Don\'t Be Distracted:** Many developers are either paralyzed by fear of AI or are wasting time pursuing machine learning careers, neglecting the development of core coding skills.\n*   **Learn from the Past (Blockchain Analogy):** This situation mirrors the blockchain hype, where many developers switched careers only to return when the bubble burst.\n*   **Focus on Fundamentals:** Developers who continue to improve their core coding skills *now* will gain a significant competitive advantage, as others are distracted by the AI hype.\n*   **Independent Analysis is Key:** The core message is to *reject* the uncritical acceptance of AI claims. Developers must conduct their own research, understand the limitations of current AI tools, and prioritize their own skill development.\n*   **Human Validation Remains Essential:** Even with AI-generated code suggestions, a human developer is *always* required to validate the output, correct errors, and ensure the code aligns with the overall project goals and evolving requirements. The AI is a tool, not a replacement.\n*   **The Twitter Example:** The degradation of Twitter\'s (X\'s) product quality after significant engineering staff cuts serves as a real-world example of the continued necessity of human developers.\n*   **Conclusion: Focus on Reality, Not Hype:** The discussion about Artificial General Intelligence (AGI) is premature and misleading, given the current limitations of AI in even relatively small codebases. The focus should be on mastering fundamental programming skills and critically evaluating the real-world capabilities of AI tools.\n\nThis revised summary addresses the identified shortcomings by:\n\n*   Providing a more nuanced explanation of the "circle of experts" and its limitations.\n*   Clarifying the computational cost of inference.\n*   Presenting a more balanced view of AI\'s capabilities (suggestions vs. replacements).\n*   Highlighting the crucial role of human validation.\n*   Better integrating the Elon Musk/Twitter example.\n*   Refining the conclusion to be less absolute but more accurate.\n* Adding specific time frames to catagories.\n',
#                 ],
#             },
#         ]
#     )

#     response = chat_session.send_message("INSERT_INPUT_HERE")

#     print(response.text)


# import re

# from django.conf import settings
# from llama_index.core import Document
# from llama_index.core import Settings
# from llama_index.core import StorageContext
# from llama_index.core import VectorStoreIndex
# from llama_index.core.node_parser import SentenceSplitter
# from llama_index.embeddings.huggingface import HuggingFaceEmbedding
# from llama_index.readers.database import DatabaseReader
# from llama_index.vector_stores.postgres import PGVectorStore
# from rest_framework.response import Response

# # open-source
# from transformers import AutoTokenizer

# # change chunk size and overlap without changing the default splitter
# Settings.chunk_size = 512
# Settings.chunk_overlap = 20

# CONTEXT_WINDOW = 3900
# DATABASE = settings.DATABASES["default"]


# class RecommendationEngine:
#     """
#     RAG pipeline

#     get data into an LLM, and a component of more sophisticated agentic systems.

#     Loading & Ingestion

#     Indexing and Embedding

#     Storing in a specialized database known as a Vector Store

#     Querying: Every indexing strategy has a corresponding querying strategy, LLM improve the relevance, speed and accuracy of what you retrieve before returning it to you.

#     Turning it into structured responses such as an API.
#     """

#     def get_therapist_recommendations(self, health_assessment):
#         from pgvector.django import CosineDistance

#         from aura.users.models import Therapist

#         return Therapist.objects.annotate(
#             similarity=CosineDistance("embedding", health_assessment.embedding),
#         ).order_by("-similarity")

#     def find_best_match(self, health_assessment):
#         return self.get_therapist_recommendations(health_assessment).first()

#     def fetch_documents_from_storage(self, query: str) -> list[Document]:
#         reader = DatabaseReader(
#             scheme="postgresql",
#             host=DATABASE["HOST"],
#             port=DATABASE["PORT"],
#             user=DATABASE["USER"],
#             password=DATABASE["PASSWORD"],
#             dbname=DATABASE["NAME"],
#         )
#         return reader.load_data(query=query)

#     def save_embeddings(self, documents: list[Document]) -> None:
#         # TODO: post_save for intentded models
#         from assessments.models import PatientAssessment

#         query = str(
#             PatientAssessment.objects.only(
#                 "responses",
#                 "result",
#                 "recommendations",
#             ).query,
#         )
#         documents = self.fetch_documents_from_storage(query=query)
#         for document in documents:
#             assessment_id = re.search(r"\d+", document.text).group(0)

#             assessment = PatientAssessment.objects.get(pk=assessment_id)

#             embedding = Settings.embed_model.get_text_embedding(document.text)
#             assessment.embedding = embedding

#             assessment.save()

#     def setup_pgvector_store(self):
#         return PGVectorStore.from_params(
#             database=DATABASE["NAME"],
#             host=DATABASE["HOST"],
#             password=DATABASE["PASSWORD"],
#             port=DATABASE["PORT"],
#             user=DATABASE["USER"],
#             table_name="assessment_embeddings",  # XXX: data_{table_name}
#             embed_dim=settings.EMBEDDING_MODEL_DIMENSIONS,  # Must match your embedding model
#         )

#     def _provide_context(self):
#         from llama_index.llms.llama_cpp import LlamaCPP
#         from llama_index.llms.llama_cpp.llama_utils import completion_to_prompt
#         from llama_index.llms.llama_cpp.llama_utils import messages_to_prompt

#         Settings.text_splitter = SentenceSplitter(chunk_size=1024)

#         llm = LlamaCPP(
#             model_path=settings.LLAMA_GGUFF_MODEL_PATH,
#             context_window=CONTEXT_WINDOW,  # Tune to your model - Mixtral 8x7b is a beast.
#             max_new_tokens=256,
#             # set to at least 1 to use GPU
#             model_kwargs={"n_gpu_layers": settings.USE_GPU},
#             verbose=True,
#             # transform inputs into Llama2 format
#             messages_to_prompt=messages_to_prompt,
#             completion_to_prompt=completion_to_prompt,
#         )
#         Settings.llm = llm

#         embed_model = HuggingFaceEmbedding(
#             model_name=settings.EMBED_MODEL_NAME,
#             embed_batch_size=10,
#             cache_dir=settings.LLAMA_INDEX_CACHE_DIR,
#         )
#         Settings.embed_model = embed_model
#         # compatible with the open-source LLM.
#         Settings.tokenzier = AutoTokenizer.from_pretrained(
#             settings.TOKENIZER_NAME,
#         )

#         Settings.context_window = CONTEXT_WINDOW

#     def generate_vector_store_index(
#         self,
#         vector_store: PGVectorStore,
#         documents: list[Document],
#     ) -> VectorStoreIndex:
#         storage_context = StorageContext.from_defaults(vector_store=vector_store)
#         return VectorStoreIndex.from_documents(
#             documents,
#             storage_context=storage_context,
#             embed_model=Settings.embed_model,
#             show_progress=True,
#         )

#     def recommend_therapist(self, k=3):
#         from assessments.models import Assessment

#         fields = (
#             "responses",
#             "result",
#             "recommendations",
#         )
#         query = str(Assessment.objects.only(*fields).query)
#         documents = self.fetch_documents_from_storage(query)

#         vector_store = self.setup_pgvector_store()
#         index = self.generate_vector_store_index(
#             documents=documents,
#             vector_store=vector_store,
#         )

#         query_engine = index.as_query_engine(
#             similarity_top_k=k,
#         )
#         response = query_engine.query("Best Therapist for me?")
#         return Response(response)
