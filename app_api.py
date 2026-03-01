from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes_docs_ui import router as docs_ui_router
from api.routes_query import router as query_router
from api.routes_system import router as system_router
from api.routes_upload import router as upload_router
from common import create_chat_llm, default_llm_model, load_project_env, resolve_llm_config
from core.errors import QueryAPIError, build_query_error_payload, build_validation_hint
from core.http import get_or_create_request_id
from core.settings import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_CONFIGS,
    COLLECTION_HARD_CAP,
    COLLECTION_NAME,
    COLLECTION_SOFT_CAP,
    DATA_DIR,
    DEFAULT_COLLECTION_KEY,
    DEFAULT_QUERY_TIMEOUT_SECONDS,
    EMBEDDING_MODEL,
    MAX_QUERY_COLLECTIONS,
    PERSIST_DIR,
    REQUEST_STATUS_APPROVED,
    REQUEST_STATUS_PENDING,
    REQUEST_STATUS_REJECTED,
    REQUEST_STATUSES,
    SEARCH_FETCH_K,
    SEARCH_K,
    SEARCH_LAMBDA,
)
from services import collection_service, index_service, query_service, runtime_service, upload_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("doc_rag.api")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    env_path = load_project_env()
    if env_path:
        print(f"Loaded env: {env_path}")
    yield


app = FastAPI(title="doc_rag local api", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(query_router)
app.include_router(system_router)
app.include_router(upload_router)
app.include_router(docs_ui_router)


@app.exception_handler(QueryAPIError)
def query_api_error_handler(request: Request, exc: QueryAPIError) -> JSONResponse:
    request_id = get_or_create_request_id(request)
    payload = build_query_error_payload(
        code=exc.code,
        message=exc.message,
        hint=exc.hint,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=payload,
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(RequestValidationError)
async def query_validation_exception_handler(request: Request, exc: RequestValidationError):
    if request.url.path != "/query":
        return await request_validation_exception_handler(request, exc)

    request_id = get_or_create_request_id(request)
    payload = build_query_error_payload(
        code="INVALID_REQUEST",
        message="잘못된 요청 파라미터입니다.",
        hint=build_validation_hint(exc),
        request_id=request_id,
    )
    logger.warning(
        "query request_id=%s code=INVALID_REQUEST provider=- model=- elapsed_ms=0",
        request_id,
    )
    return JSONResponse(
        status_code=422,
        content=payload,
        headers={"X-Request-ID": request_id},
    )


# Backward-compatible re-exports used by scripts/tests.
get_admin_code = runtime_service.get_admin_code
utc_now_iso = runtime_service.utc_now_iso
parse_bool_env = runtime_service.parse_bool_env
is_auto_approve_enabled = runtime_service.is_auto_approve_enabled
get_query_timeout_seconds = runtime_service.get_query_timeout_seconds
get_max_context_chars = runtime_service.get_max_context_chars
get_chunking_config = runtime_service.get_chunking_config
verify_admin_code = runtime_service.verify_admin_code
sanitize_source_name = runtime_service.sanitize_source_name

default_country_for_collection = collection_service.default_country_for_collection
default_doc_type_for_collection = collection_service.default_doc_type_for_collection
resolve_collection_key = collection_service.resolve_collection_key
get_collection_config = collection_service.get_collection_config
guess_collection_key_from_query = collection_service.guess_collection_key_from_query
resolve_collection_for_query = collection_service.resolve_collection_for_query
dedupe_collection_keys = collection_service.dedupe_collection_keys
resolve_collection_keys_for_query = collection_service.resolve_collection_keys_for_query
list_collection_keys = collection_service.list_collection_keys
get_collection_name = collection_service.get_collection_name
calculate_cap_status = collection_service.calculate_cap_status
list_collection_statuses = collection_service.list_collection_statuses

upload_request_store_path = upload_service.upload_request_store_path
list_upload_requests = upload_service.list_upload_requests
find_upload_request = upload_service.find_upload_request
ensure_pending_status = upload_service.ensure_pending_status
build_upload_request_metadata = upload_service.build_upload_request_metadata

get_embeddings = index_service.get_embeddings
get_db = index_service.get_db
get_vector_count = index_service.get_vector_count
get_vector_count_fast = index_service.get_vector_count_fast
index_documents_for_collection = index_service.index_documents_for_collection
collect_rejected_items = index_service.collect_rejected_items
build_validation_summary = index_service.build_validation_summary
list_target_docs = index_service.list_target_docs
resolve_doc_path = index_service.resolve_doc_path
reindex = index_service.reindex

format_docs = query_service.format_docs
build_collection_context = query_service.build_collection_context
build_query_chain = query_service.build_query_chain
invoke_query_chain = query_service.invoke_query_chain


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app_api:app", host="127.0.0.1", port=8000, reload=False)
