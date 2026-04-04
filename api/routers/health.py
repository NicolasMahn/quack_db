from fastapi import APIRouter

from quack_db.chroma.client import get_chroma_client
from quack_db.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    s = get_settings()
    chroma_ok = True
    try:
        get_chroma_client().list_collections()
    except Exception:
        chroma_ok = False
    entra_ready = bool(s.entra_jwks_url and s.entra_audience and s.entra_issuer) or s.auth_disabled
    return {
        "status": "ok",
        "chroma": chroma_ok,
        "auth_disabled": s.auth_disabled,
        "entra_configured": entra_ready,
    }
