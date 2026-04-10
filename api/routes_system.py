from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.schemas import AdminAuthRequest, ReindexRequest
from core.settings import DEFAULT_COLLECTION_KEY, PERSIST_DIR, REQUEST_STATUS_PENDING, REQUEST_STATUSES
from services import collection_service, index_service, runtime_service, upload_service

router = APIRouter()
OPS_BASELINE_REPORT_PATH = Path(__file__).resolve().parents[1] / "docs/reports/ops_baseline_gate_latest.json"


def _empty_ops_baseline_summary() -> dict[str, object]:
    return {
        "cases": 0,
        "passed": 0,
        "pass_rate": 0.0,
        "avg_latency_ms": 0.0,
        "p95_latency_ms": 0.0,
        "avg_weighted_score": 0.0,
    }


def _ops_baseline_payload(
    *,
    status: str,
    message: str,
    hint: str,
    ready: bool = False,
    generated_at: str | None = None,
    summary: dict[str, object] | None = None,
    diagnostics: list[dict[str, object]] | None = None,
    collections_ready: bool = False,
    missing_keys: list[str] | None = None,
    runtime_ready: bool = False,
) -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[1]
    try:
        report_path = str(OPS_BASELINE_REPORT_PATH.relative_to(repo_root))
    except ValueError:
        report_path = str(OPS_BASELINE_REPORT_PATH)
    return {
        "status": status,
        "message": message,
        "hint": hint,
        "report_path": report_path,
        "ready": ready,
        "generated_at": generated_at,
        "summary": summary or _empty_ops_baseline_summary(),
        "diagnostics": diagnostics or [],
        "collections_ready": collections_ready,
        "missing_keys": missing_keys or [],
        "runtime_ready": runtime_ready,
    }


@router.get("/health")
def health() -> dict[str, object]:
    default_collection = collection_service.get_collection_name(DEFAULT_COLLECTION_KEY)
    default_runtime_collection_keys = collection_service.list_default_runtime_collection_keys()
    compatibility_bundle = collection_service.get_compatibility_bundle_config()
    seed_corpus = collection_service.get_seed_corpus_config()
    compatibility_bundle_keys = list(compatibility_bundle.get("collection_keys", []))
    pending_count = len(upload_service.list_upload_requests(status=REQUEST_STATUS_PENDING))
    chunking = runtime_service.get_chunking_config()
    default_llm = runtime_service.get_default_llm_config()
    query_timeout_seconds = runtime_service.get_query_timeout_seconds()
    vectors = index_service.get_vector_count_fast(default_collection) or 0
    runtime_budget = runtime_service.plan_query_budget(
        provider=str(default_llm["provider"] or "ollama"),
        model=str(default_llm["model"] or "") or None,
        timeout_seconds=query_timeout_seconds,
        collection_count=1,
        route_reason="default",
    )
    embedding_status = index_service.get_embedding_fingerprint_status(default_runtime_collection_keys)
    compatibility_embedding_status = index_service.get_embedding_fingerprint_status(compatibility_bundle_keys)
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
        "collection": default_collection,
        "default_runtime_collection_keys": default_runtime_collection_keys,
        "compatibility_bundle_key": compatibility_bundle["key"],
        "compatibility_bundle_label": compatibility_bundle["label"],
        "compatibility_bundle_collection_keys": compatibility_bundle["collection_keys"],
        "compatibility_bundle_optional": compatibility_bundle["optional"],
        "seed_corpus_key": seed_corpus["key"],
        "seed_corpus_label": seed_corpus["label"],
        "seed_corpus_role": seed_corpus["role"],
        "seed_corpus_dataset": seed_corpus["dataset"],
        "seed_corpus_description": seed_corpus["description"],
        "persist_dir": PERSIST_DIR,
        "vectors": vectors,
        "auto_approve": runtime_service.is_auto_approve_enabled(),
        "pending_requests": pending_count,
        "chunking_mode": chunking["mode"],
        "embedding_model": runtime_service.get_embedding_model(),
        "query_timeout_seconds": query_timeout_seconds,
        "max_context_chars": runtime_service.get_max_context_chars(),
        "default_llm_provider": default_llm["provider"],
        "default_llm_model": default_llm["model"],
        "default_llm_base_url": default_llm["base_url"],
        "runtime_profile_status": release_web["runtime_profile"]["status"],
        "runtime_profile_scope": release_web["runtime_profile"]["scope"],
        "runtime_profile_message": release_web["runtime_profile"]["message"],
        "runtime_profile_recommendation": release_web["runtime_profile"]["recommendation"],
        "runtime_query_budget_profile": runtime_budget["profile"],
        "runtime_query_budget_summary": runtime_budget["summary"],
        "embedding_fingerprint_status": embedding_status["status"],
        "embedding_fingerprint_message": embedding_status["message"],
        "embedding_fingerprint_details": embedding_status["items"],
        "compatibility_bundle_embedding_fingerprint_status": compatibility_embedding_status["status"],
        "compatibility_bundle_embedding_fingerprint_message": compatibility_embedding_status["message"],
        "compatibility_bundle_embedding_fingerprint_details": compatibility_embedding_status["items"],
        "release_web_status": release_web["status"],
        "release_web_headline": release_web["headline"],
        "release_web_steps": release_web["steps"],
    }


