from __future__ import annotations

import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel, Field

from common import (
    DEFAULT_FILE_NAMES,
    create_chat_llm,
    create_embeddings,
    default_data_dir,
    default_llm_model,
    default_persist_dir,
    load_markdown_documents,
    load_project_env,
    resolve_llm_config,
    split_by_markdown_headers,
)
from scripts.validate_rag_doc import validate_loaded_documents, validate_markdown_text


PERSIST_DIR = str(default_persist_dir())
DATA_DIR = str(default_data_dir())
COLLECTION_NAME = "w2_007_header_rag"
DEFAULT_COLLECTION_KEY = "all"
EMBEDDING_MODEL = "BAAI/bge-m3"
SEARCH_K = 3
SEARCH_FETCH_K = 10
SEARCH_LAMBDA = 0.3
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
QUERY_TIMEOUT_SECONDS = 15
COLLECTION_SOFT_CAP = 30_000
COLLECTION_HARD_CAP = 50_000
ADMIN_CODE_ENV_KEY = "DOC_RAG_ADMIN_CODE"
AUTO_APPROVE_ENV_KEY = "DOC_RAG_AUTO_APPROVE"
UPLOAD_REQUEST_STORE_FILE = "upload_requests.json"
REQUEST_STATUS_PENDING = "pending"
REQUEST_STATUS_APPROVED = "approved"
REQUEST_STATUS_REJECTED = "rejected"
REQUEST_STATUSES = {REQUEST_STATUS_PENDING, REQUEST_STATUS_APPROVED, REQUEST_STATUS_REJECTED}
UPLOAD_REQUEST_LOCK = threading.Lock()

COLLECTION_CONFIGS: dict[str, dict[str, object]] = {
    "all": {
        "name": COLLECTION_NAME,
        "label": "전체 (기본)",
        "file_names": DEFAULT_FILE_NAMES,
        "keywords": (),
    },
    "eu": {
        "name": "rag_science_history_eu",
        "label": "유럽 요약",
        "file_names": ["eu_summry.md"],
        "keywords": ("유럽", "europe"),
    },
    "fr": {
        "name": "rag_science_history_fr",
        "label": "프랑스",
        "file_names": ["fr.md"],
        "keywords": ("프랑스", "france", "french"),
    },
    "ge": {
        "name": "rag_science_history_ge",
        "label": "독일",
        "file_names": ["ge.md"],
        "keywords": ("독일", "germany", "german"),
    },
    "it": {
        "name": "rag_science_history_it",
        "label": "이탈리아",
        "file_names": ["it.md"],
        "keywords": ("이탈리아", "italy", "italian"),
    },
    "uk": {
        "name": "rag_science_history_uk",
        "label": "영국",
        "file_names": ["uk.md"],
        "keywords": ("영국", "britain", "united kingdom", "england"),
    },
}

COUNTRY_BY_COLLECTION_KEY = {
    "all": "all",
    "eu": "all",
    "fr": "france",
    "ge": "germany",
    "it": "italy",
    "uk": "uk",
}


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("doc_rag.api")


PROMPT = ChatPromptTemplate.from_template(
    """당신은 유럽 과학사 질의응답 어시스턴트입니다.
반드시 [Context]에 있는 정보만 사용해 한국어로 답변하세요.
근거가 부족하면 '제공된 문서에서 확인되지 않습니다.'라고 답변하세요.

[Context]
{context}

[Question]
{question}

[Answer]
1) 핵심 답변:
2) 근거:
"""
)


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    llm_provider: str = Field(default="ollama")
    llm_model: str | None = None
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    collection: str | None = None


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


class QueryAPIError(Exception):
    def __init__(self, code: str, status_code: int, message: str, hint: str | None = None):
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.message = message
        self.hint = hint


def get_admin_code() -> str:
    value = os.getenv(ADMIN_CODE_ENV_KEY, "admin1234").strip()
    return value or "admin1234"


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def parse_bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    return value in {"1", "true", "yes", "on", "y"}


def is_auto_approve_enabled() -> bool:
    return parse_bool_env(AUTO_APPROVE_ENV_KEY, default=False)


