"""Ingestion worker client that uses restricted API access."""
from __future__ import annotations

import argparse

from services.api_client import ingest_via_api


def main():
    parser = argparse.ArgumentParser(description="Run ingestion through Quack API")
    parser.add_argument(
        "data_dir",
        nargs="?",
        default="test_data",
        help="Directory containing PDF/DOCX files (default: test_data)",
    )
    parser.add_argument(
        "--collection",
        "-c",
        default="test",
        help="Target collection name",
    )
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--overlap", type=int, default=200)
    parser.add_argument("--file-pattern", default="**/*")
    args = parser.parse_args()

    chunks = ingest_via_api(
        data_dir=args.data_dir,
        collection=args.collection,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        file_pattern=args.file_pattern,
    )
    print(f"[OK] Ingested {chunks} chunks via API.")


if __name__ == "__main__":
    main()

