# Quack API (FastAPI)

**Cloud-first:** validate against the deployed HTTPS URL. Chroma stays **internal**; only this API speaks to Chroma and Postgres (do not point browsers or tools at Chroma with user identity).

## Run (local process)

```bash
cd ..   # repo root
pip install -e .
export DATABASE_URL=sqlite:///./quack.db
# Or Postgres: pip install -e ".[postgres]" then postgresql+psycopg://...
export ADMIN_BOOTSTRAP_KEY=change-me-bootstrap
export CHROMADB_HOST=... CHROMADB_PORT=8000 CHROMADB_AUTH_TOKEN=...
export ENTRA_JWKS_URL=https://login.microsoftonline.com/<tenant>/discovery/v2.0/keys
export ENTRA_AUDIENCE=api://<api-app-client-id>
export ENTRA_ISSUER=https://login.microsoftonline.com/<tenant>/v2.0
export AZURE_OPENAI_API_KEY=...  # plus embedding/nano vars as needed
# Optional local escape hatch (never in prod):
# export AUTH_DISABLED=true
# export DEV_IMPERSONATE_USER_EMAIL=you@example.com

uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Alembic upgrades run **on startup** unless `RUN_MIGRATIONS_ON_STARTUP=false`. Manual migrations from repo root:

```bash
alembic -c src/alembic.ini upgrade head
```

## Auth: Microsoft Entra only

Every protected route expects:

`Authorization: Bearer <access_token>`  

where the token is issued **for this API** (correct `aud` / scope), not only for Microsoft Graph.

1. **Bootstrap (empty `users` table):** `POST /admin/users` with `X-Admin-Bootstrap: <ADMIN_BOOTSTRAP_KEY>` and body  
   `{ "email": "you@example.com", "tier": "board" }`  
   Email must match what Entra will put in the token (`email` or `preferred_username`).

2. **After that:** admins call `/admin/users` with their own Bearer token (board / dev_admin tier in Postgres).

3. **Optional:** set `ENTRA_AUTO_PROVISION_TIER=everyone` (or another tier) so the first Entra login auto-creates users; otherwise users must be pre-created by email.

4. **Check:** `POST /auth/validate` with the same Bearer token returns `user_id`, `entra_oid`, `tier`, etc.

## CLI ingest

Use **`QUACK_BEARER_TOKEN`** (or `quack-ingest --bearer`) with an Entra access token for this API, e.g. from `az account get-access-token` scoped to the API app.

## Docker

```bash
docker build -f api/Dockerfile -t quack-api:latest ..
```

[`chromadb/AZURE.md`](../chromadb/AZURE.md) describes ACA wiring. [`.github/README.md`](../.github/README.md) describes CI/CD variables.

## Layout

- `main.py` — app factory, migrations on lifespan
- `routers/` — `/health`, `/auth/validate`, `/collections/*`, `/admin/*`, `/rag/query`
- `deps.py` — DB session + Entra JWT → `User`
- `chroma_access.py` — RBAC helpers, `where` merge

Business logic lives under **`src/quack_db/`** (services, authz matrix, DB models).