def verify_admin_code(code: str) -> None:
    if code.strip() != get_admin_code():
        raise HTTPException(status_code=401, detail="관리자 인증코드가 올바르지 않습니다.")


def sanitize_source_name(source_name: str) -> str:
    value = source_name.strip()
    if not value:
        raise ValueError("source_name is empty")
    safe = "".join(char if (char.isalnum() or char in {"_", "-", "."}) else "_" for char in value)
    if not safe.lower().endswith(".md"):
        safe = f"{safe}.md"
    return safe


def default_country_for_collection(collection_key: str) -> str:
    return COUNTRY_BY_COLLECTION_KEY.get(collection_key, "all")


def default_doc_type_for_collection(collection_key: str) -> str:
    if collection_key in {"all", "eu"}:
        return "summary"
    return "country"


def upload_request_store_path() -> Path:
    path = Path(PERSIST_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path / UPLOAD_REQUEST_STORE_FILE


def _load_upload_requests_unlocked() -> list[dict[str, object]]:
    path = upload_request_store_path()
    if not path.exists():
        return []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload["items"]
    if isinstance(payload, list):
        return payload
    return []


def _save_upload_requests_unlocked(items: list[dict[str, object]]) -> None:
    path = upload_request_store_path()
    payload = {"items": items}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def list_upload_requests(status: str | None = None) -> list[dict[str, object]]:
    with UPLOAD_REQUEST_LOCK:
        items = _load_upload_requests_unlocked()

    if status:
        value = status.strip().lower()
        items = [item for item in items if str(item.get("status", "")).lower() == value]

    return sorted(items, key=lambda item: str(item.get("created_at", "")), reverse=True)


def find_upload_request(request_id: str) -> tuple[list[dict[str, object]], dict[str, object], int]:
    items = _load_upload_requests_unlocked()
    for index, item in enumerate(items):
        if item.get("id") == request_id:
            return items, item, index
    raise HTTPException(status_code=404, detail=f"Upload request not found: {request_id}")


def ensure_pending_status(item: dict[str, object]) -> None:
    status = str(item.get("status", ""))
    if status != REQUEST_STATUS_PENDING:
        raise HTTPException(status_code=400, detail=f"Request is not pending. status={status}")


def build_upload_request_metadata(
    *,
    source_name: str,
    collection_key: str,
    country: str | None,
    doc_type: str | None,
) -> dict[str, str]:
    metadata_country = (country or "").strip() or default_country_for_collection(collection_key)
    metadata_doc_type = (doc_type or "").strip() or default_doc_type_for_collection(collection_key)
    return {
        "source": source_name,
        "country": metadata_country,
        "doc_type": metadata_doc_type,
    }


def index_documents_for_collection(
    docs,
    *,
    collection_key: str,
    reset: bool,
) -> dict[str, object]:
    collection_name = get_collection_name(collection_key)
    chunks = split_by_markdown_headers(
        docs,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    current_vectors = get_vector_count_fast(collection_name) or 0
    projected_vectors = len(chunks) if reset else current_vectors + len(chunks)
    if projected_vectors > COLLECTION_HARD_CAP:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Hard cap exceeded for selected collection.",
                "collection": collection_name,
                "collection_key": collection_key,
                "projected_vectors": projected_vectors,
                "hard_cap": COLLECTION_HARD_CAP,
                "hint": "컬렉션 분리 또는 기존 데이터 정리 후 다시 시도하세요.",
            },
        )

    persist_dir = Path(PERSIST_DIR)
    persist_dir.mkdir(parents=True, exist_ok=True)
    embeddings = get_embeddings()

    if reset:
        try:
            temp_db = Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory=str(persist_dir),
            )
            temp_db.delete_collection()
        except Exception:
            pass
        db = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            collection_name=collection_name,
            persist_directory=str(persist_dir),
            collection_metadata={"hnsw:space": "cosine"},
        )
    else:
        db = get_db(collection_key)
        if chunks:
            db.add_documents(chunks)

    vectors = get_vector_count(db)
    cap_status = calculate_cap_status(vectors)
    return {
        "chunks_added": len(chunks),
        "vectors": vectors,
        "cap": cap_status,
        "collection": collection_name,
        "collection_key": collection_key,
    }


