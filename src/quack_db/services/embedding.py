"""Azure OpenAI embedding function (Chroma)."""

from functools import lru_cache

from chromadb.utils import embedding_functions

from quack_db.config import get_settings


@lru_cache
def get_embedding_function():
    s = get_settings()
    endpoint = (s.azure_openai_embedding_endpoint or s.azure_openai_endpoint).rstrip("/")
    key = s.azure_openai_embedding_api_key or s.azure_openai_api_key
    deployment = s.azure_openai_embedding_deployment
    return embedding_functions.OpenAIEmbeddingFunction(
        api_key=key,
        api_key_env_var="AZURE_OPENAI_EMBEDDING_API_KEY",
        model_name=deployment,
        api_type="azure",
        api_base=endpoint,
        api_version=s.azure_openai_api_version,
        deployment_id=deployment,
    )
