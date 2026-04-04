"""
Reusable RAG query service.
Queries a ChromaDB collection and generates answers using an LLM.
"""
import os

from services.chroma_client import create_http_client
from services.embedding_function import openai_ef
from services import llm_api_wrapper

PROMPT_TEMPLATE = """
Answer the question based only on the following context.
If the context is empty, say clearly that no relevant context was found.
If asked what is in the context, summarize the retrieved context snippets and cite sources.

Context:
{context}

---

Question: {question}
"""


def query_rag(
    query_text: str,
    collection_name: str,
    *,
    role: str | None = None,
    prompt_template: str | None = None,
    debug: bool = False,
    n_results: int = 3,
    model: str = "default",
):
    """
    Query a ChromaDB collection with RAG and return the LLM response.

    Args:
        query_text: The user's question.
        collection_name: Name of the ChromaDB collection.
        role: Custom system role for the LLM (optional).
        prompt_template: Custom prompt template with {context} and {question} (optional).
        debug: Print context and metadata.
        n_results: Number of chunks to retrieve.
        model: LLM model name.

    Returns:
        Tuple of (response_text, context_text, metadatas).
    """
    chroma_client = create_http_client()
    try:
        collection = chroma_client.get_collection(
            name=collection_name, embedding_function=openai_ef
        )
    except Exception as exc:
        available = []
        try:
            for item in chroma_client.list_collections():
                available.append(getattr(item, "name", str(item)))
        except Exception:
            pass
        available_text = ", ".join(available) if available else "none"
        raise RuntimeError(
            f"Collection '{collection_name}' not found or not accessible. "
            f"Available collections: {available_text}."
        ) from exc

    try:
        collection_count = collection.count()
    except Exception:
        collection_count = None

    if collection_count == 0:
        return (
            f"Collection '{collection_name}' is empty. Please ingest documents first.",
            "",
            [],
        )

    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
    )

    ids = (results.get("ids") or [[]])[0]
    page_contents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]

    context_texts = []
    safe_metadatas = []
    for i in range(len(ids)):
        metadata = metadatas[i] if i < len(metadatas) and isinstance(metadatas[i], dict) else {}
        page_content = page_contents[i] if i < len(page_contents) else ""
        if not page_content or not str(page_content).strip():
            continue
        pdf_name = metadata.get("pdf_name", metadata.get("source", "unknown"))
        title = metadata.get("title", "")
        context_texts.append(f"[source: {pdf_name}, {title}]\n{page_content}")
        safe_metadatas.append(metadata)

    context_text = "\n\n---\n\n".join(context_texts)
    if not context_text.strip():
        response_text = (
            "Ich habe keine relevanten Kontextstellen aus der Datenbank gefunden. "
            "Bitte pruefe Collection, Ingest-Stand und Chroma-Verbindung."
        )
        return response_text, "", []

    if debug:
        print("Query:\n", query_text)
        if collection_count is not None:
            print("Collection count:\n", collection_count)
        print("Context:\n", context_text)
        print("Metadata:\n", safe_metadatas)
        print()

    template = prompt_template or PROMPT_TEMPLATE
    prompt = template.format(context=context_text, question=query_text)

    default_role = "Provide accurate and concise answers based solely on the given context."
    role = role or default_role

    response_text = llm_api_wrapper.basic_prompt(
        prompt, role=role, temperature=0.2, model=model
    )

    return response_text, context_text, safe_metadatas


def load_raw_document_content(doc_name: str, data_dir: str) -> str:
    """Load raw text or CSV file content from disk."""
    file_path = os.path.join(data_dir, doc_name)
    if file_path.endswith(".txt") or file_path.endswith(".csv"):
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    return "Content not available"


