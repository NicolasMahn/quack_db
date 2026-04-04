# Chroma (optional local)

This compose file is **optional**. The plan is **cloud-first**: the real stack runs on **Azure Container Apps** (see [AZURE.md](./AZURE.md)).

## Quick try

```bash
cd chromadb
cp .env.example .env
# edit .env — set CHROMA_SERVER_AUTH_CREDENTIALS
docker compose up -d
```

Full Azure steps: [AZURE.md](./AZURE.md).

Point the API at this instance with:

- `CHROMADB_HOST=localhost`
- `CHROMADB_PORT=8000`
- `CHROMADB_AUTH_TOKEN=<same as CHROMA_SERVER_AUTH_CREDENTIALS>`

Image tag `0.5.23` is pinned for reproducibility; bump when you intentionally upgrade Chroma.
