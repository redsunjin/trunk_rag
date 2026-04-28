from __future__ import annotations

import inspect
import json
import logging
import time

from fastapi import APIRouter, Request, Response
from chromadb.errors import InvalidDimensionException

from api.schemas import (
    QueryMeta,
    QueryFeedbackRequest,
    QueryFeedbackResponse,
    QueryRequest,
    QueryResponse,
    QuerySource,
    SemanticSearchMeta,
    SemanticSearchRequest,
    SemanticSearchResponse,
    SemanticSearchResult,
)
from core.errors import QueryAPIError
from core.settings import DEFAULT_COLLECTION_KEY, MAX_QUERY_COLLECTIONS, SEARCH_FETCH_K, SEARCH_K
from services import collection_service, feedback_service, index_service, query_service, runtime_service
from common import create_chat_llm, default_llm_model, resolve_llm_config

router = APIRouter()
logger = logging.getLogger("doc_rag.api")

SEMANTIC_FALLBACK_CONTEXT_CHARS = 1200
SEMANTIC_FALLBACK_SNIPPET_CHARS = 360


def _serialize_stage_timings(
    *,
    route_reason: str | None,
    stage_timings: dict[str, int | float | str | list[str]],
    context_trace: dict[str, object],
    invoke_trace: dict[str, object],
) -> str:
    payload: dict[str, object] = {
        "route_reason": route_reason or "-",
        "stages": stage_timings,
    }
    if context_trace:
        payload["context"] = context_trace
    if invoke_trace:
        payload["invoke"] = invoke_trace
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _model_dump(model) -> dict[str, object]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _build_citation_labels(sources: list[dict[str, object]]) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for item in sources:
        source = str(item.get("source", "unknown")).strip() or "unknown"
        h2 = str(item.get("h2", "")).strip()
        label = f"{source} > {h2}" if h2 else source
        if label in seen:
            continue
        seen.add(label)
        labels.append(label)
    return labels[:3]


def _classify_support(
    *,
    context_trace: dict[str, object],
    invoke_trace: dict[str, object],
    citations: list[str],
) -> tuple[str, str]:
    docs_total = int(context_trace.get("docs_total", 0) or 0)
    context_chars = int(context_trace.get("context_chars", 0) or 0)
    invoke_status = str(invoke_trace.get("status", "") or "")
    if not citations or docs_total <= 0:
        return "insufficient_context", "retrieved_context_empty"
    if invoke_status != "ok":
        return "insufficient_context", "invoke_not_completed"
    if docs_total >= 2 and context_chars >= 300:
        return "supported", "multiple_context_segments"
    return "limited", "single_or_short_context"


def _build_semantic_search_budget(
    *,
    max_results: int,
    collection_count: int,
    route_reason: str,
) -> dict[str, object]:
    is_multi = collection_count > 1 or "multi" in route_reason
    per_collection_k = 2 if is_multi else min(max_results, SEARCH_K)
    return {
        "profile": "semantic_fallback",
        "summary": (
            f"profile=semantic_fallback | k={per_collection_k} | fetch_k={SEARCH_FETCH_K} | "
            f"max_docs={max_results} | context={SEMANTIC_FALLBACK_CONTEXT_CHARS}"
        ),
        "per_collection_k": per_collection_k,
        "per_collection_fetch_k": SEARCH_FETCH_K,
        "max_total_docs": max_results,
        "max_context_chars": SEMANTIC_FALLBACK_CONTEXT_CHARS,
    }


def _snippet(text: str, *, limit: int = SEMANTIC_FALLBACK_SNIPPET_CHARS) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "..."


def _semantic_search_result(rank: int, item) -> SemanticSearchResult:
    return SemanticSearchResult(
        rank=rank,
        source=str(item.metadata.get("source", "unknown")),
        h2=str(item.metadata.get("h2", "")),
        collection_key=str(item.metadata.get("collection_key", "")),
        snippet=_snippet(str(item.page_content or "")),
    )


