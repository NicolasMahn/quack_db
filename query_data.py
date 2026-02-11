"""
Generic RAG query module.
Queries a ChromaDB collection and generates answers using an LLM.
"""
import argparse
import os

import chromadb
from chromadb.config import Settings

from load_secrets import CHROMADB_AUTH_TOKEN, CHROMADB_HOST, CHROMADB_PORT
from embedding_function import openai_ef
import llm_api_wrapper
import util


PROMPT_TEMPLATE = """
Answer the question based only on the following context:
{context}

---

Answer the question based on the above context: {question}
"""

WHITE = "\033[97m"
ORANGE = "\033[38;5;208m"
GREEN = "\033[32m"
RESET = "\033[0m"


def main():
    parser = argparse.ArgumentParser()
    config = util.load_config()
    collections = config.get("collections", ["default"])
    default_collection = config.get("default_collection", collections[0])

    parser.add_argument("--query_text", type=str, help="The query text.")
    parser.add_argument("--debug", action="store_true", help="Additional print statements.")
    parser.add_argument(
        "--collection",
        type=str,
        default=default_collection,
        help="ChromaDB collection name.",
    )
    args = parser.parse_args()

    if args.debug:
        print(f"{ORANGE}⭕ DEBUG Mode Active{RESET}")

    if not args.query_text:
        query_text = "What is this document about?"
        print(f"{WHITE}🔍 Using default test query: {query_text}{RESET}")
    else:
        query_text = args.query_text

    print(f"{WHITE}📄 Collection: {args.collection}{RESET}")

    response_text, _, _ = query_rag(
        query_text, args.collection, debug=args.debug
    )

    print(f"{WHITE}{response_text}{RESET}")
    print()


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
    client_kwargs = {"host": CHROMADB_HOST, "port": CHROMADB_PORT}
    if CHROMADB_AUTH_TOKEN:
        client_kwargs["settings"] = Settings(
            chroma_client_auth_provider="chromadb.auth.token_authn.TokenAuthClientProvider",
            chroma_client_auth_credentials=CHROMADB_AUTH_TOKEN,
        )
    chroma_client = chromadb.HttpClient(**client_kwargs)
    collection = chroma_client.get_or_create_collection(
        name=collection_name, embedding_function=openai_ef
    )

    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
    )

    ids = results["ids"][0]
    page_contents = results["documents"][0]
    metadatas = results["metadatas"][0]

    context_texts = []
    for i in range(len(ids)):
        pdf_name = metadatas[i].get("pdf_name", metadatas[i].get("source", ""))
        title = metadatas[i].get("title", "")
        page_content = page_contents[i]
        context_texts.append(f"[source: {pdf_name}, {title}]\n{page_content}")

    context_text = "\n\n---\n\n".join(context_texts)

    if debug:
        print("Query:\n", query_text)
        print("Context:\n", context_text)
        print("Metadata:\n", metadatas)
        print()

    template = prompt_template or PROMPT_TEMPLATE
    prompt = template.format(context=context_text, question=query_text)

    default_role = "Provide accurate and concise answers based solely on the given context."
    role = role or default_role

    response_text = llm_api_wrapper.basic_prompt(
        prompt, role=role, temperature=0.2, model=model
    )

    return response_text, context_text, metadatas


def load_raw_document_content(doc_name: str, data_dir: str) -> str:
    """Load raw text or CSV file content from disk."""
    file_path = os.path.join(data_dir, doc_name)
    if file_path.endswith(".txt") or file_path.endswith(".csv"):
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    return "Content not available"


if __name__ == "__main__":
    main()
