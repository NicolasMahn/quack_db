# `src/` — installable package + tests

Python package **`quack_db`** is installed via `pip install -e .` from the repo root. Tests live in **`src/tests/`** (not shipped in the wheel). **`src/alembic.ini`** drives SQL migrations.

| Path | Role |
| ---- | ---- |
| `alembic.ini` | Alembic config — e.g. `alembic -c src/alembic.ini upgrade head` |
| `tests/` | `pytest` targets |
| `quack_db/config.py` | `pydantic-settings` env (`DATABASE_URL`, Chroma, Azure OpenAI, SMTP, …) |
| `quack_db/config.yaml` | Optional collection name defaults (`util.load_config`) |
| `quack_db/util.py` | YAML helpers, markdown code-block parsing |
| `quack_db/db/models.py` | SQLAlchemy models: `User`, `ApiKey`, `Session`, `Message` |
| `quack_db/db/session.py` | Engine + `get_db()` dependency helper |
| `quack_db/db/migrations/` | Alembic revisions — also run on API startup |
| `auth/api_keys.py` | Issue/verify bcrypt-hashed API keys |
| `authz/matrix.py` | `rwmd` matrix: repo × tier / dev flags; `user_ctx_{id}` naming |
| `chroma/client.py` | Cached `chromadb.HttpClient` |
| `services/embedding.py` | Azure OpenAI embedding function |
| `services/llm.py` | Azure / Gemini chat |
| `services/rag.py` | Multi-collection retrieve + LLM |
| `services/mail.py` | Optional SMTP for API key email |
| `ingest/core.py` | Chunk / extract PDF+DOCX for CLI or batch jobs |
| `ingest/cli.py` | Console script **`quack-ingest`** — POSTs chunks to `/collections/{name}/add` |
| `cli/query_local.py` | Console script **`quack-query`** — local RAG against Chroma (dev only) |

**Migrations** apply to **PostgreSQL** app tables only—not Chroma indexes. Chroma schema is managed through Chroma APIs (via the API gateway).