def resolve_collection_key(collection: str | None) -> str | None:
    if collection is None:
        return None

    value = collection.strip().lower()
    if not value:
        return None

    if value in COLLECTION_CONFIGS:
        return value

    for key, config in COLLECTION_CONFIGS.items():
        if value == str(config["name"]).strip().lower():
            return key

    raise ValueError(f"Unsupported collection: {collection}")


def get_collection_config(collection_key: str) -> dict[str, object]:
    config = COLLECTION_CONFIGS.get(collection_key)
    if config is None:
        raise ValueError(f"Unsupported collection key: {collection_key}")
    return config


def guess_collection_key_from_query(query: str) -> str:
    normalized = query.strip().lower()
    for key, config in COLLECTION_CONFIGS.items():
        if key == DEFAULT_COLLECTION_KEY:
            continue
        for keyword in config.get("keywords", ()):
            if str(keyword).lower() in normalized:
                return key
    return DEFAULT_COLLECTION_KEY


def resolve_collection_for_query(query: str, requested_collection: str | None) -> tuple[str, str]:
    explicit_key = resolve_collection_key(requested_collection)
    if explicit_key:
        return explicit_key, "explicit"

    guessed_key = guess_collection_key_from_query(query)
    if guessed_key != DEFAULT_COLLECTION_KEY:
        return guessed_key, "keyword"
    return DEFAULT_COLLECTION_KEY, "default"


def list_collection_keys() -> list[str]:
    return list(COLLECTION_CONFIGS.keys())


def get_collection_name(collection_key: str) -> str:
    config = get_collection_config(collection_key)
    return str(config["name"])


def calculate_cap_status(vector_count: int) -> dict[str, int | float | bool]:
    soft_usage = (vector_count / COLLECTION_SOFT_CAP) if COLLECTION_SOFT_CAP else 0.0
    hard_usage = (vector_count / COLLECTION_HARD_CAP) if COLLECTION_HARD_CAP else 0.0
    return {
        "soft_cap": COLLECTION_SOFT_CAP,
        "hard_cap": COLLECTION_HARD_CAP,
        "soft_usage_ratio": round(soft_usage, 4),
        "hard_usage_ratio": round(hard_usage, 4),
        "soft_exceeded": vector_count >= COLLECTION_SOFT_CAP,
        "hard_exceeded": vector_count >= COLLECTION_HARD_CAP,
    }


def list_collection_statuses() -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for key in list_collection_keys():
        config = get_collection_config(key)
        collection_name = str(config["name"])
        vector_count = get_vector_count_fast(collection_name)
        vectors = vector_count if isinstance(vector_count, int) else 0
        cap_status = calculate_cap_status(vectors)
        items.append(
            {
                "key": key,
                "name": collection_name,
                "label": config["label"],
                "file_names": list(config["file_names"]),
                "vectors": vectors,
                **cap_status,
            }
        )
    return items


def collect_rejected_items(validation_reports: list[dict[str, object]]) -> list[dict[str, object]]:
    rejected: list[dict[str, object]] = []
    for report in validation_reports:
        reasons = report.get("reasons", [])
        if reasons:
            rejected.append(
                {
                    "source": report.get("source", "unknown"),
                    "reasons": reasons,
                }
            )
    return rejected


def list_target_docs() -> list[dict[str, int | str]]:
    data_dir = Path(DATA_DIR)
    docs: list[dict[str, int | str]] = []
    for name in DEFAULT_FILE_NAMES:
        path = data_dir / name
        if not path.exists():
            continue
        stat = path.stat()
        docs.append(
            {
                "name": path.name,
                "size": stat.st_size,
                "updated_at": int(stat.st_mtime),
            }
        )
    return docs


def resolve_doc_path(doc_name: str) -> Path:
    # RAG 대상 문서만 조회 허용
    if doc_name not in set(DEFAULT_FILE_NAMES):
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_name}")
    path = Path(DATA_DIR) / doc_name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_name}")
    return path


