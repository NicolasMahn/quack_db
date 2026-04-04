"""API key generation and verification."""

from __future__ import annotations

import secrets

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from quack_db.db.models import ApiKey, User

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _random_key() -> str:
    return f"qk_{secrets.token_urlsafe(32)}"


def key_prefix(full_key: str) -> str:
    return full_key[:16]


def issue_api_key(db: Session, user: User) -> str:
    """Create a new API key; returns plaintext once (store hash only)."""
    plain = _random_key()
    prefix = key_prefix(plain)
    h = _pwd.hash(plain)
    row = ApiKey(user_id=user.id, prefix=prefix, key_hash=h, revoked=False)
    db.add(row)
    db.flush()
    return plain


def verify_api_key(db: Session, full_key: str | None) -> User | None:
    if not full_key or len(full_key) < 8:
        return None
    prefix = key_prefix(full_key)
    row = db.execute(
        select(ApiKey).where(ApiKey.prefix == prefix, ApiKey.revoked.is_(False))
    ).scalar_one_or_none()
    if row is None:
        return None
    if not _pwd.verify(full_key, row.key_hash):
        return None
    user = db.get(User, row.user_id)
    return user
