"""Admin users (Microsoft Entra is the only auth path — no API keys)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import count_users, get_db_session, require_user, require_user_from_bearer
from quack_db.config import get_settings
from quack_db.db.models import User

router = APIRouter(prefix="/admin", tags=["admin"])


class UserCreate(BaseModel):
    email: EmailStr
    tier: str = Field(..., pattern="^(everyone|students|members|board)$")
    is_dev_student: bool = False
    is_dev_admin: bool = False


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
    authorization: str | None = Header(None),
):
    """First user: bootstrap header when DB empty. Later: Entra token for a board/dev_admin user."""
    n = count_users(db)
    if n > 0:
        admin_user = require_user_from_bearer(db, authorization)
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

    email_norm = str(body.email).lower()
    existing = db.execute(select(User).where(User.email == email_norm)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    u = User(
        email=email_norm,
        tier=body.tier,
        is_dev_student=body.is_dev_student,
        is_dev_admin=body.is_dev_admin,
    )
    db.add(u)
    db.commit()
    db.refresh(u)

    return {"id": str(u.id), "email": u.email, "tier": u.tier}


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