@router.get("/collections")
def collections() -> dict[str, object]:
    return {
        "default_collection_key": DEFAULT_COLLECTION_KEY,
        "auto_approve": runtime_service.is_auto_approve_enabled(),
        "collections": collection_service.list_collection_statuses(index_service.get_vector_count_fast),
    }


@router.get("/ops-baseline/latest")
def ops_baseline_latest() -> dict[str, object]:
    if not OPS_BASELINE_REPORT_PATH.exists():
        return _ops_baseline_payload(
            status="missing",
            message="최근 ops-baseline 게이트 보고서가 없습니다.",
            hint="`./.venv/bin/python scripts/check_ops_baseline_gate.py --llm-provider ollama --llm-model gemma4:e4b --llm-base-url http://localhost:11434`를 실행해 최신 보고서를 생성하세요.",
        )

    try:
        payload = json.loads(OPS_BASELINE_REPORT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _ops_baseline_payload(
            status="invalid",
            message="ops-baseline 게이트 보고서를 읽을 수 없습니다.",
            hint="보고서 JSON 형식을 확인하고 `scripts/check_ops_baseline_gate.py`를 다시 실행하세요.",
        )

    if not isinstance(payload, dict):
        return _ops_baseline_payload(
            status="invalid",
            message="ops-baseline 게이트 보고서 형식이 올바르지 않습니다.",
            hint="보고서 JSON 형식을 확인하고 `scripts/check_ops_baseline_gate.py`를 다시 실행하세요.",
        )

    eval_payload = payload.get("eval", {})
    eval_summary = eval_payload.get("summary", {}) if isinstance(eval_payload, dict) else {}
    collections_payload = payload.get("collections", {})
    runtime_payload = payload.get("runtime", {})
    diagnostics = payload.get("diagnostics", [])
    return _ops_baseline_payload(
        status="ok",
        message="최근 ops-baseline 게이트 보고서를 읽었습니다.",
        hint="릴리즈 전에는 최신 보고서 시각과 pass/fail 상태를 함께 확인하세요.",
        ready=bool(payload.get("ready", False)),
        generated_at=str(payload.get("generated_at")) if payload.get("generated_at") else None,
        summary=eval_summary if isinstance(eval_summary, dict) else _empty_ops_baseline_summary(),
        diagnostics=diagnostics if isinstance(diagnostics, list) else [],
        collections_ready=bool(collections_payload.get("ready", False)) if isinstance(collections_payload, dict) else False,
        missing_keys=[
            str(item)
            for item in collections_payload.get("missing_keys", [])
        ] if isinstance(collections_payload, dict) and isinstance(collections_payload.get("missing_keys", []), list) else [],
        runtime_ready=bool(runtime_payload.get("ready", False)) if isinstance(runtime_payload, dict) else False,
    )


@router.get("/upload-requests")
def upload_requests(
    status: str | None = None,
    reason: str | None = None,
    q: str | None = None,
) -> dict[str, object]:
    if status:
        value = status.strip().lower()
        if value not in REQUEST_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported status. Use one of: {', '.join(sorted(REQUEST_STATUSES))}",
            )

    items = upload_service.list_upload_requests(status=status, reason=reason, search=q)
    counts = {
        "pending": 0,
        "approved": 0,
        "rejected": 0,
    }
    for item in upload_service.list_upload_requests(status=None):
        current = str(item.get("status", "")).lower()
        if current in counts:
            counts[current] += 1

    return {
        "auto_approve": runtime_service.is_auto_approve_enabled(),
        "counts": counts,
        "requests": items,
    }


@router.post("/reindex")
def reindex_endpoint(req: ReindexRequest) -> dict[str, object]:
    try:
        collection_key = collection_service.resolve_collection_key(req.collection) or DEFAULT_COLLECTION_KEY
    except ValueError as exc:
        supported = ", ".join(collection_service.list_collection_keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported collection. Use one of: {supported}",
        ) from exc
    return index_service.reindex(
        reset=req.reset,
        collection_key=collection_key,
        include_compatibility_bundle=req.include_compatibility_bundle,
    )


@router.post("/admin/auth")
def admin_auth(req: AdminAuthRequest) -> dict[str, bool]:
    runtime_service.verify_admin_code(req.code)
    return {"ok": True}
