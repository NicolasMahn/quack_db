"""Document chunking and extract — shared by API batch ingest and CLI."""

from __future__ import annotations

import hashlib
from pathlib import Path

from docx import Document
from pypdf import PdfReader


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
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
    reader = PdfReader(file_path)
    parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def extract_docx_text(file_path: str) -> str:
    doc = Document(file_path)
    return "\n\n".join(para.text for para in doc.paragraphs if para.text.strip())


def extract_text(file_path: str) -> str | None:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_text(file_path)
    if suffix == ".docx":
        return extract_docx_text(file_path)
    return None


def build_chunks_for_paths(
    paths: list[str],
    *,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> tuple[list[str], list[str], list[dict]]:
    """Return (ids, documents, metadatas) for Chroma add."""
    all_ids: list[str] = []
    all_docs: list[str] = []
    all_meta: list[dict] = []

    for file_path in paths:
        path = Path(file_path)
        if not path.is_file():
            continue
        if path.suffix.lower() not in (".pdf", ".docx"):
            continue
        text = extract_text(str(path))
        if not text or not text.strip():
            continue
        rel = path.name
        chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        doc_name = path.name
        for i, chunk in enumerate(chunks):
            chunk_id = hashlib.sha256(f"{rel}:{i}:{chunk[:50]}".encode()).hexdigest()[:16]
            all_ids.append(chunk_id)
            all_docs.append(chunk)
            all_meta.append({
                "source": rel,
                "pdf_name": doc_name,
                "title": f"{doc_name} (chunk {i + 1}/{len(chunks)})",
            })

    return all_ids, all_docs, all_meta
