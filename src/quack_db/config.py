"""Environment-backed settings (API + workers)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/quack"

    admin_bootstrap_key: str = ""

    chromadb_host: str = "localhost"
    chromadb_port: int = 8000
    chromadb_auth_token: str = ""

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
