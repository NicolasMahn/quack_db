"""FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from quack_db.auth.api_keys import verify_api_key
from quack_db.db.models import User
from quack_db.db.session import get_db

# FastAPI dependency alias
get_db_session = get_db


def _extract_key(
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> str | None:
    if x_api_key:
        return x_api_key
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def require_user(
    db: Annotated[Session, Depends(get_db_session)],
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> User:
    key = _extract_key(authorization, x_api_key)
    user = verify_api_key(db, key)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return user


def optional_user(
    db: Annotated[Session, Depends(get_db_session)],
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> User | None:
    key = _extract_key(authorization, x_api_key)
    if not key:
        return None
    return verify_api_key(db, key)


def count_users(db: Session) -> int:
    from quack_db.db.models import User as U

    return int(db.execute(select(func.count()).select_from(U)).scalar_one())