def format_docs(docs) -> str:
    lines = []
    for idx, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "unknown")
        h2 = doc.metadata.get("h2", "")
        lines.append(f"[{idx}] source={source} h2={h2}\n{doc.page_content}")
    return "\n\n".join(lines)


def get_or_create_request_id(request: Request) -> str:
    existing = getattr(request.state, "request_id", None)
    if isinstance(existing, str) and existing.strip():
        return existing.strip()

    header_value = request.headers.get("X-Request-ID", "").strip()
    request_id = header_value or str(uuid4())
    request.state.request_id = request_id
    return request_id


def build_query_error_payload(
    *,
    code: str,
    message: str,
    request_id: str,
    hint: str | None = None,
) -> dict[str, str | None]:
    return {
        "code": code,
        "message": message,
        "hint": hint,
        "request_id": request_id,
        "detail": message,
    }


def build_query_chain(retriever, llm):
    return (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | PROMPT
        | llm
        | StrOutputParser()
    )


def invoke_query_chain(chain, question: str, timeout_seconds: int = QUERY_TIMEOUT_SECONDS) -> str:
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(chain.invoke, question)
    try:
        return future.result(timeout=timeout_seconds)
    except FuturesTimeoutError as exc:
        future.cancel()
        raise TimeoutError("LLM invocation timed out.") from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def build_validation_hint(exc: RequestValidationError) -> str:
    if not exc.errors():
        return "요청 본문 형식을 확인하세요."

    first = exc.errors()[0]
    loc_items = [str(item) for item in first.get("loc", []) if str(item) != "body"]
    loc = ".".join(loc_items)
    msg = first.get("msg", "요청 본문 형식이 올바르지 않습니다.")
    if loc == "query":
        return "query는 1자 이상 입력해야 합니다."
    if loc:
        return f"{loc}: {msg}"
    return str(msg)


@lru_cache(maxsize=1)
def get_embeddings():
    return create_embeddings(EMBEDDING_MODEL)


def get_db(collection_key: str = DEFAULT_COLLECTION_KEY) -> Chroma:
    persist_path = Path(PERSIST_DIR)
    persist_path.mkdir(parents=True, exist_ok=True)
    collection_name = get_collection_name(collection_key)
    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embeddings(),
        persist_directory=str(persist_path),
    )


def get_vector_count(db: Chroma) -> int:
    try:
        return db._collection.count()
    except Exception:
        return 0


def get_vector_count_fast(collection_name: str = COLLECTION_NAME) -> int | None:
    try:
        import chromadb

        client = chromadb.PersistentClient(path=PERSIST_DIR)
        collection = client.get_collection(name=collection_name)
        return collection.count()
    except Exception:
        return None


def reindex(reset: bool = True, collection_key: str = DEFAULT_COLLECTION_KEY) -> dict[str, object]:
    config = get_collection_config(collection_key)
    file_names = list(config["file_names"])
    collection_name = str(config["name"])

    docs = load_markdown_documents(Path(DATA_DIR), file_names)
    if not docs:
        raise HTTPException(status_code=400, detail=f"No markdown files found in {DATA_DIR}")

    validation_reports = validate_loaded_documents(docs)
    usable_docs = [doc for doc, report in zip(docs, validation_reports) if report["usable"]]
    rejected_items = collect_rejected_items(validation_reports)
    warning_docs = sum(1 for report in validation_reports if report.get("warnings"))
    if not usable_docs:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "No usable markdown files after validation.",
                "validation": {
                    "total_docs": len(docs),
                    "usable_docs": 0,
                    "rejected_docs": len(rejected_items),
                    "warning_docs": warning_docs,
                    "rejected": rejected_items,
                },
            },
        )

    ingest_result = index_documents_for_collection(usable_docs, collection_key=collection_key, reset=reset)
    return {
        "docs": len(usable_docs),
        "docs_total": len(docs),
        "chunks": ingest_result["chunks_added"],
        "vectors": ingest_result["vectors"],
        "persist_dir": str(Path(PERSIST_DIR)),
        "collection": collection_name,
        "collection_key": collection_key,
        "cap": ingest_result["cap"],
        "validation": {
            "total_docs": len(docs),
            "usable_docs": len(usable_docs),
            "rejected_docs": len(rejected_items),
            "warning_docs": warning_docs,
            "rejected": rejected_items,
        },
    }


