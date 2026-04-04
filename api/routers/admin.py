"""Admin users and API keys."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import count_users, get_db_session, require_user
from quack_db.auth.api_keys import issue_api_key, verify_api_key
from quack_db.config import get_settings
from quack_db.db.models import ApiKey, User
from quack_db.services import mail

router = APIRouter(prefix="/admin", tags=["admin"])


class UserCreate(BaseModel):
    email: EmailStr
    tier: str = Field(..., pattern="^(everyone|students|members|board)$")
    is_dev_student: bool = False
    is_dev_admin: bool = False
    issue_key: bool = True


class UserPatch(BaseModel):
    tier: str | None = Field(None, pattern="^(everyone|students|members|board)$")
    is_dev_student: bool | None = None
    is_dev_admin: bool | None = None


def _is_full_admin(user: User) -> bool:
    return user.tier == "board" or user.is_dev_admin


def _require_admin(user: User) -> None:
    if not _is_full_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")


@router.post("/users")
def create_user(
    db: Annotated[Session, Depends(get_db_session)],
    body: UserCreate,
    x_admin_bootstrap: str | None = Header(None, alias="X-Admin-Bootstrap"),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    authorization: str | None = Header(None),
):
    """First user: `X-Admin-Bootstrap` when DB empty. Later: admin API key."""
    n = count_users(db)
    admin_user: User | None = None
    if n > 0:
        key = x_api_key
        if authorization and authorization.lower().startswith("bearer "):
            key = authorization[7:].strip()
        admin_user = verify_api_key(db, key)
        if admin_user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required")
        if admin_user.is_dev_student and not _is_full_admin(admin_user):
            if body.tier != "students":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="dev_student can only create students tier",
                )
        else:
            _require_admin(admin_user)
    else:
        settings = get_settings()
        if not settings.admin_bootstrap_key or x_admin_bootstrap != settings.admin_bootstrap_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or missing X-Admin-Bootstrap (empty database)",
            )
        if body.tier != "board" and not body.is_dev_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="First user must be tier=board or is_dev_admin=true",
            )

    existing = db.execute(select(User).where(User.email == str(body.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    u = User(
        email=str(body.email),
        tier=body.tier,
        is_dev_student=body.is_dev_student,
        is_dev_admin=body.is_dev_admin,
    )
    db.add(u)
    db.flush()

    out: dict = {"id": str(u.id), "email": u.email, "tier": u.tier}
    plaintext_key: str | None = None
    if body.issue_key:
        plaintext_key = issue_api_key(db, u)
    db.commit()

    if plaintext_key:
        try:
            mail.send_api_key_email(u.email, plaintext_key)
        except Exception:
            pass
        if n == 0:
            out["api_key"] = plaintext_key
            out["note"] = "One-time plaintext key for bootstrap; not repeated for later users."

    return out


@router.patch("/users/{user_id}")
def patch_user(
    db: Annotated[Session, Depends(get_db_session)],
    admin: Annotated[User, Depends(require_user)],
    user_id: uuid.UUID,
    body: UserPatch,
):
    _require_admin(admin)
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")
    if body.tier is not None:
        u.tier = body.tier
    if body.is_dev_student is not None:
        u.is_dev_student = body.is_dev_student
    if body.is_dev_admin is not None:
        u.is_dev_admin = body.is_dev_admin
    db.commit()
    return {"id": str(u.id), "email": u.email, "tier": u.tier}


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    db: Annotated[Session, Depends(get_db_session)],
    admin: Annotated[User, Depends(require_user)],
    user_id: uuid.UUID,
):
    _require_admin(admin)
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(u)
    db.commit()


@router.post("/users/{user_id}/keys")
def rotate_key(
    db: Annotated[Session, Depends(get_db_session)],
    admin: Annotated[User, Depends(require_user)],
    user_id: uuid.UUID,
):
    _require_admin(admin)
    if admin.is_dev_student and not _is_full_admin(admin):
        target = db.get(User, user_id)
        if target is None or target.tier != "students":
            raise HTTPException(status_code=403, detail="Can only rotate keys for students tier")

    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")
    plain = issue_api_key(db, u)
    db.commit()
    try:
        mail.send_api_key_email(u.email, plain)
    except Exception:
        pass
    return {"status": "ok", "message": "New key sent by email when SMTP is configured"}


@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_key(
    db: Annotated[Session, Depends(get_db_session)],
    admin: Annotated[User, Depends(require_user)],
    key_id: uuid.UUID,
):
    _require_admin(admin)
    row = db.get(ApiKey, key_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Key not found")
    row.revoked = True
    db.commit()
