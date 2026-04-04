"""Chroma HttpClient for server-side calls."""

from functools import lru_cache

import chromadb
from chromadb.config import Settings

from quack_db.config import get_settings


@lru_cache
def get_chroma_client() -> chromadb.HttpClient:
    s = get_settings()
    kwargs: dict = {"host": s.chromadb_host, "port": s.chromadb_port}
    if s.chromadb_auth_token:
        kwargs["settings"] = Settings(
            chroma_client_auth_provider="chromadb.auth.token_authn.TokenAuthClientProvider",
            chroma_client_auth_credentials=s.chromadb_auth_token,
        )
    return chromadb.HttpClient(**kwargs)
