"""Authentication and authorization helpers for API endpoints."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from jwt import PyJWKClient

from app_config import (
    API_AUTH_REQUIRED,
    API_INGEST_KEYS,
    API_KEYS,
    ENTRA_AUDIENCE,
    ENTRA_AUTH_ENABLED,
    ENTRA_ISSUER,
    ENTRA_JWKS_URL,
    INGEST_ROLES,
    RESTRICTED_ROLES,
)


@dataclass
class AuthContext:
    subject: str
    method: str
    roles: list[str]


_jwks_client = PyJWKClient(ENTRA_JWKS_URL) if ENTRA_JWKS_URL else None


def _roles_from_claims(claims: dict) -> list[str]:
    roles: list[str] = []
    raw_roles = claims.get("roles", [])
    if isinstance(raw_roles, list):
        roles.extend(str(item) for item in raw_roles)
    scope_claim = claims.get("scp", "")
    if isinstance(scope_claim, str):
        roles.extend(scope_claim.split())
    return sorted(set(role for role in roles if role))


def _verify_jwt(token: str) -> AuthContext:
    if not ENTRA_AUTH_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token auth is disabled.",
        )
    if not _jwks_client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT validation is misconfigured.",
        )

    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key=signing_key,
            algorithms=["RS256"],
            audience=ENTRA_AUDIENCE or None,
            issuer=ENTRA_ISSUER or None,
            options={
                "verify_aud": bool(ENTRA_AUDIENCE),
                "verify_iss": bool(ENTRA_ISSUER),
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid bearer token: {exc}",
        ) from exc

    subject = str(claims.get("sub") or claims.get("oid") or "unknown")
    return AuthContext(subject=subject, method="jwt", roles=_roles_from_claims(claims))


def _verify_api_key(api_key: str, ingest_only: bool = False) -> AuthContext:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key.",
        )

    allowed_keys = set(API_INGEST_KEYS) if ingest_only and API_INGEST_KEYS else set(API_KEYS)
    if api_key not in allowed_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )
    return AuthContext(subject="service-client", method="api_key", roles=["service"])


def _require_role(context: AuthContext, allowed_roles: list[str], detail: str) -> AuthContext:
    if context.method == "api_key":
        return context
    if any(role in context.roles for role in allowed_roles):
        return context
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _extract_bearer(authorization: str | None) -> str:
    if not authorization:
        return ""
    prefix = "bearer "
    value = authorization.strip()
    if value.lower().startswith(prefix):
        return value[len(prefix) :].strip()
    return ""


def _build_dependency(
    *,
    restricted_roles: list[str] | None = None,
    ingest_only_key: bool = False,
) -> Callable:
    async def _dependency(
        request: Request,
        authorization: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ) -> AuthContext:
        if not API_AUTH_REQUIRED:
            return AuthContext(subject="anonymous", method="none", roles=[])

        context: AuthContext | None = None
        if x_api_key:
            context = _verify_api_key(x_api_key, ingest_only=ingest_only_key)
        else:
            bearer = _extract_bearer(authorization)
            if bearer:
                context = _verify_jwt(bearer)

        if context is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Provide either a bearer token or X-API-Key.",
            )

        if restricted_roles:
            context = _require_role(
                context,
                restricted_roles,
                detail="Your role does not permit this endpoint.",
            )

        request.state.auth_subject = context.subject
        request.state.auth_method = context.method
        return context

    return _dependency


RequireAccess = Depends(_build_dependency())
RequireRestrictedAccess = Depends(_build_dependency(restricted_roles=RESTRICTED_ROLES))
RequireIngestAccess = Depends(
    _build_dependency(restricted_roles=INGEST_ROLES, ingest_only_key=True)
)

