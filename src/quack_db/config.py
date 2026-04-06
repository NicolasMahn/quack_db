"""Environment-backed settings (API + workers)."""

from functools import lru_cache

from pydantic import ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLite file (default): cheap for small data. Docker image sets DATABASE_URL=/app/data/...
    # Postgres: `postgresql+psycopg://user:pass@host:5432/db` and `pip install -e ".[postgres]"`.
    database_url: str = "sqlite:///./quack.db"

    admin_bootstrap_key: str = ""

    # Microsoft Entra ID — JWT validation (v2.0 + legacy v1 issuers; see entra_tenant_id defaults).
    entra_jwks_url: str = ""
    entra_audience: str = ""
    entra_issuer: str = ""
    # When set, fills ENTRA_ISSUER / ENTRA_JWKS_URL with the usual single-tenant v2.0 URLs
    # if those are empty (stable defaults from the directory (tenant) ID).
    entra_tenant_id: str = ""

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

    # GitHub Actions / Container Apps often inject missing vars as "" which breaks bool/int parsing.
    @field_validator("auth_disabled", "smtp_use_tls", "run_migrations_on_startup", mode="before")
    @classmethod
    def _empty_string_bool_defaults(cls, v, info: ValidationInfo):
        defaults = {
            "auth_disabled": False,
            "smtp_use_tls": True,
            "run_migrations_on_startup": True,
        }
        if v is None or v == "":
            return defaults[info.field_name]
        return v

    @field_validator("smtp_port", "rag_n_results_cap", "chroma_n_results_cap", mode="before")
    @classmethod
    def _empty_string_int_defaults(cls, v, info: ValidationInfo):
        defaults = {
            "smtp_port": 587,
            "rag_n_results_cap": 50,
            "chroma_n_results_cap": 100,
        }
        if v is None or v == "":
            return defaults[info.field_name]
        return v

    @field_validator("azure_openai_nano_temperature", mode="before")
    @classmethod
    def _empty_string_float_default(cls, v):
        if v is None or v == "":
            return 1.0
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

    @field_validator("entra_jwks_url", "entra_audience", mode="after")
    @classmethod
    def _normalize_entra_urls_and_audience(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            return v
        return v.rstrip("/")

    @field_validator("entra_issuer", mode="after")
    @classmethod
    def _normalize_entra_issuer(cls, v: str) -> str:
        # Do not strip trailing "/" — v1 tokens use https://sts.windows.net/<tid>/
        return (v or "").strip()

    @field_validator("entra_tenant_id", mode="after")
    @classmethod
    def _normalize_entra_tenant_id(cls, v: str) -> str:
        return (v or "").strip()

    @model_validator(mode="after")
    def _entra_defaults_from_tenant_id(self):
        tid = self.entra_tenant_id
        if not tid:
            return self
        if not self.entra_issuer:
            # Device code / some clients issue v1.0 tokens (iss sts.windows.net); others use v2.0.
            self.entra_issuer = (
                f"https://login.microsoftonline.com/{tid}/v2.0,"
                f"https://sts.windows.net/{tid}/"
            )
        if not self.entra_jwks_url:
            self.entra_jwks_url = (
                f"https://login.microsoftonline.com/{tid}/discovery/v2.0/keys"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
