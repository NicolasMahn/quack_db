# Azure bring-up (cloud-first)

This file lists **names and wiring only**—no secrets in git. The authoritative runtime is **Azure Container Apps (ACA)** + **PostgreSQL Flexible Server** + **Azure Files** for Chroma + **ACR** for images.

## Components

| Piece | Role |
| ----- | ---- |
| **Resource group** | Holds all resources |
| **ACR** | Stores `quack-api` / `quack-ui` images (CI pushes when you run deploy workflows) |
| **App DB** | Default **SQLite** file on a mounted share (`quack.db`); optional Postgres later |
| **Storage account + File share** | Chroma persistence (mount in Chroma Container App) |
| **ACA environment** | Shared internal DNS for `api` ↔ `chroma` |
| **Container App `chroma`** | `chromadb/chroma` image, **internal ingress**, volume mount |
| **Container App `api`** | This repo’s FastAPI image, **external** HTTPS ingress |
| **Azure OpenAI** | Embeddings + chat (endpoints/keys as ACA secrets) |
| **Microsoft Entra ID** | Users sign in; API validates JWT (`ENTRA_*` env vars) |

## Secrets → ACA environment variables (API app)

Set as Container App **secrets** / env (names are illustrative—keep consistent with [`api/README.md`](../api/README.md)):

| Name | Purpose |
| ---- | ------- |
| `DATABASE_URL` | Default in image: `sqlite:////app/data/quack.db` — mount **Azure Files** (or emptyDir + backup) on `/app/data`. For Postgres: `postgresql+psycopg://...` + `[postgres]` extra in image |
| `ADMIN_BOOTSTRAP_KEY` | One-time bootstrap for `POST /admin/users` when `users` is empty |
| `CHROMADB_HOST` | Internal hostname of Chroma app |
| `CHROMADB_PORT` | Usually `8000` |
| `CHROMADB_AUTH_TOKEN` | Shared token with Chroma server auth |
| `AZURE_OPENAI_*` / `GOOGLE_API_KEY` | As in `.env.example` |
| `ENTRA_JWKS_URL`, `ENTRA_AUDIENCE`, `ENTRA_ISSUER` | Required unless `AUTH_DISABLED=true` (dev only) |
| `ENTRA_AUTO_PROVISION_TIER` | Optional: auto-create users on first login |
| `SMTP_*` | Reserved / optional |

## Bring-up order

1. Resource group + region.
2. **PostgreSQL** — create DB/user; allow ACA egress (firewall rules / VNet per your choice).
3. **Storage + file share** for Chroma.
4. **Deploy Chroma** ACA: mount share, set Chroma token env vars, **internal** only.
5. **ACR** + push images (see [`.github/README.md`](../.github/README.md)).
6. **Deploy API** ACA: paste `DATABASE_URL` and other secrets; set `PYTHONPATH=/app` inside image **already** in Dockerfile.
7. Open public URL → `GET /health` → `POST /admin/users` with `X-Admin-Bootstrap` (empty DB) to seed the first board user (email must match Entra) → sign in and obtain an access token for the API app → `POST /auth/validate` with `Authorization: Bearer` → `/rag/query` and `/collections/...` as usual.

## CI/CD

GitHub Actions **OIDC** to Azure: see [`.github/README.md`](../.github/README.md) for secrets, variables, and **Azure Deploy** (`azure-deploy.yml`).

## Links

- [Azure Container Apps](https://learn.microsoft.com/azure/container-apps/)
- [PostgreSQL Flexible Server](https://learn.microsoft.com/azure/postgresql/flexible-server/)
- [Azure Files + ACA volumes](https://learn.microsoft.com/azure/container-apps/storage-mounts)
