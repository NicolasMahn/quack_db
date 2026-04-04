from app_config import COLLECTIONS, DEFAULT_COLLECTION


def load_config() -> dict:
    """Return application config sourced from app_config module."""
    return {
        "collections": list(COLLECTIONS),
        "default_collection": DEFAULT_COLLECTION,
    }
