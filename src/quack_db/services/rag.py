"""RAG retrieve + LLM (ported from query_data)."""

from __future__ import annotations

from typing import Any

from quack_db.chroma.client import get_chroma_client
from quack_db.services import llm as llm_mod
from quack_db.services.embedding import get_embedding_function

PROMPT_TEMPLATE = """
Answer the question based only on the following context:
{context}

---

Answer the question based on the above context: {question}
"""


def query_rag(
    query_text: str,
    collection_names: list[str],
    *,
    prompt_template: str | None = None,
    debug: bool = False,
    n_results: int = 3,
    model: str = "default",
) -> tuple[str, str, list[dict[str, Any]]]:
    """
    Multi-collection RAG: query each readable collection, merge chunks, call LLM.

    `collection_names` must already be authorized server-side.
    """
    ef = get_embedding_function()
    client = get_chroma_client()

    merged_docs: list[str] = []
    merged_meta: list[dict] = []

    per_collection = max(1, n_results // max(1, len(collection_names)))
    for name in collection_names:
        collection = client.get_or_create_collection(name=name, embedding_function=ef)
        results = collection.query(query_texts=[query_text], n_results=per_collection)
        ids = results["ids"][0] if results["ids"] else []
        docs = results["documents"][0] if results.get("documents") else []
        metas = results["metadatas"][0] if results.get("metadatas") else []
        for i in range(len(ids)):
            merged_docs.append(docs[i])
            merged_meta.append(metas[i] if i < len(metas) else {})

    context_texts = []
    for i, page_content in enumerate(merged_docs):
        md = merged_meta[i] if i < len(merged_meta) else {}
        pdf_name = md.get("pdf_name", md.get("source", ""))
        title = md.get("title", "")
        context_texts.append(f"[source: {pdf_name}, {title}]\n{page_content}")

    context_text = "\n\n---\n\n".join(context_texts)
    template = prompt_template or PROMPT_TEMPLATE
    prompt = template.format(context=context_text, question=query_text)
    default_role = "Provide accurate and concise answers based solely on the given context."
    response_text = llm_mod.basic_prompt(prompt, role=default_role, temperature=0.2, model=model)

    if debug:
        print("Query:\n", query_text)
        print("Context:\n", context_text)

    return response_text, context_text, merged_meta


def default_collections_for_user(user) -> list[str]:
    """Default multi-collection RAG list: public + student (if readable) + user ctx."""
    from quack_db.authz import matrix

    names = []
    if matrix.rwmd_for_repo(user, "public").read:
        names.append("public")
    if matrix.rwmd_for_repo(user, "student").read:
        names.append("student")
    if matrix.rwmd_for_repo(user, "user_agent_context").read:
        names.append(matrix.user_ctx_collection_name(user.id))
    return names
