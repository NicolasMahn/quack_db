"""Environment-backed settings (API + workers)."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLite file (default): cheap for small data. Docker image sets DATABASE_URL=/app/data/...
    # Postgres: `postgresql+psycopg://user:pass@host:5432/db` and `pip install -e ".[postgres]"`.
    database_url: str = "sqlite:///./quack.db"

    admin_bootstrap_key: str = ""

    # Microsoft Entra ID — access tokens for this API (v2.0, delegated or app).
    entra_jwks_url: str = ""
    entra_audience: str = ""
    entra_issuer: str = ""

    # First-time login: create a DB user with this tier (e.g. "everyone") if set.
    # Empty => admin must pre-register users by email.
    entra_auto_provision_tier: str = ""

    # Local / CI only: skip JWT and use this existing user row by email.
    auth_disabled: bool = False
    dev_impersonate_user_email: str = ""

    chromadb_host: str = "localhost"
    chromadb_port: int = 8000
    chromadb_auth_token: str = ""

    @field_validator("chromadb_port", mode="before")
    @classmethod
    def _empty_chromadb_port_to_default(cls, v):
        if v is None or v == "":
            return 8000
        return v

    azure_openai_endpoint: str = "https://example.openai.azure.com/"
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-02-15-preview"

    azure_openai_embedding_endpoint: str = ""
    azure_openai_embedding_api_key: str = ""
    azure_openai_embedding_deployment: str = "text-embedding-ada-002"

    azure_openai_nano_endpoint: str = ""
    azure_openai_nano_api_key: str = ""
    azure_openai_nano_deployment: str = "gpt-4o-mini"
    azure_openai_nano_temperature: float = 1.0

    google_api_key: str = ""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True

    run_migrations_on_startup: bool = True

    rag_n_results_cap: int = 50
    chroma_n_results_cap: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings()
