import os

from llama_index.core import Settings
from llama_index.embeddings.gemini import GeminiEmbedding
from llama_index.llms.gemini import Gemini


def init_settings():
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is missing in environment variables")

    # Sử dụng Gemini Flash Lite
    Settings.llm = Gemini(
        model=os.getenv("MODEL") or "models/gemini-3.1-flash-lite",
        api_key=api_key,
    )
    # Sử dụng Embedding model của Google
    Settings.embed_model = GeminiEmbedding(
        model_name=os.getenv("EMBEDDING_MODEL") or "models/gemini-embedding-001",
        api_key=api_key,
    )
