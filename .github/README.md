# CI/CD

## `ci.yml`

Runs on every **push** to `main` and on **pull requests**:

- `ruff check` on `src`, `api`, `tests`
- `pytest`
- `docker build -f api/Dockerfile` (smoke)

## `deploy.yml` (Deploy API)

**Manual only** (`workflow_dispatch`). Builds `api/Dockerfile`, pushes `quack-api` to ACR, updates one API Container App.

Uses **OpenID Connect** to Azure (`azure/login@v2`)—no long-lived service principal secret in GitHub if you use **federated credentials** on the app registration (see below).

### GitHub repository secrets (`deploy.yml`)

| Secret | Purpose |
| ------ | ------- |
| `AZURE_CLIENT_ID` | App registration **application (client) ID** used by the workflow |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Subscription containing ACR and Container Apps |
| `ACR_NAME` | Azure Container Registry name (no `.azurecr.io`) |
| `ACA_RESOURCE_GROUP` | Resource group that contains the **API** Container App |
| `ACA_API_APP_NAME` | Name of the **API** Container App resource |

## `azure-deploy.yml` (Azure Deploy)

**Manual only** (`workflow_dispatch`): choose `dev` / `prod` and toggles **Deploy Chroma / API / UI**. Builds and pushes only what you enable (API uses `api/Dockerfile`; UI uses `Dockerfile.ui` and requires a `./ui` directory). Can create RG and Container Apps environment, then deploys selected apps with env vars and secrets.

- **Secrets:** Same repository secrets as `deploy.yml` for Azure auth and ACR: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, **`ACR_NAME`** (registry resource name only—5–50 alphanumeric chars; optional `.azurecr.io` suffix is stripped). Plus `API_KEYS`, `API_INGEST_KEYS`, `AZURE_OPENAI_API_KEY`, `UI_API_CLIENT_KEY`, and any others referenced in the workflow.
- **Variables:** `AZURE_RESOURCE_GROUP`, `AZURE_LOCATION`, `AZURE_CONTAINERAPPS_ENV`, `APP_NAME_CHROMA`, `APP_NAME_API`, `APP_NAME_UI`, plus the `vars.*` used in API/UI env blocks (OpenAI, Chroma host, Entra, etc.).
- **Dev vs prod** is chosen in the workflow inputs (`environment`) and passed to Azure as `APP_ENV` / image tags only. The **`deploy` job does not use a GitHub Environment** on purpose, so OIDC matches the same federated credential as `build-and-push` (branch subject, e.g. `repo:OWNER/REPO:ref:refs/heads/main`). If you add `environment: prod` to `deploy` later (for approvals / env-scoped secrets), you must add Entra federated credentials for `repo:OWNER/REPO:environment:prod` (and `environment:dev`) or login will fail with **AADSTS700213**.

### Federated credentials (OIDC) — required for both workflows

If `azure/login` fails with **AADSTS70025** (“client has no configured federated identity credentials”), the Entra **app registration** tied to `AZURE_CLIENT_ID` has no (matching) federated credential.

1. **Entra ID → App registrations →** your app → **Certificates & secrets → Federated credentials → Add credential.**
2. **Federated credential scenario:** GitHub Actions deploying Azure resources.
3. **Organization / repository:** your GitHub org or user and repo name (must match where the workflow runs).
4. **Entity type:** Branch, tag, or pull request — for runs triggered from `main`, use branch `main`. If you start the workflow from another branch, add a matching federated credential for that ref.

**Subject identifiers** GitHub sends (add one federated credential per subject you need):

| When | Example subject identifier |
| ---- | ------------------------- |
| Jobs **without** a GitHub `environment:` key (current `azure-deploy.yml` for both jobs) | `repo:OWNER/REPO:ref:refs/heads/main` |
| A job **with** `environment: prod` in the workflow | `repo:OWNER/REPO:environment:prod` |
| Same for `environment: dev` | `repo:OWNER/REPO:environment:dev` |

Replace `OWNER/REPO` with your real path (case-sensitive).

**AADSTS700213** (“No matching federated identity record… **environment:prod**”): the failing job used a GitHub **Environment**, so the token subject is `repo:…:environment:…`. Either add that exact subject in Entra **or** remove `environment:` from the job (as in the current workflow) so only the **branch** credential is required.

Then grant that app's **enterprise application** (service principal) **AcrPush** on the registry and rights to create/update Container Apps and resource groups as needed (`azure-deploy.yml` creates the RG and Container Apps environment if missing).

### “No subscriptions found” after login

If OIDC succeeds but the log shows **No subscriptions found** (or `az account list` would be empty), the identity is signed in but **has no access** to the subscription you passed as `AZURE_SUBSCRIPTION_ID`, or the **subscription ID in GitHub is wrong**.

1. In **Azure Portal → Subscriptions**, open the subscription that holds ACR and Container Apps and copy its **Subscription ID**. It must match **`AZURE_SUBSCRIPTION_ID`** in GitHub secrets exactly (no quotes or spaces).
2. On that same subscription → **Access control (IAM)** → **Add role assignment** → assign at least **Reader** to verify access; for `azure-deploy.yml` you typically need **Contributor** on the subscription (or a narrower custom role on the RG + ACR + Container Apps).
3. Assign the role to **User, group, or service principal** → search for the **display name** of your app registration (e.g. “QuackDB”), not the client ID string.

**Cloud Shell / local CLI:** `az account show --query id -o tsv` proves *your user* can see the subscription. Actions uses **only** the app registration behind `AZURE_CLIENT_ID`. Confirm that principal has roles on that subscription (replace IDs):

```bash
SUBSCRIPTION_ID="<same value as AZURE_SUBSCRIPTION_ID / az account show --query id -o tsv>"
APP_CLIENT_ID="<Application (client) ID from Entra — same as AZURE_CLIENT_ID>"
az role assignment list --assignee "$APP_CLIENT_ID" --scope "/subscriptions/$SUBSCRIPTION_ID" -o table
```

If the table is empty, add **Contributor** (or Reader + scoped roles) on that subscription for the app, then re-run the workflow. OIDC setup steps are in the [Azure/login README — Login with OpenID Connect](https://github.com/Azure/login#login-with-openid-connect-oidc-recommended).

Wait a few minutes after IAM changes, then re-run the workflow.

### Quick outline (`deploy.yml` only)

1. Create an app registration; add federated credential(s) as above (e.g. `repo:OWNER/REPO:ref:refs/heads/main` when you run the workflow from `main`; add other branches if you dispatch from them).
2. Grant roles on the subscription or resources (ACR push, Container App update).
3. Fill the secrets in **GitHub → Settings → Secrets and variables → Actions**.

See [chromadb/AZURE.md](../chromadb/AZURE.md) for full stack bring-up (Postgres, Chroma, API, env vars).