app = FastAPI(title="doc_rag local api", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.on_event("startup")
def startup() -> None:
    env_path = load_project_env()
    if env_path:
        print(f"Loaded env: {env_path}")


@app.get("/health")
def health() -> dict[str, int | str | None]:
    default_collection = get_collection_name(DEFAULT_COLLECTION_KEY)
    pending_count = len([item for item in list_upload_requests(status=REQUEST_STATUS_PENDING)])
    return {
        "status": "ok",
        "collection_key": DEFAULT_COLLECTION_KEY,
        "collection": default_collection,
        "persist_dir": PERSIST_DIR,
        "vectors": get_vector_count_fast(default_collection),
        "auto_approve": is_auto_approve_enabled(),
        "pending_requests": pending_count,
    }


@app.get("/collections")
def collections() -> dict[str, object]:
    return {
        "default_collection_key": DEFAULT_COLLECTION_KEY,
        "auto_approve": is_auto_approve_enabled(),
        "collections": list_collection_statuses(),
    }


@app.get("/upload-requests")
def upload_requests(status: str | None = None) -> dict[str, object]:
    if status:
        value = status.strip().lower()
        if value not in REQUEST_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported status. Use one of: {', '.join(sorted(REQUEST_STATUSES))}",
            )

    items = list_upload_requests(status=status)
    counts = {
        REQUEST_STATUS_PENDING: 0,
        REQUEST_STATUS_APPROVED: 0,
        REQUEST_STATUS_REJECTED: 0,
    }
    for item in list_upload_requests(status=None):
        current = str(item.get("status", "")).lower()
        if current in counts:
            counts[current] += 1

    return {
        "auto_approve": is_auto_approve_enabled(),
        "counts": counts,
        "requests": items,
    }


@app.get("/upload-requests/{request_id}")
def upload_request_detail(request_id: str) -> dict[str, object]:
    with UPLOAD_REQUEST_LOCK:
        _items, item, _index = find_upload_request(request_id)
    return {"request": item}


@app.post("/upload-requests")
def create_upload_request(req: UploadRequestCreateRequest) -> dict[str, object]:
    try:
        collection_key = resolve_collection_key(req.collection) or DEFAULT_COLLECTION_KEY
    except ValueError as exc:
        supported = ", ".join(list_collection_keys())
        raise HTTPException(status_code=400, detail=f"Unsupported collection. Use one of: {supported}") from exc

    source_seed = req.source_name or f"upload_{int(time.time())}"
    try:
        source_name = sanitize_source_name(source_seed)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="source_name is required.") from exc

    metadata = build_upload_request_metadata(
        source_name=source_name,
        collection_key=collection_key,
        country=req.country,
        doc_type=req.doc_type,
    )
    validation = validate_markdown_text(
        source=source_name,
        text=req.content,
        metadata=metadata,
    )

    now = utc_now_iso()
    request_item: dict[str, object] = {
        "id": str(uuid4()),
        "status": REQUEST_STATUS_PENDING,
        "collection_key": collection_key,
        "collection": get_collection_name(collection_key),
        "source_name": source_name,
        "content": req.content,
        "metadata": metadata,
        "validation": validation,
        "usable": bool(validation.get("usable", False)),
        "created_at": now,
        "updated_at": now,
        "approved_at": None,
        "rejected_at": None,
        "rejected_reason": None,
        "ingest": None,
    }

    auto_approve = is_auto_approve_enabled()
    if auto_approve:
        if not request_item["usable"]:
            request_item["status"] = REQUEST_STATUS_REJECTED
            request_item["rejected_at"] = now
            request_item["rejected_reason"] = "auto-approve enabled but validation failed"
        else:
            metadata_obj = request_item["metadata"]
            if not isinstance(metadata_obj, dict):
                metadata_obj = {}

            ingest_result = index_documents_for_collection(
                [
                    Document(
                        page_content=req.content,
                        metadata=metadata_obj,
                    )
                ],
                collection_key=collection_key,
                reset=False,
            )
            request_item["status"] = REQUEST_STATUS_APPROVED
            request_item["approved_at"] = now
            request_item["ingest"] = ingest_result
        request_item["updated_at"] = now

    with UPLOAD_REQUEST_LOCK:
        items = _load_upload_requests_unlocked()
        items.append(request_item)
        _save_upload_requests_unlocked(items)

    return {"auto_approve": auto_approve, "request": request_item}


