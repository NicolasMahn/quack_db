"""CLI: ingest files via API (not direct Chroma)."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import httpx

from quack_db.ingest.core import build_chunks_for_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents via quack API")
    parser.add_argument(
        "paths",
        nargs="+",
        help="PDF/DOCX file paths",
    )
    parser.add_argument("--collection", "-c", default="test", help="Target collection")
    parser.add_argument(
        "--api-url",
        default=os.environ.get("QUACK_API_URL", "http://127.0.0.1:8000"),
        help="API base URL",
    )
    parser.add_argument(
        "--bearer",
        default=os.environ.get("QUACK_BEARER_TOKEN", ""),
        help="Authorization bearer: Entra access token for this API (or QUACK_BEARER_TOKEN)",
    )
    args = parser.parse_args()
    if not args.bearer:
        raise SystemExit(
            "Set --bearer or QUACK_BEARER_TOKEN "
            "(e.g. az account get-access-token --resource <api-client-id>)"
        )

    resolved = [str(Path(p).resolve()) for p in args.paths]
    ids, docs, metas = build_chunks_for_paths(resolved)
    if not docs:
        print("No documents to ingest.")
        return

    url = args.api_url.rstrip("/") + f"/collections/{args.collection}/add"
    headers = {"Authorization": f"Bearer {args.bearer}"}
    batch = 100
    with httpx.Client(timeout=120.0) as client:
        for i in range(0, len(docs), batch):
            body = {
                "ids": ids[i : i + batch],
                "documents": docs[i : i + batch],
                "metadatas": metas[i : i + batch],
            }
            r = client.post(url, json=body, headers=headers)
            r.raise_for_status()
            print(f"Posted batch {i // batch + 1}, status {r.status_code}")

    print(f"Ingested {len(docs)} chunks into '{args.collection}' via API")


if __name__ == "__main__":
    main()
