"""Authorization helpers for Chroma collection operations."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from quack_db.authz import matrix
from quack_db.db.models import User


def resolve_repo_or_404(collection_name: str, user: User) -> str:
    repo = matrix.resolve_repo(collection_name, user.id)
    if repo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown collection")
    return repo


def require_rwmd(
    user: User,
    repo: str,
    *,
    read: bool = False,
    write: bool = False,
    modify: bool = False,
    delete: bool = False,
) -> None:
    p = matrix.rwmd_for_repo(user, repo)
    if read and not p.read:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read not allowed")
    if write and not p.write:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Write not allowed")
    if modify and not p.modify:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Modify not allowed")
    if delete and not p.delete:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Delete not allowed")


def merge_where(
    server: dict[str, Any] | None,
    client: dict[str, Any] | None,
) -> dict[str, Any] | None:
    parts = [p for p in (server, client) if p]
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return {"$and": parts}
