"""
Ingest documents into a ChromaDB collection.
Supports PDF and DOCX. Chunks text and embeds using the configured embedding function.
"""
import argparse
import hashlib
import os
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from services.chroma_client import create_http_client
from services.embedding_function import openai_ef


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks."""
    if not text.strip():
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap if end < len(text) else len(text)
    return chunks


def extract_pdf_text(file_path: str) -> str:
    """Extract text from a PDF file."""
    reader = PdfReader(file_path)
    parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def extract_docx_text(file_path: str) -> str:
    """Extract text from a DOCX file."""
    doc = Document(file_path)
    return "\n\n".join(para.text for para in doc.paragraphs if para.text.strip())


def extract_text(file_path: str) -> str | None:
    """Extract text from PDF or DOCX. Returns None for unsupported types."""
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_text(file_path)
    if suffix == ".docx":
        return extract_docx_text(file_path)
    return None


def ingest_directory(
    data_dir: str,
    collection_name: str,
    *,
    chunk_size: int = 1200,
    overlap: int = 200,
    file_pattern: str = "**/*",
) -> int:
    """
    Ingest all PDF and DOCX files from a directory into a ChromaDB collection.

    Returns:
        Number of chunks added.
    """
    chroma_client = create_http_client()
    collection = chroma_client.get_or_create_collection(
        name=collection_name, embedding_function=openai_ef
    )

    data_path = Path(data_dir)
    if not data_path.is_dir():
        raise ValueError(f"Not a directory: {data_dir}")

    all_ids = []
    all_docs = []
    all_metadatas = []

    for file_path in sorted(data_path.glob(file_pattern)):
        if file_path.is_file() and file_path.suffix.lower() in (".pdf", ".docx"):
            rel_path = str(file_path.relative_to(data_path))
            text = extract_text(str(file_path))
            if not text or not text.strip():
                print(f"  [WARN] Skipped (no text): {rel_path}")
                continue

            chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
            doc_name = file_path.name

            for i, chunk in enumerate(chunks):
                chunk_id = hashlib.sha256(
                    f"{rel_path}:{i}:{chunk[:50]}".encode()
                ).hexdigest()[:16]
                all_ids.append(chunk_id)
                all_docs.append(chunk)
                all_metadatas.append(
                    {
                        "source": rel_path,
                        "pdf_name": doc_name,
                        "title": f"{doc_name} (chunk {i + 1}/{len(chunks)})",
                    }
                )

            print(f"  [OK] {rel_path}: {len(chunks)} chunks")

    if not all_docs:
        print("No documents to ingest.")
        return 0

    # ChromaDB add has a limit per batch; chunk into batches of 100
    batch_size = 100
    for i in range(0, len(all_docs), batch_size):
        batch_ids = all_ids[i : i + batch_size]
        batch_docs = all_docs[i : i + batch_size]
        batch_metadatas = all_metadatas[i : i + batch_size]
        collection.add(ids=batch_ids, documents=batch_docs, metadatas=batch_metadatas)

    print(f"\n[OK] Ingested {len(all_docs)} chunks into collection '{collection_name}'")
    return len(all_docs)


def main():
    parser = argparse.ArgumentParser(description="Ingest documents into ChromaDB")
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
        help="ChromaDB collection name (default: test)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1200,
        help="Characters per chunk (default: 1200)",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=200,
        help="Overlap between chunks (default: 200)",
    )
    args = parser.parse_args()

    base = Path(__file__).resolve().parent.parent
    data_dir = (
        base / args.data_dir if not os.path.isabs(args.data_dir) else Path(args.data_dir)
    )

    print(f"Ingesting from {data_dir} -> collection '{args.collection}'")
    print()
    ingest_directory(
        str(data_dir),
        args.collection,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )


if __name__ == "__main__":
    main()


