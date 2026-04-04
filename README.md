# Quack DB

RAG stack with **FastAPI** as the **Chroma gateway**, **PostgreSQL** for users/sessions/messages, and **Azure** as the primary deployment target.

Application code lives in **three trees**; the repo root only keeps packaging (`pyproject.toml`), env template, and CI.

| Location | What |
| -------- | ---- |
| [`api/`](api/) | FastAPI app + `Dockerfile` |
| [`src/`](src/) | **`quack_db` package**, `src/alembic.ini`, **`src/tests/`** |
| [`chromadb/`](chromadb/) | Optional local Chroma compose + [`AZURE.md`](chromadb/AZURE.md) |
| [`.github/`](.github/) | CI + deploy workflows |

**Quick pointers:** [`api/README.md`](api/README.md) (HTTP + bootstrap), [`src/README.md`](src/README.md) (package + migrations + tests), [`chromadb/AZURE.md`](chromadb/AZURE.md) (cloud), [`.github/README.md`](.github/README.md) (OIDC secrets).

Install: `pip install -e ".[dev]"` from repo root. Tests: `python -m pytest`. CLIs: `quack-ingest`, `quack-query`.
