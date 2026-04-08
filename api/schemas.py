from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    llm_provider: str = Field(default="ollama")
    llm_model: str | None = None
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    query_profile: str | None = None
    collection: str | None = None
    collections: list[str] | None = None
    debug: bool = False


class QuerySource(BaseModel):
    source: str
    h2: str = ""
    collection_key: str = ""


class QueryMeta(BaseModel):
    request_id: str
    collections: list[str] = Field(default_factory=list)
    route_reason: str = "-"
    budget_profile: str | None = None
    support_level: str = "insufficient_context"
    support_reason: str = "retrieved_context_empty"
    citations: list[str] = Field(default_factory=list)
    stage_timings: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    invoke: dict[str, Any] = Field(default_factory=dict)
    sources: list[QuerySource] = Field(default_factory=list)


class QueryResponse(BaseModel):
    answer: str
    provider: str
    model: str
    meta: QueryMeta | None = None


class ReindexRequest(BaseModel):
    reset: bool = True
    collection: str | None = None
    include_compatibility_bundle: bool = False


class AdminAuthRequest(BaseModel):
    code: str = Field(..., min_length=1)


class UploadRequestCreateRequest(BaseModel):
    content: str = Field(..., min_length=1)
    source_name: str | None = None
    request_type: str | None = None
    doc_key: str | None = None
    change_summary: str | None = None
    collection: str | None = None
    country: str | None = None
    doc_type: str | None = None


class UploadRequestApproveAction(BaseModel):
    code: str = Field(..., min_length=1)
    collection: str | None = None


class UploadRequestRejectAction(BaseModel):
    code: str = Field(..., min_length=1)
    reason_code: str | None = None
    reason: str = Field(..., min_length=1)
    decision_note: str | None = None