@app.post("/upload-requests/{request_id}/approve")
def approve_upload_request(request_id: str, action: UploadRequestApproveAction) -> dict[str, object]:
    verify_admin_code(action.code)

    with UPLOAD_REQUEST_LOCK:
        items, item, index = find_upload_request(request_id)
        ensure_pending_status(item)

        usable = bool(item.get("usable", False))
        if not usable:
            raise HTTPException(
                status_code=400,
                detail="Validation failed request cannot be approved. Check request.validation.reasons.",
            )

        try:
            collection_key = resolve_collection_key(action.collection or str(item.get("collection_key", "")))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Unsupported collection.") from exc

        if collection_key is None:
            collection_key = DEFAULT_COLLECTION_KEY

        metadata_obj = item.get("metadata", {})
        if not isinstance(metadata_obj, dict):
            metadata_obj = {}

        ingest_result = index_documents_for_collection(
            [
                Document(
                    page_content=str(item.get("content", "")),
                    metadata=metadata_obj,
                )
            ],
            collection_key=collection_key,
            reset=False,
        )

        now = utc_now_iso()
        item["status"] = REQUEST_STATUS_APPROVED
        item["collection_key"] = collection_key
        item["collection"] = get_collection_name(collection_key)
        item["approved_at"] = now
        item["updated_at"] = now
        item["rejected_at"] = None
        item["rejected_reason"] = None
        item["ingest"] = ingest_result
        items[index] = item
        _save_upload_requests_unlocked(items)

    return {"request": item}


@app.post("/upload-requests/{request_id}/reject")
def reject_upload_request(request_id: str, action: UploadRequestRejectAction) -> dict[str, object]:
    verify_admin_code(action.code)

    with UPLOAD_REQUEST_LOCK:
        items, item, index = find_upload_request(request_id)
        ensure_pending_status(item)

        now = utc_now_iso()
        item["status"] = REQUEST_STATUS_REJECTED
        item["rejected_reason"] = action.reason.strip()
        item["rejected_at"] = now
        item["updated_at"] = now
        item["approved_at"] = None
        item["ingest"] = None
        items[index] = item
        _save_upload_requests_unlocked(items)

    return {"request": item}


@app.get("/rag-docs")
def docs() -> dict[str, list[dict[str, int | str]]]:
    return {"docs": list_target_docs()}


