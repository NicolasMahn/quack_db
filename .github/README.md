# CI/CD

Use **GitHub → Settings → Secrets and variables → Actions**. **Secrets** = sensitive; **Variables** = non-sensitive. Define **Variables** at **repository** scope (not only GitHub *Environments*) so OIDC can stay branch-based—see [OIDC](#federated-credentials-oidc).

---

## `ci.yml`

Runs on every **push** to `main` and on **pull requests**:

- `python -m ruff check` on `src`, `api`, `src/tests`
- `python -m pytest`
- `docker build -f api/Dockerfile` (smoke)

**No GitHub secrets or variables required.**

---

## GitHub **Secrets** checklist (`azure-deploy.yml`)

| Secret | Purpose |
| ------ | ------- |
| `AZURE_CLIENT_ID` | Entra app registration **Application (client) ID** (OIDC) |
| `AZURE_TENANT_ID` | Entra **Directory (tenant) ID** |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription GUID |
| `ACR_NAME` | Container Registry **name** only (alphanumeric, 5–50 chars; no `.azurecr.io`) |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI (`azure-openai-api-key`) |

**Not applied by these workflows** (set on the Container App or elsewhere): e.g. **`DATABASE_URL`** only if you override the image default (SQLite under `/app/data`), **`CHROMADB_AUTH_TOKEN`**, **`ADMIN_BOOTSTRAP_KEY`**—see [chromadb/AZURE.md](../chromadb/AZURE.md) and [api/README.md](../api/README.md).

Auth is **Microsoft Entra JWT** only (`Authorization: Bearer`). Register an **API** app + SPA/native clients; set **Variables** below (`ENTRA_*`). Do **not** expose Chroma publicly—the API remains the only gateway to Chroma and to Postgres-backed users/authz.

---

## GitHub **Variables** checklist

**Repository** variables. Optional **`_DEV` / `_PROD`** overrides apply when the workflow **Target environment** is `dev` or `prod`; if an override is empty, the unsuffixed name is used.

### Azure layout (required)

| Variable | Purpose |
| -------- | ------- |
| `AZURE_RESOURCE_GROUP` | Resource group for Container Apps |
| `AZURE_LOCATION` | Azure region (e.g. `westeurope`) |
| `AZURE_CONTAINERAPPS_ENV` | Container Apps **environment** resource name |
| `APP_NAME_CHROMA` | Container App name for Chroma |
| `APP_NAME_API` | Container App name for API |
| `APP_NAME_UI` | Container App name for UI |

If you still have old secrets **`ACA_RESOURCE_GROUP`** / **`ACA_API_APP_NAME`**, copy their values into **`AZURE_RESOURCE_GROUP`** / **`APP_NAME_API`** variables, then delete those secrets—they are not read by the workflow.

**Optional:** `AZURE_RESOURCE_GROUP_DEV`, `AZURE_RESOURCE_GROUP_PROD`, `AZURE_LOCATION_DEV`, `AZURE_LOCATION_PROD`, `AZURE_CONTAINERAPPS_ENV_DEV`, `AZURE_CONTAINERAPPS_ENV_PROD`, `APP_NAME_CHROMA_DEV` / `_PROD`, `APP_NAME_API_DEV` / `_PROD`, `APP_NAME_UI_DEV` / `_PROD`.

### API Container App (non-secret env)

**Important:** `azure-deploy.yml` always pushes these names to the Container App. If a **GitHub Variable is missing**, Actions expands it to **empty**, which **overrides** defaults in [`quack_db.config.Settings`](../src/quack_db/config.py) / [`.env.example`](../.env.example). For Azure, **set variables explicitly**.

| Variable | Set in Azure? | Default if unset | Notes |
| -------- | ------------- | ---------------- | ----- |
| `AZURE_OPENAI_ENDPOINT` | **Yes** in prod | example placeholder | Your Azure OpenAI resource URL. |
| `CHROMADB_HOST` | **Yes** | `localhost` | Internal Chroma hostname/FQDN in ACA. |
| `CHROMADB_PORT` | Recommended | `8000` | |
| `ENTRA_JWKS_URL` | **Yes** | `""` | e.g. `https://login.microsoftonline.com/<tenant-id>/discovery/v2.0/keys` |
| `ENTRA_AUDIENCE` | **Yes** | `""` | API app scope / Application ID URI audience. |
| `ENTRA_ISSUER` | **Yes** | `""` | e.g. `https://login.microsoftonline.com/<tenant-id>/v2.0` |
| `ENTRA_AUTO_PROVISION_TIER` | Optional | `""` | If set (e.g. `everyone`), first Entra login creates a DB user with that tier. Empty = admin must pre-create users by email. |
| `AUTH_DISABLED` | **Never in prod** | `false` | If `true`, API uses `DEV_IMPERSONATE_USER_EMAIL` (local dev only). |
| `DEV_IMPERSONATE_USER_EMAIL` | With `AUTH_DISABLED` | `""` | Existing `users.email` row to impersonate. |

### UI Container App (if you deploy UI)

Workflow sets container env `API_BASE_URL` from **`UI_API_BASE_URL`**.

| Variable | Set in Azure? | Default in [`app_config.py`](../app_config.py) if env is **unset** | Notes |
| -------- | ------------- | -------------------------------------------------------------------- | ----- |
| `UI_API_BASE_URL` | **Yes** | `http://127.0.0.1:8001` | Public `https://…` URL of the **API** Container App. |
| `ENABLE_UI_INGEST` | Optional | `false` | |
| `COLLECTIONS` | Optional | `test` | CSV |
| `DEFAULT_COLLECTION` | Optional | first entry of `COLLECTIONS` or `test` | |

---

## `azure-deploy.yml` (Azure Deploy)

**Manual only** (`workflow_dispatch`): **Target environment** `dev` / `prod` and per-component **true/false** choices for **Chroma / API / UI** (string choices so the build and deploy jobs agree). Builds only what you enable (`api/Dockerfile`; UI needs `./ui`— leave UI **false** if the folder is missing). Image tags look like `quack-api:{env}-{shortSha}` (and `:latest`). After changing workflow inputs, use **Re-run all jobs** if a previous run skipped the build but still tried to deploy.

Configure **Secrets** and **Variables** above. Resource group, region, Container Apps environment, and `APP_NAME_*` values come **only** from **Variables**.

**OIDC:** add a federated credential for each branch you dispatch from (e.g. `repo:OWNER/REPO:ref:refs/heads/main`). Avoid GitHub `environment:` on jobs unless you also add `repo:…:environment:*` credentials in Entra.

### Federated credentials (OIDC)

If `azure/login` fails with **AADSTS70025** (“client has no configured federated identity credentials”), the Entra **app registration** tied to `AZURE_CLIENT_ID` has no (matching) federated credential.

1. **Entra ID → App registrations →** your app → **Certificates & secrets → Federated credentials → Add credential.**
2. **Federated credential scenario:** GitHub Actions deploying Azure resources.
3. **Organization / repository:** your GitHub org or user and repo name (must match where the workflow runs).
4. **Entity type:** Branch, tag, or pull request — for runs triggered from `main`, use branch `main`. If you start the workflow from another branch, add a matching federated credential for that ref.

**Subject identifier** for this workflow (no GitHub `environment:` on jobs):

| | Example |
| -- | -- |
| Runs from `main` | `repo:OWNER/REPO:ref:refs/heads/main` |

Replace `OWNER/REPO` with your real path (case-sensitive). Add another federated credential if you run the workflow from other branches.

**AADSTS700213** with `environment:prod` in the error means some job still had `environment: prod` (or similar)—the subject then requires a matching **environment** federated credential. This repo’s `azure-deploy.yml` does not use that, so you should only see **branch** subjects.

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

### Quick outline

1. Create an Entra app registration; add a federated credential for each branch you use (e.g. `repo:OWNER/REPO:ref:refs/heads/main`).
2. Grant that app’s service principal **Contributor** (or narrower) on the subscription / RG / ACR as needed.
3. Add **Secrets** and **Variables** as documented above for **`azure-deploy.yml`**.

See [chromadb/AZURE.md](../chromadb/AZURE.md) for Postgres, Chroma wiring, and Container App env not covered by the workflows.
