"""Factory helpers for Chroma HTTP clients."""
from __future__ import annotations

from urllib.parse import urlparse

import chromadb
from chromadb.config import Settings

from app_config import CHROMADB_AUTH_TOKEN, CHROMADB_HOST, CHROMADB_PORT, CHROMADB_SSL


def _connection_kwargs() -> dict:
    raw_host = CHROMADB_HOST.strip()
    host = raw_host
    port = CHROMADB_PORT
    ssl = CHROMADB_SSL

    if raw_host.startswith("http://") or raw_host.startswith("https://"):
        parsed = urlparse(raw_host)
        host = parsed.hostname or host
        if parsed.port:
            port = parsed.port
        ssl = parsed.scheme == "https"

    kwargs = {"host": host, "port": port, "ssl": ssl}
    if CHROMADB_AUTH_TOKEN:
        kwargs["settings"] = Settings(
            chroma_client_auth_provider="chromadb.auth.token_authn.TokenAuthClientProvider",
            chroma_client_auth_credentials=CHROMADB_AUTH_TOKEN,
        )
    return kwargs


def create_http_client() -> chromadb.HttpClient:
    return chromadb.HttpClient(**_connection_kwargs())