@router.post("/semantic-search", response_model=SemanticSearchResponse)
def semantic_search(req: SemanticSearchRequest, request: Request, response: Response) -> SemanticSearchResponse:
    from core.http import get_or_create_request_id

    request_id = get_or_create_request_id(request)
    response.headers["X-Request-ID"] = request_id
    started_at = time.perf_counter()
    route_reason = "-"
    stage_timings: dict[str, int | float | str | list[str]] = {}
    context_trace: dict[str, object] = {}
    resolved_query_profile = query_service.normalize_query_profile(req.query_profile)
    stage_timings["query_profile"] = resolved_query_profile
    stage_timings["search_mode"] = "semantic_fallback"
    stage_timings["quality_mode"] = req.quality_mode
    response.headers["X-RAG-Quality-Mode"] = req.quality_mode

    try:
        try:
            route_started_at = time.perf_counter()
            collection_keys, route_reason, allow_default_fallback = collection_service.resolve_collection_keys_for_query(
                req.query,
                req.collection,
                req.collections,
                allow_keyword_routing=(resolved_query_profile == query_service.QUERY_PROFILE_SAMPLE_PACK),
            )
            stage_timings["resolve_route_ms"] = round((time.perf_counter() - route_started_at) * 1000, 3)
            stage_timings["requested_collections"] = list(collection_keys)
        except ValueError as exc:
            supported = ", ".join(collection_service.list_collection_keys())
            raise QueryAPIError(
                code="INVALID_COLLECTION",
                status_code=400,
                message="지원하지 않는 collection입니다.",
                hint=f"지원값: {supported}, 최대 {MAX_QUERY_COLLECTIONS}개 선택 가능",
            ) from exc

        active_collection_keys: list[str] = []
        collection_probe_started_at = time.perf_counter()
        for key in collection_keys:
            vectors = index_service.get_vector_count_snapshot(key)
            if vectors is None:
                db = index_service.get_db(key)
                vectors = index_service.get_vector_count(db)
            if (vectors or 0) > 0:
                active_collection_keys.append(key)

        if (
            not active_collection_keys
            and allow_default_fallback
            and DEFAULT_COLLECTION_KEY not in collection_keys
        ):
            fallback_vector_count = index_service.get_vector_count_snapshot(DEFAULT_COLLECTION_KEY)
            if fallback_vector_count is None:
                fallback_db = index_service.get_db(DEFAULT_COLLECTION_KEY)
                fallback_vector_count = index_service.get_vector_count(fallback_db)
            if (fallback_vector_count or 0) > 0:
                active_collection_keys = [DEFAULT_COLLECTION_KEY]
                route_reason = f"{route_reason}->fallback"
        stage_timings["active_collection_probe_ms"] = round(
            (time.perf_counter() - collection_probe_started_at) * 1000,
            3,
        )
        stage_timings["active_collections"] = list(active_collection_keys)

        if not active_collection_keys:
            selected_names = [collection_service.get_collection_name(key) for key in collection_keys]
            hint_value = ",".join(selected_names)
            raise QueryAPIError(
                code="VECTORSTORE_EMPTY",
                status_code=400,
                message="선택된 컬렉션에 인덱스가 없습니다. 먼저 /reindex를 실행하세요.",
                hint=f"collections={hint_value} | Reindex 또는 build_index.py --reset 을 실행하세요.",
            )

        embedding_status = index_service.get_embedding_fingerprint_status(active_collection_keys)
        stage_timings["embedding_fingerprint_status"] = str(embedding_status["status"])
        if embedding_status["status"] == "mismatch":
            raise QueryAPIError(
                code="VECTORSTORE_EMBEDDING_MISMATCH",
                status_code=409,
                message="현재 임베딩 모델과 저장된 인덱스 fingerprint가 맞지 않습니다.",
                hint="Reindex 또는 build_index.py --reset 을 실행하고 DOC_RAG_EMBEDDING_MODEL 설정을 확인하세요.",
            )

        active_collection_names = [collection_service.get_collection_name(key) for key in active_collection_keys]
        response.headers["X-RAG-Collection"] = active_collection_names[0]
        response.headers["X-RAG-Collections"] = ",".join(active_collection_names)
        response.headers["X-RAG-Route-Reason"] = route_reason
        response.headers["X-RAG-Query-Profile"] = resolved_query_profile
        response.headers["X-RAG-Search-Mode"] = "semantic_fallback"

        budget = _build_semantic_search_budget(
            max_results=req.max_results,
            collection_count=len(active_collection_keys),
            route_reason=route_reason,
        )
        stage_timings["budget_profile"] = "semantic_fallback"
        retrieval_started_at = time.perf_counter()
        docs = query_service.retrieve_collection_documents(
            question=req.query,
            collection_keys=active_collection_keys,
            trace=context_trace,
            budget=budget,
        )
        stage_timings["semantic_retrieval_ms"] = round((time.perf_counter() - retrieval_started_at) * 1000, 3)
        results = [
            _semantic_search_result(index, item)
            for index, item in enumerate(docs[: req.max_results], start=1)
        ]
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.info(
            "semantic_search request_id=%s code=OK collections=%s route=%s results=%d elapsed_ms=%d timings=%s",
            request_id,
            ",".join(active_collection_names),
            route_reason,
            len(results),
            elapsed_ms,
            _serialize_stage_timings(
                route_reason=route_reason,
                stage_timings=stage_timings,
                context_trace=context_trace,
                invoke_trace={},
            ),
        )
        return SemanticSearchResponse(
            query=req.query,
            results=results,
            meta=SemanticSearchMeta(
                request_id=request_id,
                query_profile=resolved_query_profile,
                collections=active_collection_keys,
                route_reason=route_reason,
                retrieval_strategy=str(context_trace.get("retrieval_strategy", "-")),
                stage_timings=stage_timings,
                context={key: value for key, value in context_trace.items() if key != "sources"},
            ),
        )
    except QueryAPIError as exc:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.warning(
            "semantic_search request_id=%s code=%s elapsed_ms=%d timings=%s",
            request_id,
            exc.code,
            elapsed_ms,
            _serialize_stage_timings(
                route_reason=route_reason,
                stage_timings=stage_timings,
                context_trace=context_trace,
                invoke_trace={},
            ),
        )
        raise exc


