from chromadb.utils import embedding_functions

from app_config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, MODELS

_embedding_cfg = MODELS["text-embedding-3-large"]

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=AZURE_OPENAI_API_KEY,
    api_key_env_var="AZURE_OPENAI_API_KEY",
    model_name="text-embedding-3-large",
    api_type="azure",
    api_base=AZURE_OPENAI_ENDPOINT.rstrip("/"),
    api_version=_embedding_cfg["api_version"],
    deployment_id="text-embedding-3-large",
)


