"""
Local RAG script using `quack_db.services.rag` (needs Chroma + Azure env).

Prefer `POST /rag/query` on the deployed API for cloud-first workflows.
"""

from __future__ import annotations

import argparse
import uuid

from quack_db.authz import matrix
from quack_db.db.models import User
from quack_db.services import rag as rag_mod


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query_text", type=str, default="What is this document about?")
    parser.add_argument("--collection", type=str, default="test")
    args = parser.parse_args()

    u = User(
        id=uuid.uuid4(),
        email="local@example.com",
        tier="board",
        is_dev_student=False,
        is_dev_admin=True,
    )
    names = [args.collection] if args.collection else matrix.list_readable_collections(u)
    text, _, _ = rag_mod.query_rag(args.query_text, names, n_results=3)
    print(text)


if __name__ == "__main__":
    main()
