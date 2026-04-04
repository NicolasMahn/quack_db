"""Thin Chroma proxy with RBAC."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.chroma_access import merge_where, require_rwmd, resolve_repo_or_404
from api.deps import require_user
from quack_db.authz import matrix
from quack_db.chroma.client import get_chroma_client
from quack_db.db.models import User
from quack_db.services.embedding import get_embedding_function

router = APIRouter(prefix="/collections", tags=["collections"])


def _server_where(repo: str, user: User) -> dict | None:
    if repo == "user_agent_context":
        return {"user_id": str(user.id)}
    return None


def _get_collection(name: str):
    client = get_chroma_client()
    try:
        return client.get_collection(name)
    except Exception:
        raise HTTPException(status_code=404, detail="Collection not found") from None


@router.get("")
def list_collections(
    user: Annotated[User, Depends(require_user)],
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    allowed = set(matrix.list_readable_collections(user))
    client = get_chroma_client()
    all_cols = client.list_collections()
    names = sorted({c.name for c in all_cols if c.name in allowed})
    slice_ = names[offset : offset + limit]
    return {"collections": [{"name": n} for n in slice_], "total": len(names)}


class CreateCollectionBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=512)
    metadata: dict[str, Any] | None = None


@router.post("")
def create_collection(user: Annotated[User, Depends(require_user)], body: CreateCollectionBody):
    repo = resolve_repo_or_404(body.name, user)
    require_rwmd(user, repo, write=True)
    client = get_chroma_client()
    try:
        client.create_collection(
            name=body.name,
            metadata=body.metadata or {},
            embedding_function=get_embedding_function(),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"name": body.name}


@router.get("/{name}")
def get_collection_meta(user: Annotated[User, Depends(require_user)], name: str):
    repo = resolve_repo_or_404(name, user)
    require_rwmd(user, repo, read=True)
    col = _get_collection(name)
    return {"name": name, "metadata": col.metadata or {}}


class ModifyCollectionBody(BaseModel):
    new_name: str | None = None
    metadata: dict[str, Any] | None = None


@router.patch("/{name}")
def modify_collection(
    user: Annotated[User, Depends(require_user)],
    name: str,
    body: ModifyCollectionBody,
):
    repo = resolve_repo_or_404(name, user)
    require_rwmd(user, repo, modify=True)
    col = _get_collection(name)
    try:
        col.modify(metadata=body.metadata, new_name=body.new_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"status": "ok"}


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection_endpoint(user: Annotated[User, Depends(require_user)], name: str):
    repo = resolve_repo_or_404(name, user)
    require_rwmd(user, repo, delete=True)
    try:
        get_chroma_client().delete_collection(name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{name}/count")
def count_collection(user: Annotated[User, Depends(require_user)], name: str):
    repo = resolve_repo_or_404(name, user)
    require_rwmd(user, repo, read=True)
    col = _get_collection(name)
    return {"count": col.count()}


@router.get("/{name}/peek")
def peek_collection(
    user: Annotated[User, Depends(require_user)], name: str, limit: int = Query(10, ge=1, le=100)
):
    repo = resolve_repo_or_404(name, user)
    require_rwmd(user, repo, read=True)
    col = _get_collection(name)
    try:
        return col.peek(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class AddBody(BaseModel):
    ids: list[str]
    documents: list[str] | None = None
    metadatas: list[dict[str, Any]] | None = None
    embeddings: list[list[float]] | None = None


@router.post("/{name}/add")
def add_records(
    user: Annotated[User, Depends(require_user)],
    name: str,
    body: AddBody,
):
    repo = resolve_repo_or_404(name, user)
    require_rwmd(user, repo, write=True)
    col = _get_collection(name)
    metas = list(body.metadatas) if body.metadatas else [{} for _ in body.ids]
    for i, m in enumerate(metas):
        m = dict(m)
        if repo == "user_agent_context":
            m["user_id"] = str(user.id)
        metas[i] = m
    try:
        col.add(
            ids=body.ids,
            documents=body.documents,
            metadatas=metas,
            embeddings=body.embeddings,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"status": "ok", "added": len(body.ids)}


class QueryBody(BaseModel):
    query_embeddings: list[list[float]] | None = None
    query_texts: list[str] | None = None
    n_results: int = 10
    where: dict[str, Any] | None = None
    where_document: dict[str, Any] | None = None
    include: list[str] | None = None


@router.post("/{name}/query")
def query_collection(user: Annotated[User, Depends(require_user)], name: str, body: QueryBody):
    repo = resolve_repo_or_404(name, user)
    require_rwmd(user, repo, read=True)
    col = _get_collection(name)
    n = min(body.n_results, 100)
    merged = merge_where(_server_where(repo, user), body.where)
    try:
        return col.query(
            query_embeddings=body.query_embeddings,
            query_texts=body.query_texts,
            n_results=n,
            where=merged,
            where_document=body.where_document,
            include=body.include,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class GetBody(BaseModel):
    ids: list[str] | None = None
    where: dict[str, Any] | None = None
    limit: int | None = None
    offset: int | None = None
    where_document: dict[str, Any] | None = None
    include: list[str] | None = None


@router.post("/{name}/get")
def get_records(user: Annotated[User, Depends(require_user)], name: str, body: GetBody):
    repo = resolve_repo_or_404(name, user)
    require_rwmd(user, repo, read=True)
    col = _get_collection(name)
    merged = merge_where(_server_where(repo, user), body.where)
    try:
        return col.get(
            ids=body.ids,
            where=merged,
            limit=body.limit,
            offset=body.offset,
            where_document=body.where_document,
            include=body.include,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class UpdateBody(BaseModel):
    ids: list[str] | None = None
    where: dict[str, Any] | None = None
    documents: list[str] | None = None
    metadatas: list[dict[str, Any]] | None = None
    embeddings: list[list[float]] | None = None


@router.post("/{name}/update")
def update_records(user: Annotated[User, Depends(require_user)], name: str, body: UpdateBody):
    repo = resolve_repo_or_404(name, user)
    require_rwmd(user, repo, modify=True)
    col = _get_collection(name)
    merged = merge_where(_server_where(repo, user), body.where)
    try:
        col.update(
            ids=body.ids,
            where=merged,
            documents=body.documents,
            metadatas=body.metadatas,
            embeddings=body.embeddings,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"status": "ok"}


class UpsertBody(BaseModel):
    ids: list[str]
    documents: list[str] | None = None
    metadatas: list[dict[str, Any]] | None = None
    embeddings: list[list[float]] | None = None


@router.post("/{name}/upsert")
def upsert_records(user: Annotated[User, Depends(require_user)], name: str, body: UpsertBody):
    repo = resolve_repo_or_404(name, user)
    require_rwmd(user, repo, write=True)
    col = _get_collection(name)
    metas = list(body.metadatas) if body.metadatas else [{} for _ in body.ids]
    for i, m in enumerate(metas):
        m = dict(m)
        if repo == "user_agent_context":
            m["user_id"] = str(user.id)
        metas[i] = m
    try:
        col.upsert(
            ids=body.ids,
            documents=body.documents,
            metadatas=metas,
            embeddings=body.embeddings,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"status": "ok"}


class DeleteRecordsBody(BaseModel):
    ids: list[str] | None = None
    where: dict[str, Any] | None = None
    where_document: dict[str, Any] | None = None


@router.post("/{name}/delete")
def delete_records(
    user: Annotated[User, Depends(require_user)],
    name: str,
    body: DeleteRecordsBody,
):
    repo = resolve_repo_or_404(name, user)
    require_rwmd(user, repo, delete=True)
    col = _get_collection(name)
    merged = merge_where(_server_where(repo, user), body.where)
    try:
        col.delete(ids=body.ids, where=merged, where_document=body.where_document)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"status": "ok"}
