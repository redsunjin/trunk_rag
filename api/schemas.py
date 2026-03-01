from __future__ import annotations

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    llm_provider: str = Field(default="ollama")
    llm_model: str | None = None
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    collection: str | None = None
    collections: list[str] | None = None


class QueryResponse(BaseModel):
    answer: str
    provider: str
    model: str


class ReindexRequest(BaseModel):
    reset: bool = True
    collection: str | None = None


class AdminAuthRequest(BaseModel):
    code: str = Field(..., min_length=1)


class UploadRequestCreateRequest(BaseModel):
    content: str = Field(..., min_length=1)
    source_name: str | None = None
    collection: str | None = None
    country: str | None = None
    doc_type: str | None = None


class UploadRequestApproveAction(BaseModel):
    code: str = Field(..., min_length=1)
    collection: str | None = None


class UploadRequestRejectAction(BaseModel):
    code: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)
