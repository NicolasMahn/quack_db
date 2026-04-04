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
  - (`DATABASE_URL`, `ADMIN_BOOTSTRAP_KEY`, `CHROMADB_*` as env / secrets on the app, not necessarily in GitHub)
- `ui-prod`:
  - No shared API key: UI acquires tokens via **MSAL** (or similar) and sends `Authorization: Bearer` to the API.

## 4) Access Model

- **All clients** (UI, CLI, other services) call the **API** with `Authorization: Bearer <Entra access token for the Quack API app>`.
- Postgres `users` rows (tier, flags) drive authorization (`authz` matrix); Chroma remains private behind the API.

UI / ingest toggles:
- `ENABLE_UI_INGEST=true|false`

Recommended prod defaults:
- `ENABLE_UI_INGEST=false` (enable only for trusted admin UI)

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
- Query volume anomalies and model token-cost jumps
- Ingestion job failures
- Chroma reachability from API only

## 7) Cutover Checklist

1. Deploy API and UI in `dev` and validate `/health` + `/query`.
2. Switch UI to API-backed flow (no direct Chroma access).
3. Validate ingestion through `/admin/ingest`.
4. In `prod`, set Chroma ingress to internal and verify no public access.
5. Confirm JWT audience/issuer checks (`/health` reports `entra_configured`).

