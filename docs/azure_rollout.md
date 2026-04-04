# Quack DB Azure Rollout Guide

This guide implements the `dev` + single-`prod` topology with three deployments:
- Chroma DB container app
- Quack API container app
- Quack UI container app

## 1) Environment Topology

- `dev`:
  - Public test environment for students
  - Synthetic/non-sensitive datasets only
- `prod`:
  - API and UI can be public
  - Chroma ingress must be internal/private

## 2) Network and Ingress Rules

For `prod`, apply:
- `chroma-prod`: ingress `internal`
- `api-prod`: ingress `external`
- `ui-prod`: ingress `external`

The API uses private networking to reach Chroma. UI only talks to API.

## 3) Runtime Secrets

Never bake secrets into image build args. Inject at runtime using Container Apps secrets / Key Vault references.

Minimum secrets by app:
- `api-prod`:
  - `AZURE_OPENAI_API_KEY`
  - `API_KEYS`
  - `API_INGEST_KEYS`
  - `ENTRA_*` JWT validation values
- `ui-prod`:
  - `API_CLIENT_KEY` (if UI uses key mode)
  - or `API_BEARER_TOKEN` for service scenarios

## 4) Access Model

- Query endpoint (`POST /query`):
  - Requires API key or Entra bearer token
- Restricted query endpoint (`POST /query/restricted`):
  - Requires role claim from `RESTRICTED_ROLES` (JWT) or trusted key
- Ingestion endpoint (`POST /admin/ingest`):
  - Requires key from `API_INGEST_KEYS` or ingest role claim from `INGEST_ROLES`
  - Can be globally toggled in prod using `ALLOW_PROD_INGEST`

Execution mode toggles:
- `RAG_EXECUTION_MODE=api|direct`
- `INGEST_EXECUTION_MODE=api|direct`
- `ENABLE_UI_INGEST=true|false`

Recommended prod defaults:
- `RAG_EXECUTION_MODE=api`
- `INGEST_EXECUTION_MODE=api`
- `ENABLE_UI_INGEST=false` (enable only for trusted admin UI)
- `ALLOW_PROD_INGEST=false` except controlled ingest windows

## 5) Deployment Guardrails

- Students:
  - Can deploy `dev`
  - Cannot deploy `prod`
  - Cannot read `prod` secrets
- Maintainers:
  - Own `prod` deployment approvals
  - Rotate secrets and review audit logs

## 6) Monitoring Checklist

- HTTP 401/403 spikes on API endpoints
- HTTP 429 spikes (rate limit)
- Query volume anomalies and model token-cost jumps
- Ingestion job failures
- Chroma reachability from API only

## 7) Cutover Checklist

1. Deploy API and UI in `dev` and validate `/health` + `/query`.
2. Switch UI to API-backed flow (no direct Chroma access).
3. Validate ingestion through `/admin/ingest`.
4. In `prod`, set Chroma ingress to internal and verify no public access.
5. Enable Entra validation and confirm JWT audience/issuer checks.
6. Validate rate limiting and request correlation (`X-Request-ID`).

