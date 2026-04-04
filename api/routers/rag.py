"""RAG query + optional SQL session/message persistence."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as SaSession

from api.deps import get_db_session, require_user
from quack_db.authz import matrix
from quack_db.config import get_settings
from quack_db.db.models import Message, User
from quack_db.db.models import Session as ChatSession
from quack_db.services import rag as rag_svc

router = APIRouter(tags=["rag"])


class RagBody(BaseModel):
    query_text: str
    collections: list[str] | None = None
    collection: str | None = None
    n_results: int = Field(default=3, ge=1, le=50)
    model: str = "default"
    debug: bool = False
    session_id: uuid.UUID | None = None
    call_id: str | None = None


@router.post("/rag/query")
def rag_query(
    db: Annotated[SaSession, Depends(get_db_session)],
    user: Annotated[User, Depends(require_user)],
    body: RagBody,
):
    settings = get_settings()
    cap = settings.rag_n_results_cap
    n = min(body.n_results, cap)

    if body.collections:
        names = body.collections
    elif body.collection:
        names = [body.collection]
    else:
        names = rag_svc.default_collections_for_user(user)

    for n_ in names:
        repo = matrix.resolve_repo(n_, user.id)
        if repo is None:
            raise HTTPException(status_code=404, detail=f"Unknown collection: {n_}")
        p = matrix.rwmd_for_repo(user, repo)
        if not p.read:
            raise HTTPException(status_code=403, detail=f"No read access to {n_}")

    call_id = body.call_id or str(uuid.uuid4())

    response_text, context_text, metas = rag_svc.query_rag(
        body.query_text,
        names,
        debug=body.debug,
        n_results=n,
        model=body.model,
    )

    sid = body.session_id
    if sid is None:
        chat = ChatSession(user_id=user.id, title=body.query_text[:120])
        db.add(chat)
        db.flush()
        sid = chat.id
    else:
        chat = db.get(ChatSession, sid)
        if chat is None or chat.user_id != user.id:
            raise HTTPException(status_code=404, detail="Session not found")

    db.add(
        Message(
            session_id=sid,
            call_id=call_id + ":user",
            role="user",
            content=body.query_text,
            extra_metadata={"collections": names},
        )
    )
    db.add(
        Message(
            session_id=sid,
            call_id=call_id + ":assistant",
            role="assistant",
            content=response_text,
            extra_metadata={"context_preview": context_text[:2000], "sources": len(metas)},
        )
    )
    db.commit()

    out: dict[str, Any] = {
        "answer": response_text,
        "call_id": call_id,
        "session_id": str(sid),
        "collections": names,
    }
    if body.debug:
        out["context"] = context_text
        out["metadata"] = metas
    return out
