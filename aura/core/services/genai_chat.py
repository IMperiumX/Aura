# TODO: Implement the following functions
# ref: https://stackoverflow.com/questions/76771761/why-does-llama-index-still-require-an-openai-key-when-using-hugging-face-local-e

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
#                     'This YouTube video transcript discusses the limitations of current AI coding tool',
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
#                     'Okay, let\'s analyz',
#                 ],
#             },
#         ]
#     )

#     response = chat_session.send_message("INSERT_INPUT_HERE")

#     print(response.text)