@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest, request: Request, response: Response) -> QueryResponse:
    from core.http import get_or_create_request_id

    request_id = get_or_create_request_id(request)
    response.headers["X-Request-ID"] = request_id
    started_at = time.perf_counter()
    log_provider = req.llm_provider
    log_model = req.llm_model or "-"
    log_collection = collection_service.get_collection_name(DEFAULT_COLLECTION_KEY)
    route_reason = "-"
    stage_timings: dict[str, int | float | str | list[str]] = {}
    context_trace: dict[str, object] = {}
    invoke_trace: dict[str, object] = {}
    query_budget: dict[str, object] | None = None
    resolved_query_profile = query_service.QUERY_PROFILE_GENERIC
    quality_stage = req.quality_stage or req.quality_mode

    try:
        stage_timings["quality_mode"] = req.quality_mode
        stage_timings["quality_stage"] = quality_stage
        response.headers["X-RAG-Quality-Mode"] = req.quality_mode
        response.headers["X-RAG-Quality-Stage"] = quality_stage
        if req.quality_mode == "semantic":
            raise QueryAPIError(
                code="QUALITY_MODE_REQUIRES_SEMANTIC_SEARCH",
                status_code=400,
                message="semantic 모드는 LLM 질의 없이 /semantic-search를 사용해야 합니다.",
                hint="/query에는 balanced 또는 quality 모드를 사용하고, semantic 전용 검색은 /semantic-search로 호출하세요.",
            )

        query_timeout_seconds = req.timeout_seconds or runtime_service.get_query_timeout_seconds()
        stage_timings["timeout_seconds"] = query_timeout_seconds
        try:
            config_started_at = time.perf_counter()
            desired_model = req.llm_model or default_llm_model(req.llm_provider)
            provider, model, api_key, base_url = resolve_llm_config(
                provider=req.llm_provider,
                model=desired_model,
                api_key=req.llm_api_key,
                base_url=req.llm_base_url,
            )
            stage_timings["resolve_config_ms"] = round((time.perf_counter() - config_started_at) * 1000, 3)
        except ValueError as exc:
            raise QueryAPIError(
                code="INVALID_PROVIDER",
                status_code=400,
                message="지원하지 않는 llm_provider입니다.",
                hint="openai, ollama, lmstudio, groq 중 하나를 사용하세요.",
            ) from exc

        log_provider = provider
        log_model = model
        resolved_query_profile = query_service.normalize_query_profile(req.query_profile)
        stage_timings["query_profile"] = resolved_query_profile

        try:
            route_started_at = time.perf_counter()
            collection_keys, route_reason, allow_default_fallback = collection_service.resolve_collection_keys_for_query(
                req.query,
                req.collection,
                req.collections,
                allow_keyword_routing=(resolved_query_profile == query_service.QUERY_PROFILE_SAMPLE_PACK),
            )
            stage_timings["resolve_route_ms"] = round((time.perf_counter() - route_started_at) * 1000, 3)
            stage_timings["requested_collections"] = list(collection_keys)
        except ValueError as exc:
            supported = ", ".join(collection_service.list_collection_keys())
            raise QueryAPIError(
                code="INVALID_COLLECTION",
                status_code=400,
                message="지원하지 않는 collection입니다.",
                hint=f"지원값: {supported}, 최대 {MAX_QUERY_COLLECTIONS}개 선택 가능",
            ) from exc

        active_collection_keys: list[str] = []
        collection_probe_started_at = time.perf_counter()
        for key in collection_keys:
            vectors = index_service.get_vector_count_snapshot(key)
            if vectors is None:
                db = index_service.get_db(key)
                vectors = index_service.get_vector_count(db)
            if (vectors or 0) > 0:
                active_collection_keys.append(key)

        if (
            not active_collection_keys
            and allow_default_fallback
            and DEFAULT_COLLECTION_KEY not in collection_keys
        ):
            fallback_vector_count = index_service.get_vector_count_snapshot(DEFAULT_COLLECTION_KEY)
            if fallback_vector_count is None:
                fallback_db = index_service.get_db(DEFAULT_COLLECTION_KEY)
                fallback_vector_count = index_service.get_vector_count(fallback_db)
            if (fallback_vector_count or 0) > 0:
                active_collection_keys = [DEFAULT_COLLECTION_KEY]
                route_reason = f"{route_reason}->fallback"
        stage_timings["active_collection_probe_ms"] = round(
            (time.perf_counter() - collection_probe_started_at) * 1000,
            3,
        )
        stage_timings["active_collections"] = list(active_collection_keys)

        if not active_collection_keys:
            selected_names = [collection_service.get_collection_name(key) for key in collection_keys]
            hint_value = ",".join(selected_names)
            raise QueryAPIError(
                code="VECTORSTORE_EMPTY",
                status_code=400,
                message="선택된 컬렉션에 인덱스가 없습니다. 먼저 /reindex를 실행하세요.",
                hint=(
                    f"collections={hint_value} | "
                    "run_doc_rag.bat로 서버를 연 뒤 /intro 상태를 확인하고 "
                    "Reindex 또는 .venv\\Scripts\\python.exe build_index.py --reset 을 실행하세요."
                ),
            )

        active_collection_names = [collection_service.get_collection_name(key) for key in active_collection_keys]
        log_collection = ",".join(active_collection_names)
        response.headers["X-RAG-Collection"] = active_collection_names[0]
        response.headers["X-RAG-Collections"] = ",".join(active_collection_names)
        response.headers["X-RAG-Route-Reason"] = route_reason
        response.headers["X-RAG-Query-Profile"] = resolved_query_profile

        embedding_status = index_service.get_embedding_fingerprint_status(active_collection_keys)
        stage_timings["embedding_fingerprint_status"] = str(embedding_status["status"])
        if embedding_status["status"] == "mismatch":
            raise QueryAPIError(
                code="VECTORSTORE_EMBEDDING_MISMATCH",
                status_code=409,
                message="현재 임베딩 모델과 저장된 인덱스 fingerprint가 맞지 않습니다.",
                hint=(
                    "run_doc_rag.bat로 서버를 연 뒤 /intro 상태를 확인하고 "
                    "Reindex 또는 .venv\\Scripts\\python.exe build_index.py --reset 을 실행하세요. "
                    "DOC_RAG_EMBEDDING_MODEL 설정도 함께 확인하세요."
                ),
            )

        query_budget = runtime_service.plan_query_budget(
            provider=provider,
            model=model,
            timeout_seconds=query_timeout_seconds,
            collection_count=len(active_collection_keys),
            route_reason=route_reason,
        )
        response.headers["X-RAG-Budget-Profile"] = str(query_budget["profile"])
        stage_timings["budget_profile"] = str(query_budget["profile"])

        try:
            llm_started_at = time.perf_counter()
            llm = create_chat_llm(
                provider=provider,
                model=model,
                temperature=0.0,
                api_key=api_key,
                base_url=base_url,
                max_output_tokens=int(query_budget["max_output_tokens"]) if query_budget.get("max_output_tokens") else None,
            )
            stage_timings["llm_init_ms"] = round((time.perf_counter() - llm_started_at) * 1000, 3)
        except Exception as exc:
            raise QueryAPIError(
                code="LLM_CONNECTION_FAILED",
                status_code=502,
                message="LLM 연결에 실패했습니다.",
                hint=(
                    "run_doc_rag.bat로 서버를 연 뒤 /intro 상태를 확인하고 "
                    "provider/base_url/api_key 설정과 모델 실행 상태를 점검하세요."
                ),
            ) from exc

        def _context_builder(question: str) -> str:
            return query_service.build_collection_context(
                question=question,
                collection_keys=active_collection_keys,
                trace=context_trace,
                budget=query_budget,
            )

        chain_started_at = time.perf_counter()
        if "query_profile" in inspect.signature(query_service.build_query_chain).parameters:
            chain = query_service.build_query_chain(_context_builder, llm, query_profile=resolved_query_profile)
        else:
            chain = query_service.build_query_chain(_context_builder, llm)
        stage_timings["chain_build_ms"] = round((time.perf_counter() - chain_started_at) * 1000, 3)
        try:
            invoke_kwargs = {
                "chain": chain,
                "question": req.query,
                "timeout_seconds": query_timeout_seconds,
            }
            if "trace" in inspect.signature(query_service.invoke_query_chain).parameters:
                invoke_kwargs["trace"] = invoke_trace
            if "query_profile" in inspect.signature(query_service.invoke_query_chain).parameters:
                invoke_kwargs["query_profile"] = resolved_query_profile
            answer = query_service.invoke_query_chain(**invoke_kwargs)
        except TimeoutError as exc:
            raise QueryAPIError(
                code="LLM_TIMEOUT",
                status_code=504,
                message=f"LLM 응답 시간이 제한({query_timeout_seconds}초)을 초과했습니다.",
                hint="모델 상태를 확인하고 더 짧은 질문으로 다시 시도하거나 /intro 상태에서 기본 런타임 준비를 다시 확인하세요.",
            ) from exc
        except InvalidDimensionException as exc:
            raise QueryAPIError(
                code="VECTORSTORE_EMBEDDING_MISMATCH",
                status_code=409,
                message="현재 임베딩 모델과 저장된 인덱스 차원이 맞지 않습니다.",
                hint=(
                    "run_doc_rag.bat로 서버를 연 뒤 /intro 상태를 확인하고 "
                    "Reindex 또는 .venv\\Scripts\\python.exe build_index.py --reset 을 실행하세요. "
                    "DOC_RAG_EMBEDDING_MODEL 설정도 함께 확인하세요."
                ),
            ) from exc
        except Exception as exc:
            raise QueryAPIError(
                code="LLM_CONNECTION_FAILED",
                status_code=502,
                message="LLM 응답 생성 중 연결 오류가 발생했습니다.",
                hint=(
                    "run_doc_rag.bat로 서버를 연 뒤 /intro 상태를 확인하고 "
                    "provider/base_url/api_key 설정과 모델 실행 상태를 점검하세요."
                ),
            ) from exc

        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.info(
            "query request_id=%s code=OK provider=%s model=%s collection=%s route=%s elapsed_ms=%d timings=%s",
            request_id,
            log_provider,
            log_model,
            log_collection,
            route_reason,
            elapsed_ms,
            _serialize_stage_timings(
                route_reason=route_reason,
                stage_timings=stage_timings,
                context_trace=context_trace,
                invoke_trace=invoke_trace,
            ),
        )
        response_meta = None
        if req.debug:
            source_items = [
                item
                for item in context_trace.get("sources", [])
                if isinstance(item, dict)
            ]
            citations = _build_citation_labels(source_items)
            support_level, support_reason = _classify_support(
                context_trace=context_trace,
                invoke_trace=invoke_trace,
                citations=citations,
            )
            response_meta = QueryMeta(
                request_id=request_id,
                query_profile=resolved_query_profile,
                collections=active_collection_keys,
                route_reason=route_reason,
                budget_profile=str(query_budget["profile"]) if query_budget else None,
                quality_mode=req.quality_mode,
                quality_stage=quality_stage,
                support_level=support_level,
                support_reason=support_reason,
                citations=citations,
                stage_timings=stage_timings,
                context={key: value for key, value in context_trace.items() if key != "sources"},
                invoke=invoke_trace,
                sources=[
                    QuerySource(
                        source=str(item.get("source", "unknown")),
                        h2=str(item.get("h2", "")),
                        collection_key=str(item.get("collection_key", "")),
                    )
                    for item in source_items
                ],
            )
        return QueryResponse(answer=answer, provider=provider, model=model, meta=response_meta)
    except QueryAPIError as exc:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.warning(
            "query request_id=%s code=%s provider=%s model=%s collection=%s elapsed_ms=%d timings=%s",
            request_id,
            exc.code,
            log_provider,
            log_model,
            log_collection,
            elapsed_ms,
            _serialize_stage_timings(
                route_reason=route_reason,
                stage_timings=stage_timings,
                context_trace=context_trace,
                invoke_trace=invoke_trace,
            ),
        )
        raise exc
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.exception(
            "query request_id=%s code=INTERNAL_ERROR provider=%s model=%s collection=%s elapsed_ms=%d timings=%s",
            request_id,
            log_provider,
            log_model,
            log_collection,
            elapsed_ms,
            _serialize_stage_timings(
                route_reason=route_reason,
                stage_timings=stage_timings,
                context_trace=context_trace,
                invoke_trace=invoke_trace,
            ),
        )
        raise QueryAPIError(
            code="INTERNAL_ERROR",
            status_code=500,
            message="요청 처리 중 내부 오류가 발생했습니다.",
            hint="잠시 후 다시 시도하거나 서버 로그에서 request_id를 확인하세요.",
        ) from exc


@router.post("/query-feedback", response_model=QueryFeedbackResponse)
def query_feedback(
    req: QueryFeedbackRequest,
    request: Request,
    response: Response,
) -> QueryFeedbackResponse:
    from core.http import get_or_create_request_id

    request_id = get_or_create_request_id(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-RAG-Feedback"] = "accepted"
    try:
        saved = feedback_service.append_feedback(_model_dump(req))
    except OSError as exc:
        raise QueryAPIError(
            code="FEEDBACK_STORE_FAILED",
            status_code=500,
            message="질의 피드백 저장에 실패했습니다.",
            hint="서버의 chroma_db 쓰기 권한과 디스크 여유 공간을 확인하세요.",
        ) from exc
    return QueryFeedbackResponse(
        accepted=True,
        feedback_id=str(saved["id"]),
        request_id=request_id,
        storage=str(saved["storage"]),
    )
