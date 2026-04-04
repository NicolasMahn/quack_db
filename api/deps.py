"""FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from quack_db.auth.entra_jwt import verify_entra_jwt
from quack_db.config import get_settings
from quack_db.db.models import User
from quack_db.db.session import get_db

get_db_session = get_db


def _extract_bearer(authorization: str | None) -> str:
    if not authorization:
        return ""
    prefix = "bearer "
    value = authorization.strip()
    if value.lower().startswith(prefix):
        return value[len(prefix) :].strip()
    return ""


def require_user_from_bearer(db: Session, authorization: str | None) -> User:
    s = get_settings()
    if s.auth_disabled:
        if not s.dev_impersonate_user_email:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="auth_disabled requires dev_impersonate_user_email.",
            )
        user = db.execute(
            select(User).where(User.email == s.dev_impersonate_user_email)
        ).scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Dev impersonation user not found.",
            )
        return user

    token = _extract_bearer(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization: Bearer <Entra access token for this API> required.",
        )

    try:
        claims = verify_entra_jwt(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid bearer token: {exc}",
        ) from exc

    oid = claims.get("oid") or claims.get("sub")
    if not oid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing oid/sub claim.",
        )
    oid_s = str(oid)
    raw_email = claims.get("email") or claims.get("preferred_username")
    if not raw_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing email / preferred_username.",
        )
    email = str(raw_email).strip().lower()

    user = db.execute(select(User).where(User.entra_oid == oid_s)).scalar_one_or_none()
    if user is None:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is not None and user.entra_oid is None:
            user.entra_oid = oid_s
            db.commit()
            db.refresh(user)

    if user is None and s.entra_auto_provision_tier:
        user = User(
            email=email,
            entra_oid=oid_s,
            tier=s.entra_auto_provision_tier,
            is_dev_student=False,
            is_dev_admin=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "No Quack user for this identity. Ask an admin to create your account "
                "(email must match Entra)."
            ),
        )
    return user


def require_user(
    db: Annotated[Session, Depends(get_db_session)],
    authorization: str | None = Header(None),
) -> User:
    return require_user_from_bearer(db, authorization)


def optional_user(
    db: Annotated[Session, Depends(get_db_session)],
    authorization: str | None = Header(None),
) -> User | None:
    s = get_settings()
    if s.auth_disabled:
        return require_user_from_bearer(db, authorization)
    if not _extract_bearer(authorization):
        return None
    try:
        return require_user_from_bearer(db, authorization)
    except HTTPException:
        return None


def count_users(db: Session) -> int:
    from quack_db.db.models import User as U

    return int(db.execute(select(func.count()).select_from(U)).scalar_one())