@app.get("/rag-docs/{doc_name}")
def read_doc(doc_name: str) -> dict[str, str]:
    path = resolve_doc_path(doc_name)
    return {
        "name": path.name,
        "content": path.read_text(encoding="utf-8"),
    }


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest, request: Request, response: Response) -> QueryResponse:
    request_id = get_or_create_request_id(request)
    response.headers["X-Request-ID"] = request_id
    started_at = time.perf_counter()
    log_provider = req.llm_provider
    log_model = req.llm_model or "-"
    log_collection = get_collection_name(DEFAULT_COLLECTION_KEY)

    try:
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
            collection_key, route_reason = resolve_collection_for_query(req.query, req.collection)
        except ValueError as exc:
            supported = ", ".join(list_collection_keys())
            raise QueryAPIError(
                code="INVALID_COLLECTION",
                status_code=400,
                message="지원하지 않는 collection입니다.",
                hint=f"지원값: {supported}",
            ) from exc

        collection_name = get_collection_name(collection_key)
        log_collection = collection_name
        response.headers["X-RAG-Collection"] = collection_name

        db = get_db(collection_key)
        vector_count = get_vector_count(db)
        if vector_count == 0 and req.collection is None and collection_key != DEFAULT_COLLECTION_KEY:
            # 자동 라우팅된 컬렉션이 비었으면 기본 컬렉션으로 1회 fallback
            fallback_key = DEFAULT_COLLECTION_KEY
            fallback_db = get_db(fallback_key)
            fallback_vector_count = get_vector_count(fallback_db)
            if fallback_vector_count > 0:
                db = fallback_db
                vector_count = fallback_vector_count
                collection_key = fallback_key
                collection_name = get_collection_name(collection_key)
                route_reason = f"{route_reason}->fallback"
                log_collection = collection_name
                response.headers["X-RAG-Collection"] = collection_name

        if vector_count == 0:
            raise QueryAPIError(
                code="VECTORSTORE_EMPTY",
                status_code=400,
                message="선택된 컬렉션에 인덱스가 없습니다. 먼저 /reindex를 실행하세요.",
                hint=f"collection={collection_name}",
            )

        retriever = db.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": SEARCH_K,
                "fetch_k": SEARCH_FETCH_K,
                "lambda_mult": SEARCH_LAMBDA,
                },
            )

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

        chain = build_query_chain(retriever, llm)
        try:
            answer = invoke_query_chain(chain=chain, question=req.query, timeout_seconds=QUERY_TIMEOUT_SECONDS)
        except TimeoutError as exc:
            raise QueryAPIError(
                code="LLM_TIMEOUT",
                status_code=504,
                message=f"LLM 응답 시간이 제한({QUERY_TIMEOUT_SECONDS}초)을 초과했습니다.",
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
        return QueryResponse(answer=answer, provider=provider, model=model)
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
        raise QueryAPIError(
            code="INTERNAL_ERROR",
            status_code=500,
            message="요청 처리 중 내부 오류가 발생했습니다.",
            hint="잠시 후 다시 시도하거나 서버 로그에서 request_id를 확인하세요.",
        ) from exc


@app.post("/reindex")
def reindex_endpoint(req: ReindexRequest) -> dict[str, object]:
    try:
        collection_key = resolve_collection_key(req.collection) or DEFAULT_COLLECTION_KEY
    except ValueError as exc:
        supported = ", ".join(list_collection_keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported collection. Use one of: {supported}",
        ) from exc
    return reindex(reset=req.reset, collection_key=collection_key)


@app.post("/admin/auth")
def admin_auth(req: AdminAuthRequest) -> dict[str, bool]:
    verify_admin_code(req.code)
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def index_page() -> HTMLResponse:
    return RedirectResponse(url="/intro")


@app.get("/intro", response_class=HTMLResponse)
def intro_page() -> HTMLResponse:
    page_path = Path(__file__).resolve().parent / "web" / "intro.html"
    if not page_path.exists():
        return HTMLResponse("<h3>web/intro.html not found.</h3>", status_code=404)
    return HTMLResponse(page_path.read_text(encoding="utf-8"))


@app.get("/app", response_class=HTMLResponse)
def app_page() -> HTMLResponse:
    page_path = Path(__file__).resolve().parent / "web" / "index.html"
    if not page_path.exists():
        return HTMLResponse("<h3>web/index.html not found.</h3>", status_code=404)
    return HTMLResponse(page_path.read_text(encoding="utf-8"))


@app.get("/admin", response_class=HTMLResponse)
def admin_page() -> HTMLResponse:
    page_path = Path(__file__).resolve().parent / "web" / "admin.html"
    if not page_path.exists():
        return HTMLResponse("<h3>web/admin.html not found.</h3>", status_code=404)
    return HTMLResponse(page_path.read_text(encoding="utf-8"))


@app.get("/styles.css")
def styles_file() -> FileResponse:
    css_path = Path(__file__).resolve().parent / "web" / "styles.css"
    if not css_path.exists():
        raise HTTPException(status_code=404, detail="styles.css not found")
    return FileResponse(css_path, media_type="text/css")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app_api:app", host="127.0.0.1", port=8000, reload=False)
