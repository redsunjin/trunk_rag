from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from fastapi import HTTPException

from core.collection_manifest import build_seed_document_metadata
from core.settings import DATA_DIR, DEFAULT_COLLECTION_KEY
from services import collection_service, index_service, query_service, runtime_service, upload_service

ToolPayload = dict[str, object]
ToolAdapter = Callable[[ToolPayload, "ToolContext"], ToolPayload]


class ToolInputError(ValueError):
    pass


@dataclass(frozen=True)
class ToolContext:
    request_id: str = "-"
    actor: str = "internal"
    allow_mutation: bool = False
    timeout_seconds: float | None = None
    admin_code: str | None = None
    mutation_intent: str | None = None
    apply_envelope: dict[str, object] | None = None
    executor_binding: dict[str, object] | None = None


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    category: str
    side_effect: str
    input_schema: dict[str, object]
    output_schema: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "side_effect": self.side_effect,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
        }


@dataclass(frozen=True)
class RegisteredTool:
    definition: ToolDefinition
    adapter: ToolAdapter


def _object_schema(
    *,
    properties: dict[str, object] | None = None,
    required: list[str] | None = None,
) -> dict[str, object]:
    return {
        "type": "object",
        "properties": properties or {},
        "required": required or [],
        "additionalProperties": False,
    }


def _string_property(description: str) -> dict[str, str]:
    return {"type": "string", "description": description}


def _boolean_property(description: str) -> dict[str, str]:
    return {"type": "boolean", "description": description}


def _array_property(description: str) -> dict[str, object]:
    return {
        "type": "array",
        "description": description,
        "items": {"type": "string"},
    }


def _required_text(payload: ToolPayload, key: str) -> str:
    value = str(payload.get(key, "")).strip()
    if not value:
        raise ToolInputError(f"{key} is required.")
    return value


def _optional_text(payload: ToolPayload, key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _optional_bool(payload: ToolPayload, key: str, *, default: bool = False) -> bool:
    value = payload.get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _optional_text_list(payload: ToolPayload, key: str) -> list[str] | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, list):
        raise ToolInputError(f"{key} must be a list.")
    items = [str(item).strip() for item in value if str(item).strip()]
    return items or None


def _resolve_collection_key(value: str | None) -> str:
    return collection_service.resolve_collection_key(value) or DEFAULT_COLLECTION_KEY


def _tool_list_collections(_payload: ToolPayload, _context: ToolContext) -> ToolPayload:
    return {
        "default_collection_key": DEFAULT_COLLECTION_KEY,
        "compatibility_bundle": collection_service.get_compatibility_bundle_config(),
        "seed_corpus": collection_service.get_seed_corpus_config(),
        "collections": collection_service.list_collection_statuses(index_service.get_vector_count_fast),
    }


def _tool_health_check(_payload: ToolPayload, _context: ToolContext) -> ToolPayload:
    default_collection_name = collection_service.get_collection_name(DEFAULT_COLLECTION_KEY)
    default_llm = runtime_service.get_default_llm_config()
    query_timeout_seconds = runtime_service.get_query_timeout_seconds()
    vectors = index_service.get_vector_count_fast(default_collection_name) or 0
    release_web = runtime_service.build_release_web_guidance(
        vectors=vectors,
        default_llm_provider=str(default_llm["provider"] or "ollama"),
        default_llm_model=str(default_llm["model"] or "") or None,
        default_llm_base_url=str(default_llm["base_url"] or "") or None,
        query_timeout_seconds=query_timeout_seconds,
        embedding_model=runtime_service.get_embedding_model(),
    )
    return {
        "status": "ok",
        "collection_key": DEFAULT_COLLECTION_KEY,
        "collection": default_collection_name,
        "vectors": vectors,
        "seed_corpus": collection_service.get_seed_corpus_config(),
        "embedding_fingerprint": index_service.get_embedding_fingerprint_status(
            collection_service.list_default_runtime_collection_keys()
        ),
        "runtime_profile": release_web["runtime_profile"],
        "release_web_status": release_web["status"],
    }


def _tool_search_docs(payload: ToolPayload, _context: ToolContext) -> ToolPayload:
    query = _required_text(payload, "query")
    query_profile = query_service.normalize_query_profile(_optional_text(payload, "query_profile"))
    collection_keys, route_reason, _allow_default_fallback = collection_service.resolve_collection_keys_for_query(
        query,
        _optional_text(payload, "collection"),
        _optional_text_list(payload, "collections"),
        allow_keyword_routing=(query_profile == query_service.QUERY_PROFILE_SAMPLE_PACK),
    )
    default_llm = runtime_service.get_default_llm_config()
    budget = runtime_service.plan_query_budget(
        provider=str(default_llm["provider"] or "ollama"),
        model=str(default_llm["model"] or "") or None,
        timeout_seconds=runtime_service.get_query_timeout_seconds(),
        collection_count=len(collection_keys),
        route_reason=route_reason,
    )
    trace: dict[str, Any] = {}
    context_text = query_service.build_collection_context(
        question=query,
        collection_keys=collection_keys,
        trace=trace,
        budget=budget,
    )
    return {
        "query": query,
        "query_profile": query_profile,
        "collections": collection_keys,
        "route_reason": route_reason,
        "budget_profile": budget["profile"],
        "context": context_text,
        "sources": trace.get("sources", []),
        "trace": trace,
    }


