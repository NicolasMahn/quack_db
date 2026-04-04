from fastapi import APIRouter

from quack_db.chroma.client import get_chroma_client

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    chroma_ok = True
    try:
        get_chroma_client().list_collections()
    except Exception:
        chroma_ok = False
    return {"status": "ok", "chroma": chroma_ok}
