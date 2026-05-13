from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Request, Response
from langchain_core.documents import Document

from api.schemas import QueryRequest, QueryResponse
from core.errors import QueryAPIError
from core.settings import DEFAULT_COLLECTION_KEY, MAX_QUERY_COLLECTIONS
from services import (
    collection_service,
    index_service,
    query_failure_note_service,
    query_service,
    query_trace_service,
    runtime_service,
)
from common import create_chat_llm, default_llm_model, resolve_llm_config

router = APIRouter()
logger = logging.getLogger("doc_rag.api")


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
    trace_enabled = runtime_service.is_query_trace_enabled()
    failure_note_enabled = runtime_service.is_query_failure_note_enabled()
    trace_sources: list[dict[str, object]] = []
    citation_docs: list[Document] = []

    def emit_query_trace(*, code: str, status_code: int, elapsed_ms: int, error_message: str | None = None) -> None:
        if not trace_enabled:
            return

        query_trace_service.append_query_trace(
            {
                "timestamp": runtime_service.utc_now_iso(),
                "request_id": request_id,
                "code": code,
                "status_code": status_code,
                "elapsed_ms": elapsed_ms,
                "query": req.query,
                "provider": log_provider,
                "model": log_model,
                "route_reason": route_reason,
                "collection": log_collection,
                "requested_collection": req.collection,
                "requested_collections": req.collections or [],
                "top_sources": trace_sources,
                "error_message": error_message,
            }
        )

    def emit_query_failure_note(
        *,
        note_type: str,
        code: str,
        status_code: int,
        elapsed_ms: int,
        answer: str | None = None,
        error_message: str | None = None,
        sources: list[dict[str, object]] | None = None,
    ) -> None:
        if not failure_note_enabled:
            return

        note_sources = sources or trace_sources
        query_failure_note_service.append_failure_note(
            {
                "timestamp": runtime_service.utc_now_iso(),
                "request_id": request_id,
                "type": note_type,
                "code": code,
                "status_code": status_code,
                "elapsed_ms": elapsed_ms,
                "query": req.query,
                "answer": answer,
                "provider": log_provider,
                "model": log_model,
                "route_reason": route_reason,
                "collection": log_collection,
                "requested_collection": req.collection,
                "requested_collections": req.collections or [],
                "top_sources": note_sources,
                "error_message": error_message,
            }
        )

    try:
        query_timeout_seconds = runtime_service.get_query_timeout_seconds()
        try:
            desired_model = req.llm_model or default_llm_model(req.llm_provider)
            provider, model, api_key, base_url = resolve_llm_config(
                provider=req.llm_provider,
                model=desired_model,
                api_key=req.llm_api_key,
                base_url=req.llm_base_url,
            )
        except ValueError as exc:
            raise QueryAPIError(
                code="INVALID_PROVIDER",
                status_code=400,
                message="지원하지 않는 llm_provider입니다.",
                hint="openai, ollama, lmstudio 중 하나를 사용하세요.",
            ) from exc

        log_provider = provider
        log_model = model

        try:
            collection_keys, route_reason, allow_default_fallback = collection_service.resolve_collection_keys_for_query(
                req.query,
                req.collection,
                req.collections,
            )
        except ValueError as exc:
            supported = ", ".join(collection_service.list_collection_keys())
            raise QueryAPIError(
                code="INVALID_COLLECTION",
                status_code=400,
                message="지원하지 않는 collection입니다.",
                hint=f"지원값: {supported}, 최대 {MAX_QUERY_COLLECTIONS}개 선택 가능",
            ) from exc

        active_collection_keys: list[str] = []
        for key in collection_keys:
            db = index_service.get_db(key)
            if index_service.get_vector_count(db) > 0:
                active_collection_keys.append(key)

        if (
            not active_collection_keys
            and allow_default_fallback
            and DEFAULT_COLLECTION_KEY not in collection_keys
        ):
            fallback_db = index_service.get_db(DEFAULT_COLLECTION_KEY)
            fallback_vector_count = index_service.get_vector_count(fallback_db)
            if fallback_vector_count > 0:
                active_collection_keys = [DEFAULT_COLLECTION_KEY]
                route_reason = f"{route_reason}->fallback"

        if not active_collection_keys:
            selected_names = [collection_service.get_collection_name(key) for key in collection_keys]
            hint_value = ",".join(selected_names)
            raise QueryAPIError(
                code="VECTORSTORE_EMPTY",
                status_code=400,
                message="선택된 컬렉션에 인덱스가 없습니다. 먼저 /reindex를 실행하세요.",
                hint=f"collections={hint_value}",
            )

        active_collection_names = [collection_service.get_collection_name(key) for key in active_collection_keys]
        log_collection = ",".join(active_collection_names)
        response.headers["X-RAG-Collection"] = active_collection_names[0]
        response.headers["X-RAG-Collections"] = ",".join(active_collection_names)

        try:
            llm = create_chat_llm(
                provider=provider,
                model=model,
                temperature=0.0,
                api_key=api_key,
                base_url=base_url,
            )
        except Exception as exc:
            raise QueryAPIError(
                code="LLM_CONNECTION_FAILED",
                status_code=502,
                message="LLM 연결에 실패했습니다.",
                hint="provider/base_url/api_key 설정과 모델 실행 상태를 확인하세요.",
            ) from exc

        def _context_builder(question: str) -> str:
            def _capture_docs(docs):
                nonlocal trace_sources, citation_docs
                citation_docs = list(docs)
                if trace_enabled:
                    trace_sources = query_trace_service.summarize_docs_for_trace(docs)

            return query_service.build_collection_context(
                question=question,
                collection_keys=active_collection_keys,
                on_docs=_capture_docs,
            )

        chain = query_service.build_query_chain(_context_builder, llm)
        try:
            answer = query_service.invoke_query_chain(
                chain=chain,
                question=req.query,
                timeout_seconds=query_timeout_seconds,
            )
        except TimeoutError as exc:
            raise QueryAPIError(
                code="LLM_TIMEOUT",
                status_code=504,
                message=f"LLM 응답 시간이 제한({query_timeout_seconds}초)을 초과했습니다.",
                hint="모델 상태를 확인하거나 더 짧은 질문으로 다시 시도하세요.",
            ) from exc
        except Exception as exc:
            raise QueryAPIError(
                code="LLM_CONNECTION_FAILED",
                status_code=502,
                message="LLM 응답 생성 중 연결 오류가 발생했습니다.",
                hint="provider/base_url/api_key 설정과 모델 실행 상태를 확인하세요.",
            ) from exc

        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.info(
            "query request_id=%s code=OK provider=%s model=%s collection=%s route=%s elapsed_ms=%d",
            request_id,
            log_provider,
            log_model,
            log_collection,
            route_reason,
            elapsed_ms,
        )
        emit_query_trace(code="OK", status_code=200, elapsed_ms=elapsed_ms)
        sources = query_service.build_citation_sources(citation_docs)
        if query_service.is_insufficient_answer(answer):
            emit_query_failure_note(
                note_type="insufficient",
                code="INSUFFICIENT_CONTEXT",
                status_code=200,
                elapsed_ms=elapsed_ms,
                answer=answer,
                sources=sources,
            )
        return QueryResponse(answer=answer, provider=provider, model=model, sources=sources)
    except QueryAPIError as exc:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.warning(
            "query request_id=%s code=%s provider=%s model=%s collection=%s elapsed_ms=%d",
            request_id,
            exc.code,
            log_provider,
            log_model,
            log_collection,
            elapsed_ms,
        )
        emit_query_trace(
            code=exc.code,
            status_code=exc.status_code,
            elapsed_ms=elapsed_ms,
            error_message=exc.message,
        )
        emit_query_failure_note(
            note_type="error",
            code=exc.code,
            status_code=exc.status_code,
            elapsed_ms=elapsed_ms,
            error_message=exc.message,
        )
        raise exc
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.exception(
            "query request_id=%s code=INTERNAL_ERROR provider=%s model=%s collection=%s elapsed_ms=%d",
            request_id,
            log_provider,
            log_model,
            log_collection,
            elapsed_ms,
        )
        emit_query_trace(
            code="INTERNAL_ERROR",
            status_code=500,
            elapsed_ms=elapsed_ms,
            error_message=str(exc),
        )
        emit_query_failure_note(
            note_type="error",
            code="INTERNAL_ERROR",
            status_code=500,
            elapsed_ms=elapsed_ms,
            error_message=str(exc),
        )
        raise QueryAPIError(
            code="INTERNAL_ERROR",
            status_code=500,
            message="요청 처리 중 내부 오류가 발생했습니다.",
            hint="잠시 후 다시 시도하거나 서버 로그에서 request_id를 확인하세요.",
        ) from exc
