# CI/CD

## `ci.yml`

Runs on every **push** to `main` and on **pull requests**:

- `ruff check` on `src`, `api`, `tests`
- `pytest`
- `docker build -f api/Dockerfile` (smoke)

## `deploy.yml`

Runs on **push** to `main` after merge.

Uses **OpenID Connect** to Azure (`azure/login@v2`)—no long-lived service principal secret in GitHub if you use a **federated credential** on an app registration.

### GitHub repository secrets

| Secret | Purpose |
| ------ | ------- |
| `AZURE_CLIENT_ID` | App registration **application (client) ID** used by the workflow |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Subscription containing ACR and Container Apps |
| `ACR_NAME` | Azure Container Registry name (no `.azurecr.io`) |
| `ACA_RESOURCE_GROUP` | Resource group that contains the **API** Container App |
| `ACA_API_APP_NAME` | Name of the **API** Container App resource |

### Azure setup (outline)

1. Create an app registration; add federated credential for `repo:YOUR_ORG/YOUR_REPO:ref:refs/heads/main`.
2. Grant that identity **AcrPush** on your registry and permission to update the Container App (e.g. **Contributor** on the app or a custom role).
3. Fill the secrets above in **GitHub → Settings → Secrets and variables → Actions**.

See [chromadb/AZURE.md](../chromadb/AZURE.md) for full stack bring-up (Postgres, Chroma, API, env vars).
