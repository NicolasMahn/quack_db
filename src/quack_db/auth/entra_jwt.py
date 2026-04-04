"""Validate Microsoft Entra access tokens (JWKS / RS256)."""

from __future__ import annotations

import jwt
from jwt import PyJWKClient

from quack_db.config import Settings, get_settings


def verify_entra_jwt(token: str, settings: Settings | None = None) -> dict:
    """Decode and validate token; return claims."""
    s = settings or get_settings()
    if not s.entra_jwks_url:
        raise ValueError("ENTRA_JWKS_URL is not set")
    client = PyJWKClient(s.entra_jwks_url)
    signing_key = client.get_signing_key_from_jwt(token).key
    return jwt.decode(
        token,
        key=signing_key,
        algorithms=["RS256"],
        audience=s.entra_audience or None,
        issuer=s.entra_issuer or None,
        options={
            "verify_aud": bool(s.entra_audience),
            "verify_iss": bool(s.entra_issuer),
        },
    )
