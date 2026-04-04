# Azure bring-up (cloud-first)

This file lists **names and wiring only**—no secrets in git. The authoritative runtime is **Azure Container Apps (ACA)** + **PostgreSQL Flexible Server** + **Azure Files** for Chroma + **ACR** for images.

## Components

| Piece | Role |
| ----- | ---- |
| **Resource group** | Holds all resources |
| **ACR** | Stores `quack-api` image (CI pushes from `main`) |
| **PostgreSQL Flexible** | App DB: `users`, `api_keys`, `sessions`, `messages` |
| **Storage account + File share** | Chroma persistence (mount in Chroma Container App) |
| **ACA environment** | Shared internal DNS for `api` ↔ `chroma` |
| **Container App `chroma`** | `chromadb/chroma` image, **internal ingress**, volume mount |
| **Container App `api`** | This repo’s FastAPI image, **external** HTTPS ingress |
| **Azure OpenAI** | Embeddings + chat (endpoints/keys as ACA secrets) |
| **SMTP or transactional provider** | Sends API keys to users when SMTP env is set |

## Secrets → ACA environment variables (API app)

Set as Container App **secrets** / env (names are illustrative—keep consistent with [`api/README.md`](../api/README.md)):

| Name | Purpose |
| ---- | ------- |
| `DATABASE_URL` | `postgresql+psycopg://...` |
| `ADMIN_BOOTSTRAP_KEY` | One-time bootstrap for `POST /admin/users` when `users` is empty |
| `CHROMADB_HOST` | Internal hostname of Chroma app |
| `CHROMADB_PORT` | Usually `8000` |
| `CHROMADB_AUTH_TOKEN` | Shared token with Chroma server auth |
| `AZURE_OPENAI_*` / `GOOGLE_API_KEY` | As in `.env.example` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Optional email delivery |

## Bring-up order

1. Resource group + region.
2. **PostgreSQL** — create DB/user; allow ACA egress (firewall rules / VNet per your choice).
3. **Storage + file share** for Chroma.
4. **Deploy Chroma** ACA: mount share, set Chroma token env vars, **internal** only.
5. **ACR** + push images (see [`.github/README.md`](../.github/README.md)).
6. **Deploy API** ACA: paste `DATABASE_URL` and other secrets; set `PYTHONPATH=/app` inside image **already** in Dockerfile.
7. Open public URL → `GET /health` → `POST /admin/users` with `X-Admin-Bootstrap` (empty DB) → capture one-time `api_key` → `POST /auth/validate` → ingest / `POST /rag/query`.

## CI/CD

GitHub Actions **OIDC** to Azure: see [`.github/README.md`](../.github/README.md). Repository secrets: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `ACR_NAME`, `ACA_RESOURCE_GROUP`, `ACA_API_APP_NAME`.

## Links

- [Azure Container Apps](https://learn.microsoft.com/azure/container-apps/)
- [PostgreSQL Flexible Server](https://learn.microsoft.com/azure/postgresql/flexible-server/)
- [Azure Files + ACA volumes](https://learn.microsoft.com/azure/container-apps/storage-mounts)
