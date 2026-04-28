from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

QualityMode = Literal["semantic", "balanced", "quality"]


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    llm_provider: str = Field(default="ollama")
    llm_model: str | None = None
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    query_profile: str | None = None
    collection: str | None = None
    collections: list[str] | None = None
    timeout_seconds: int | None = Field(default=None, ge=1, le=180)
    quality_mode: QualityMode = "balanced"
    quality_stage: str | None = None
    debug: bool = False


class QuerySource(BaseModel):
    source: str
    h2: str = ""
    collection_key: str = ""


class QueryMeta(BaseModel):
    request_id: str
    query_profile: str = "generic"
    collections: list[str] = Field(default_factory=list)
    route_reason: str = "-"
    budget_profile: str | None = None
    quality_mode: str = "balanced"
    quality_stage: str = "balanced"
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


class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    query_profile: str | None = None
    collection: str | None = None
    collections: list[str] | None = None
    max_results: int = Field(default=3, ge=1, le=8)
    quality_mode: QualityMode = "semantic"


class SemanticSearchResult(BaseModel):
    rank: int
    source: str
    h2: str = ""
    collection_key: str = ""
    snippet: str


class SemanticSearchMeta(BaseModel):
    request_id: str
    query_profile: str = "generic"
    collections: list[str] = Field(default_factory=list)
    route_reason: str = "-"
    search_mode: str = "semantic_fallback"
    retrieval_strategy: str = "-"
    stage_timings: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)


class SemanticSearchResponse(BaseModel):
    query: str
    results: list[SemanticSearchResult] = Field(default_factory=list)
    meta: SemanticSearchMeta


class QueryFeedbackRequest(BaseModel):
    request_id: str | None = None
    query: str = Field(..., min_length=1)
    answer: str | None = None
    rating: Literal["positive", "negative", "quality_request"]
    reason_tags: list[str] = Field(default_factory=list)
    note: str | None = None
    quality_mode: QualityMode = "balanced"
    quality_stage: str | None = None
    provider: str | None = None
    model: str | None = None
    collections: list[str] = Field(default_factory=list)
    sources: list[QuerySource] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class QueryFeedbackResponse(BaseModel):
    accepted: bool
    feedback_id: str
    request_id: str
    storage: str


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
