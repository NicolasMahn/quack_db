from chromadb.utils import embedding_functions
from load_secrets import (
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_EMBEDDING_API_KEY,
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
    AZURE_OPENAI_EMBEDDING_ENDPOINT,
)

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=AZURE_OPENAI_EMBEDDING_API_KEY,
    api_key_env_var="AZURE_OPENAI_EMBEDDING_API_KEY",
    model_name=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
    api_type="azure",
    api_base=AZURE_OPENAI_EMBEDDING_ENDPOINT.rstrip("/"),
    api_version=AZURE_OPENAI_API_VERSION,
    deployment_id=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
)
