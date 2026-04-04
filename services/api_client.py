"""HTTP client for calling Quack API endpoints."""
from __future__ import annotations

import httpx

from app_config import (
    API_BASE_URL,
    API_BEARER_TOKEN,
    API_CLIENT_KEY,
    API_INGEST_CLIENT_KEY,
    API_TIMEOUT_SECONDS,
)


def _headers(*, for_ingest: bool = False) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    api_key = API_INGEST_CLIENT_KEY if for_ingest and API_INGEST_CLIENT_KEY else API_CLIENT_KEY
    if api_key:
        headers["X-API-Key"] = api_key
    if API_BEARER_TOKEN:
        headers["Authorization"] = f"Bearer {API_BEARER_TOKEN}"
    return headers


def query_rag_api(
    *,
    query_text: str,
    collection_name: str,
    n_results: int = 3,
    model: str = "default",
    debug: bool = False,
    restricted: bool = False,
) -> tuple[str, str, list[dict]]:
    endpoint = "/query/restricted" if restricted else "/query"
    url = f"{API_BASE_URL.rstrip('/')}{endpoint}"
    payload = {
        "query_text": query_text,
        "collection": collection_name,
        "n_results": n_results,
        "model": model,
        "debug": debug,
    }
    with httpx.Client(timeout=API_TIMEOUT_SECONDS) as client:
        response = client.post(url, json=payload, headers=_headers())
    response.raise_for_status()
    data = response.json()
    return data["response_text"], data.get("context_text", ""), data.get("metadatas", [])


def ingest_via_api(
    *,
    data_dir: str,
    collection: str,
    chunk_size: int = 1200,
    overlap: int = 200,
    file_pattern: str = "**/*",
) -> int:
    url = f"{API_BASE_URL.rstrip('/')}/admin/ingest"
    payload = {
        "data_dir": data_dir,
        "collection": collection,
        "chunk_size": chunk_size,
        "overlap": overlap,
        "file_pattern": file_pattern,
    }
    with httpx.Client(timeout=API_TIMEOUT_SECONDS) as client:
        response = client.post(url, json=payload, headers=_headers(for_ingest=True))
    response.raise_for_status()
    body = response.json()
    return int(body.get("chunks_added", 0))

