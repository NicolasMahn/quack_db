"""Application configuration shared across UI, API and ingestion jobs."""
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

# Azure OpenAI
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv(
    "AZURE_OPENAI_ENDPOINT",
    "https://quackgpt-llm.openai.azure.com/",
)
AZURE_DEFAULT_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

# Optional legacy Chroma client token. Self-hosted Chroma Rust server ignores it.
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

# Direct Chroma connectivity (used by API and ingest worker only in prod).
CHROMADB_HOST = os.getenv("CHROMADB_HOST", "127.0.0.1")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8000"))
CHROMADB_SSL = _env_bool("CHROMADB_SSL", default=False)

# Frontend-to-API connectivity.
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8001")
API_TIMEOUT_SECONDS = float(os.getenv("API_TIMEOUT_SECONDS", "30"))
API_CLIENT_KEY = os.getenv("API_CLIENT_KEY", "")
API_INGEST_CLIENT_KEY = os.getenv("API_INGEST_CLIENT_KEY", "")
API_BEARER_TOKEN = os.getenv("API_BEARER_TOKEN", "")
RAG_EXECUTION_MODE = os.getenv("RAG_EXECUTION_MODE", "api").strip().lower()
INGEST_EXECUTION_MODE = os.getenv("INGEST_EXECUTION_MODE", RAG_EXECUTION_MODE).strip().lower()
ENABLE_UI_INGEST = _env_bool("ENABLE_UI_INGEST", default=False)
ALLOW_PROD_INGEST = _env_bool("ALLOW_PROD_INGEST", default=False)

# API runtime controls.
API_AUTH_REQUIRED = _env_bool("API_AUTH_REQUIRED", default=True)
API_KEYS = _env_csv("API_KEYS")
API_INGEST_KEYS = _env_csv("API_INGEST_KEYS")
API_RATE_LIMIT_PER_MINUTE = int(os.getenv("API_RATE_LIMIT_PER_MINUTE", "120"))

# Entra JWT validation config.
ENTRA_AUTH_ENABLED = _env_bool("ENTRA_AUTH_ENABLED", default=False)
ENTRA_TENANT_ID = os.getenv("ENTRA_TENANT_ID", "")
ENTRA_AUDIENCE = os.getenv("ENTRA_AUDIENCE", "")
ENTRA_ISSUER = os.getenv("ENTRA_ISSUER", "")
ENTRA_JWKS_URL = os.getenv("ENTRA_JWKS_URL", "")
RESTRICTED_ROLES = _env_csv("RESTRICTED_ROLES", default="quack.restricted")
INGEST_ROLES = _env_csv("INGEST_ROLES", default="quack.ingest")

# Collections exposed by frontend selector.
COLLECTIONS = _env_csv("COLLECTIONS", default="test")
DEFAULT_COLLECTION = os.getenv("DEFAULT_COLLECTION", COLLECTIONS[0] if COLLECTIONS else "test")
