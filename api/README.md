# Quack API (FastAPI)

**Cloud-first:** validate against the **deployed** HTTPS URL. Optional local Chroma is described in [`chromadb/README.md`](../chromadb/README.md).

## Run (local process)

```bash
cd ..   # repo root
pip install -e .
export DATABASE_URL=postgresql+psycopg://USER:PASS@HOST:5432/DBNAME
export ADMIN_BOOTSTRAP_KEY=change-me-bootstrap
export CHROMADB_HOST=... CHROMADB_PORT=8000 CHROMADB_AUTH_TOKEN=...
export AZURE_OPENAI_API_KEY=...  # plus embedding/nano vars as needed
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Alembic upgrades run **on startup** unless `RUN_MIGRATIONS_ON_STARTUP=false`. To run migrations manually from the repo root:

```bash
alembic -c src/alembic.ini upgrade head
```

## First user (empty database)

1. `POST /admin/users` with header `X-Admin-Bootstrap: <ADMIN_BOOTSTRAP_KEY>` and JSON body, e.g.  
   `{ "email": "you@example.com", "tier": "board", "issue_key": true }`
2. Response includes **`api_key` once** (plaintext) when the DB had zero users. After that, keys are emailed when SMTP is configured (no plaintext in JSON).

## Discover `user_id` for `user_ctx_{uuid}` collections

`POST /auth/validate` with `X-API-Key` returns `user_id`. Personal Chroma corpus: collection name `user_ctx_<user_id>` (see `quack_db.authz.matrix`).

## Docker

```bash
docker build -f api/Dockerfile -t quack-api:latest ..
```

[`chromadb/AZURE.md`](../chromadb/AZURE.md) describes ACA wiring. [`.github/README.md`](../.github/README.md) describes CI/CD secrets.

## Layout

- `main.py` — app factory, migrations on lifespan
- `routers/` — `/health`, `/auth/validate`, `/collections/*`, `/admin/*`, `/rag/query`
- `deps.py` — DB session + API key auth
- `chroma_access.py` — RBAC helpers, `where` merge

Business logic lives under **`src/quack_db/`** (services, authz matrix, DB models).
