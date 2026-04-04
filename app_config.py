"""Shared config for optional Dash UI / local tools (API uses `quack_db.config.Settings`)."""
import os

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_csv(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


APP_ENV = os.getenv("APP_ENV", "dev").strip().lower()

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv(
    "AZURE_OPENAI_ENDPOINT",
    "https://quackgpt-llm.openai.azure.com/",
)
AZURE_DEFAULT_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

CHROMADB_AUTH_TOKEN = os.getenv("CHROMADB_AUTH_TOKEN")

MODELS = {
    "gpt-5-nano": {
        "endpoint": "openai/deployments/gpt-5-nano/chat/completions",
        "api_version": "2025-01-01-preview",
        "deployment": "gpt-5-nano",
        "temperature_setable": False,
        "embedding": False,
    },
    "text-embedding-3-large": {
        "endpoint": "openai/deployments/text-embedding-3-large/embeddings",
        "api_version": "2023-05-15",
        "temperature_setable": False,
        "embedding": True,
    },
}

CHROMADB_HOST = os.getenv("CHROMADB_HOST", "127.0.0.1")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8000"))

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8001")
API_TIMEOUT_SECONDS = float(os.getenv("API_TIMEOUT_SECONDS", "30"))
API_BEARER_TOKEN = os.getenv("API_BEARER_TOKEN", "")
ENABLE_UI_INGEST = _env_bool("ENABLE_UI_INGEST", default=False)

COLLECTIONS = _env_csv("COLLECTIONS", default="test")
DEFAULT_COLLECTION = os.getenv("DEFAULT_COLLECTION", COLLECTIONS[0] if COLLECTIONS else "test")
