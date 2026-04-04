# GitHub Actions Deployment to Azure

This repository includes `.github/workflows/azure-deploy.yml` to deploy all three services:
- `chroma` (internal ingress)
- `api` (external ingress)
- `ui` (external ingress)

## 1) One-time Azure and GitHub setup

1. Create an Azure AD app/service principal for GitHub OIDC.
2. Add a federated credential for your GitHub repo/environment.
3. Grant the principal rights on your resource group:
   - `Contributor` on the resource group
   - `AcrPush` on your ACR (or Contributor on RG containing ACR)

## 2) Required GitHub Secrets

Add these repository secrets:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `ACR_NAME` (Container Registry resource name, no `.azurecr.io`; same as `deploy.yml`)
- `AZURE_OPENAI_API_KEY`
- `API_KEYS`
- `API_INGEST_KEYS`
- `UI_API_CLIENT_KEY`

## 3) Required GitHub Variables

Add these as **repository** variables (**Settings → Secrets and variables → Actions → Variables**). Values stored only under GitHub **Environments** are **not** visible to this workflow (jobs do not use `environment:` so OIDC stays branch-based).

- `AZURE_RESOURCE_GROUP`
- `AZURE_LOCATION`
- `AZURE_CONTAINERAPPS_ENV`
- `APP_NAME_CHROMA`
- `APP_NAME_API`
- `APP_NAME_UI`

Optional: if **dev** vs **prod** targets different RGs or app names, add repository variables `*_DEV` and `*_PROD` for any of the above (see `.github/README.md`).

API runtime vars:
- `AZURE_OPENAI_ENDPOINT`
- `CHROMADB_HOST` (internal hostname of Chroma in Container Apps)
- `CHROMADB_PORT` (usually `8000`)
- `CHROMADB_SSL` (`true`/`false`)
- `API_AUTH_REQUIRED` (`true`/`false`)
- `API_RATE_LIMIT_PER_MINUTE` (e.g. `120`)
- `ENTRA_AUTH_ENABLED` (`true`/`false`)
- `ENTRA_TENANT_ID`
- `ENTRA_AUDIENCE`
- `ENTRA_ISSUER`
- `ENTRA_JWKS_URL`
- `RESTRICTED_ROLES` (comma-separated)
- `INGEST_ROLES` (comma-separated)
- `RAG_EXECUTION_MODE` (`api` recommended in prod)
- `INGEST_EXECUTION_MODE` (`api` recommended in prod)
- `ALLOW_PROD_INGEST` (`false` unless intentional ingest window)

UI runtime vars:
- `UI_API_BASE_URL` (public URL of API)
- `COLLECTIONS` (comma-separated)
- `DEFAULT_COLLECTION`
- `ENABLE_UI_INGEST` (`true` only for trusted/admin-facing UI)

## 4) Running deployment

Deploys are **manual** only (`workflow_dispatch`).

- In GitHub Actions, run **Azure Deploy** (stack) or **Deploy API** (API-only).
- For **Azure Deploy**, choose:
  - environment: `dev` or `prod`
  - whether to build/deploy each component (`chroma`, `api`, `ui`). Disable **API** or **UI** if you did not change that part; **UI** requires a `./ui` directory in the repo.

## 5) Suggested protection

- Restrict who can run **Actions** or approve deployments (branch protection, environment approvals only apply if you add `environment:` to jobs and matching Entra federated credentials).
- Use different Azure resource names per tier via optional `*_DEV` / `*_PROD` repository variables.

## 6) Post-deploy checks

- API health: `GET /health`
- Query endpoint rejects missing auth
- Chroma is not reachable publicly in `prod`
- UI can query API successfully