def _find_seed_doc(collection_key: str, doc_key: str) -> ToolPayload | None:
    data_dir = Path(DATA_DIR)
    config = collection_service.get_collection_config(collection_key)
    for file_name in config.get("file_names", []):
        path = data_dir / str(file_name)
        if path.stem.lower() != doc_key:
            continue
        if not path.exists():
            continue
        return {
            "origin": "seed",
            "collection_key": collection_key,
            "doc_key": doc_key,
            "source_name": path.name,
            "content": path.read_text(encoding="utf-8"),
            "metadata": build_seed_document_metadata(path.name),
        }
    return None


def _find_managed_doc(collection_key: str, doc_key: str) -> ToolPayload | None:
    for item in upload_service.list_active_managed_docs(collection_key):
        if str(item.get("doc_key", "")).strip().lower() != doc_key:
            continue
        path = Path(str(item.get("file_path", "")))
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        return {
            "origin": "managed",
            "collection_key": collection_key,
            "doc_key": doc_key,
            "source_name": str(item.get("source_name", path.name if path.name else "")),
            "version_id": item.get("version_id"),
            "content": content,
            "metadata": item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
        }
    return None


def _tool_read_doc(payload: ToolPayload, _context: ToolContext) -> ToolPayload:
    collection_key = _resolve_collection_key(_optional_text(payload, "collection"))
    doc_key = _required_text(payload, "doc_key").lower()
    found = _find_managed_doc(collection_key, doc_key) or _find_seed_doc(collection_key, doc_key)
    if found is None:
        raise ToolInputError(f"doc_key not found in collection {collection_key}: {doc_key}")
    return found


def _tool_reindex(payload: ToolPayload, _context: ToolContext) -> ToolPayload:
    collection_key = _resolve_collection_key(_optional_text(payload, "collection"))
    return index_service.reindex(
        reset=_optional_bool(payload, "reset", default=True),
        collection_key=collection_key,
        include_compatibility_bundle=_optional_bool(payload, "include_compatibility_bundle", default=False),
    )


def _tool_list_upload_requests(payload: ToolPayload, _context: ToolContext) -> ToolPayload:
    return {
        "requests": upload_service.list_upload_requests(
            status=_optional_text(payload, "status"),
            reason=_optional_text(payload, "reason"),
            search=_optional_text(payload, "q"),
        )
    }


def _tool_approve_upload_request(payload: ToolPayload, _context: ToolContext) -> ToolPayload:
    return {
        "request": upload_service.approve_upload_request(
            request_id=_required_text(payload, "request_id"),
            code=_required_text(payload, "code"),
            collection=_optional_text(payload, "collection"),
        )
    }


def _tool_reject_upload_request(payload: ToolPayload, _context: ToolContext) -> ToolPayload:
    return {
        "request": upload_service.reject_upload_request(
            request_id=_required_text(payload, "request_id"),
            code=_required_text(payload, "code"),
            reason=_required_text(payload, "reason"),
            reason_code=_optional_text(payload, "reason_code"),
            decision_note=_optional_text(payload, "decision_note"),
        )
    }


