"""Validate Microsoft Entra access tokens (JWKS / RS256)."""

from __future__ import annotations

import jwt
from jwt import PyJWKClient

from quack_db.config import Settings, get_settings


def _issuer_value_for_pyjwt(issuer: str) -> str | tuple[str, ...] | None:
    """Single issuer or tuple for PyJWT when ENTRA_ISSUER is comma-separated."""
    issuer = (issuer or "").strip()
    if not issuer:
        return None
    parts = tuple(
        p.strip().rstrip("/") for p in issuer.split(",") if p.strip()
    )
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return parts


def verify_entra_jwt(token: str, settings: Settings | None = None) -> dict:
    """Decode and validate token; return claims."""
    s = settings or get_settings()
    if not s.entra_jwks_url:
        raise ValueError("ENTRA_JWKS_URL is not set")
    client = PyJWKClient(s.entra_jwks_url)
    signing_key = client.get_signing_key_from_jwt(token).key
    iss = _issuer_value_for_pyjwt(s.entra_issuer)
    return jwt.decode(
        token,
        key=signing_key,
        algorithms=["RS256"],
        audience=s.entra_audience or None,
        issuer=iss,
        options={
            "verify_aud": bool(s.entra_audience),
            "verify_iss": bool(iss),
        },
    )
