"""
Secrets / environment configuration.
Load API keys and service URLs from environment variables (.env).
"""
import os

from dotenv import load_dotenv

load_dotenv()

# Azure OpenAI (shared fallbacks)
AZURE_OPENAI_ENDPOINT = os.environ.get(
    "AZURE_OPENAI_ENDPOINT", "https://quackgpt-llm.openai.azure.com/"
)
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

# Embedding model (optional overrides; falls back to shared endpoint/key)
AZURE_OPENAI_EMBEDDING_ENDPOINT = (
    os.environ.get("AZURE_OPENAI_EMBEDDING_ENDPOINT") or AZURE_OPENAI_ENDPOINT
)
AZURE_OPENAI_EMBEDDING_API_KEY = (
    os.environ.get("AZURE_OPENAI_EMBEDDING_API_KEY") or AZURE_OPENAI_API_KEY
)
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = (
    os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "").strip()
    or "text-embedding-ada-002"
)

# Nano / chat model (optional overrides; falls back to shared endpoint/key)
AZURE_OPENAI_NANO_ENDPOINT = (
    os.environ.get("AZURE_OPENAI_NANO_ENDPOINT") or AZURE_OPENAI_ENDPOINT
)
AZURE_OPENAI_NANO_API_KEY = (
    os.environ.get("AZURE_OPENAI_NANO_API_KEY") or AZURE_OPENAI_API_KEY
)
AZURE_OPENAI_NANO_DEPLOYMENT = (
    os.environ.get("AZURE_OPENAI_NANO_DEPLOYMENT", "").strip() or "gpt-4o-mini"
)
# Nano/reasoning models (o1, o1-mini) only support temperature=1
AZURE_OPENAI_NANO_TEMPERATURE = float(
    os.environ.get("AZURE_OPENAI_NANO_TEMPERATURE", "1")
)

# Optional: Google (for Gemini models)
GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY", "")

# ChromaDB
CHROMADB_HOST = os.environ.get("CHROMADB_HOST", "localhost")
CHROMADB_PORT = int(os.environ.get("CHROMADB_PORT", "8000"))
CHROMADB_AUTH_TOKEN = os.environ.get("CHROMADB_AUTH_TOKEN", "")