def _build_registry() -> dict[str, RegisteredTool]:
    tools = [
        RegisteredTool(
            definition=ToolDefinition(
                name="search_docs",
                description="Retrieve context snippets from one or more RAG collections without invoking an LLM.",
                category="retrieval",
                side_effect="read",
                input_schema=_object_schema(
                    properties={
                        "query": _string_property("User question or search query."),
                        "collection": _string_property("Optional single collection key/name."),
                        "collections": _array_property("Optional collection key/name list."),
                        "query_profile": _string_property("generic or sample_pack."),
                    },
                    required=["query"],
                ),
                output_schema=_object_schema(),
            ),
            adapter=_tool_search_docs,
        ),
        RegisteredTool(
            definition=ToolDefinition(
                name="read_doc",
                description="Read an active seed or managed markdown document by collection and doc_key.",
                category="documents",
                side_effect="read",
                input_schema=_object_schema(
                    properties={
                        "collection": _string_property("Collection key/name. Defaults to core all."),
                        "doc_key": _string_property("Document key without extension."),
                    },
                    required=["doc_key"],
                ),
                output_schema=_object_schema(),
            ),
            adapter=_tool_read_doc,
        ),
        RegisteredTool(
            definition=ToolDefinition(
                name="list_collections",
                description="List collection manifest metadata and vector counts.",
                category="collections",
                side_effect="read",
                input_schema=_object_schema(),
                output_schema=_object_schema(),
            ),
            adapter=_tool_list_collections,
        ),
        RegisteredTool(
            definition=ToolDefinition(
                name="health_check",
                description="Return the core runtime readiness snapshot used by V1 release checks.",
                category="runtime",
                side_effect="read",
                input_schema=_object_schema(),
                output_schema=_object_schema(),
            ),
            adapter=_tool_health_check,
        ),
        RegisteredTool(
            definition=ToolDefinition(
                name="reindex",
                description="Run a collection reindex using the existing index service.",
                category="indexing",
                side_effect="write",
                input_schema=_object_schema(
                    properties={
                        "collection": _string_property("Collection key/name. Defaults to core all."),
                        "reset": _boolean_property("Whether to reset the target collection first."),
                        "include_compatibility_bundle": _boolean_property("Also reindex sample-pack compatibility routes."),
                    },
                ),
                output_schema=_object_schema(),
            ),
            adapter=_tool_reindex,
        ),
        RegisteredTool(
            definition=ToolDefinition(
                name="list_upload_requests",
                description="List upload requests with optional status, reason, or search filters.",
                category="uploads",
                side_effect="read",
                input_schema=_object_schema(
                    properties={
                        "status": _string_property("Optional request status filter."),
                        "reason": _string_property("Optional rejection reason search."),
                        "q": _string_property("Optional free-text search."),
                    },
                ),
                output_schema=_object_schema(),
            ),
            adapter=_tool_list_upload_requests,
        ),
        RegisteredTool(
            definition=ToolDefinition(
                name="approve_upload_request",
                description="Approve a pending upload request through the existing upload service.",
                category="uploads",
                side_effect="write",
                input_schema=_object_schema(
                    properties={
                        "request_id": _string_property("Upload request id."),
                        "code": _string_property("Admin code."),
                        "collection": _string_property("Optional approval collection override."),
                    },
                    required=["request_id", "code"],
                ),
                output_schema=_object_schema(),
            ),
            adapter=_tool_approve_upload_request,
        ),
        RegisteredTool(
            definition=ToolDefinition(
                name="reject_upload_request",
                description="Reject a pending upload request through the existing upload service.",
                category="uploads",
                side_effect="write",
                input_schema=_object_schema(
                    properties={
                        "request_id": _string_property("Upload request id."),
                        "code": _string_property("Admin code."),
                        "reason": _string_property("Human-readable rejection reason."),
                        "reason_code": _string_property("Optional normalized reason code."),
                        "decision_note": _string_property("Optional operator note."),
                    },
                    required=["request_id", "code", "reason"],
                ),
                output_schema=_object_schema(),
            ),
            adapter=_tool_reject_upload_request,
        ),
    ]
    return {tool.definition.name: tool for tool in tools}


TOOL_REGISTRY = _build_registry()


def list_tool_names() -> list[str]:
    return list(TOOL_REGISTRY.keys())


def list_tool_definitions() -> list[dict[str, object]]:
    return [tool.definition.as_dict() for tool in TOOL_REGISTRY.values()]


def get_tool_definition(name: str) -> dict[str, object]:
    try:
        return TOOL_REGISTRY[name].definition.as_dict()
    except KeyError as exc:
        raise ToolInputError(f"Unknown tool: {name}") from exc


def invoke_tool(
    name: str,
    payload: ToolPayload | None = None,
    *,
    context: ToolContext | None = None,
) -> dict[str, object]:
    resolved_payload = payload or {}
    if not isinstance(resolved_payload, dict):
        raise ToolInputError("payload must be an object.")

    binding = TOOL_REGISTRY.get(name)
    if binding is None:
        raise ToolInputError(f"Unknown tool: {name}")

    resolved_context = context or ToolContext()
    definition = binding.definition
    if definition.side_effect == "write" and not resolved_context.allow_mutation:
        return {
            "tool": name,
            "ok": False,
            "result": None,
            "error": {
                "code": "MUTATION_NOT_ALLOWED",
                "message": "This tool requires ToolContext.allow_mutation=True.",
            },
        }

    try:
        result = binding.adapter(resolved_payload, resolved_context)
    except HTTPException as exc:
        return {
            "tool": name,
            "ok": False,
            "result": None,
            "error": {
                "code": "HTTP_ERROR",
                "status_code": exc.status_code,
                "message": str(exc.detail),
            },
        }
    except Exception as exc:
        return {
            "tool": name,
            "ok": False,
            "result": None,
            "error": {
                "code": exc.__class__.__name__,
                "message": str(exc),
            },
        }

    return {
        "tool": name,
        "ok": True,
        "result": result,
        "error": None,
    }
