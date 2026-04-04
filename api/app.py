"""FastAPI service for authenticated query and ingestion access."""
from __future__ import annotations

import logging
import os
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.auth import RequireAccess, RequireIngestAccess, RequireRestrictedAccess
from api.models import IngestRequest, QueryRequest, QueryResponse
from api.rate_limit import RateLimitMiddleware
from app_config import (
    ALLOW_PROD_INGEST,
    API_AUTH_REQUIRED,
    APP_ENV,
    API_RATE_LIMIT_PER_MINUTE,
    ENTRA_AUDIENCE,
    ENTRA_AUTH_ENABLED,
    ENTRA_ISSUER,
    ENTRA_JWKS_URL,
)
from ingest.ingest import ingest_directory
from services.rag_query import query_rag

logger = logging.getLogger("quack.api")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

app = FastAPI(title="Quack DB API", version="1.0.0")
app.add_middleware(RateLimitMiddleware, requests_per_minute=API_RATE_LIMIT_PER_MINUTE)


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    logger.info(
        "request path=%s method=%s status=%s request_id=%s auth_method=%s auth_subject=%s",
        request.url.path,
        request.method,
        response.status_code,
        getattr(request.state, "request_id", "unknown"),
        getattr(request.state, "auth_method", "none"),
        getattr(request.state, "auth_subject", "unknown"),
    )
    return response


def _auth_config_errors() -> list[str]:
    errors = []
    if API_AUTH_REQUIRED and ENTRA_AUTH_ENABLED:
        if not ENTRA_JWKS_URL:
            errors.append("ENTRA_JWKS_URL must be set when ENTRA_AUTH_ENABLED=true.")
        if not ENTRA_AUDIENCE:
            errors.append("ENTRA_AUDIENCE should be set for audience validation.")
        if not ENTRA_ISSUER:
            errors.append("ENTRA_ISSUER should be set for issuer validation.")
    return errors


@app.get("/health")
def health():
    return {
        "status": "ok",
        "auth_required": API_AUTH_REQUIRED,
        "entra_enabled": ENTRA_AUTH_ENABLED,
        "auth_config_errors": _auth_config_errors(),
    }


@app.post("/query", response_model=QueryResponse)
def query(payload: QueryRequest, _auth=RequireAccess):
    response_text, context_text, metadatas = query_rag(
        query_text=payload.query_text,
        collection_name=payload.collection,
        n_results=payload.n_results,
        model=payload.model,
        debug=payload.debug,
    )
    return QueryResponse(
        response_text=response_text,
        context_text=context_text,
        metadatas=metadatas,
    )


@app.post("/query/restricted", response_model=QueryResponse)
def query_restricted(payload: QueryRequest, _auth=RequireRestrictedAccess):
    return query(payload, _auth)


@app.post("/admin/ingest")
def ingest(payload: IngestRequest, _auth=RequireIngestAccess):
    if APP_ENV == "prod" and not ALLOW_PROD_INGEST:
        return JSONResponse(
            status_code=403,
            content={"detail": "Ingest is disabled in prod. Enable ALLOW_PROD_INGEST to allow it."},
        )
    chunks = ingest_directory(
        data_dir=payload.data_dir,
        collection_name=payload.collection,
        chunk_size=payload.chunk_size,
        overlap=payload.overlap,
        file_pattern=payload.file_pattern,
    )
    return {"status": "ok", "chunks_added": chunks}


@app.exception_handler(Exception)
async def handle_exception(_request: Request, exc: Exception):
    logger.exception("Unhandled API exception: %s", exc)
    return JSONResponse(status_code=500, content={"detail": f"Internal server error: {exc}"})

