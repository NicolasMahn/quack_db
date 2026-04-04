"""Request/response models for API endpoints."""
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query_text: str = Field(..., min_length=1)
    collection: str = Field(..., min_length=1)
    n_results: int = Field(default=3, ge=1, le=8)
    model: str = Field(default="default")
    debug: bool = Field(default=False)


class QueryResponse(BaseModel):
    response_text: str
    context_text: str
    metadatas: list[dict]


class IngestRequest(BaseModel):
    data_dir: str = Field(default="test_data", min_length=1)
    collection: str = Field(..., min_length=1)
    chunk_size: int = Field(default=1200, ge=200, le=8000)
    overlap: int = Field(default=200, ge=0, le=2000)
    file_pattern: str = Field(default="**/*")

