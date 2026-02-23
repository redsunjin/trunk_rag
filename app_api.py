from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from langchain_chroma import Chroma
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


PERSIST_DIR = str(default_persist_dir())
DATA_DIR = str(default_data_dir())
COLLECTION_NAME = "w2_007_header_rag"
EMBEDDING_MODEL = "BAAI/bge-m3"
SEARCH_K = 3
SEARCH_FETCH_K = 10
SEARCH_LAMBDA = 0.3
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
QUERY_TIMEOUT_SECONDS = 15


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


class QueryResponse(BaseModel):
    answer: str
    provider: str
    model: str


class ReindexRequest(BaseModel):
    reset: bool = True


class QueryAPIError(Exception):
    def __init__(self, code: str, status_code: int, message: str, hint: str | None = None):
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.message = message
        self.hint = hint


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


def get_db() -> Chroma:
    persist_path = Path(PERSIST_DIR)
    persist_path.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=str(persist_path),
    )


def get_vector_count(db: Chroma) -> int:
    try:
        return db._collection.count()
    except Exception:
        return 0


def get_vector_count_fast() -> int | None:
    try:
        import chromadb

        client = chromadb.PersistentClient(path=PERSIST_DIR)
        collection = client.get_collection(name=COLLECTION_NAME)
        return collection.count()
    except Exception:
        return None


def reindex(reset: bool = True) -> dict[str, int | str]:
    docs = load_markdown_documents(Path(DATA_DIR), DEFAULT_FILE_NAMES)
    if not docs:
        raise HTTPException(status_code=400, detail=f"No markdown files found in {DATA_DIR}")

    chunks = split_by_markdown_headers(
        docs,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    persist_dir = Path(PERSIST_DIR)
    persist_dir.mkdir(parents=True, exist_ok=True)
    embeddings = get_embeddings()

    if reset:
        try:
            temp_db = Chroma(
                collection_name=COLLECTION_NAME,
                embedding_function=embeddings,
                persist_directory=str(persist_dir),
            )
            temp_db.delete_collection()
        except Exception:
            pass

    db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(persist_dir),
        collection_metadata={"hnsw:space": "cosine"},
    )

    return {
        "docs": len(docs),
        "chunks": len(chunks),
        "vectors": get_vector_count(db),
        "persist_dir": str(persist_dir),
        "collection": COLLECTION_NAME,
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
    return {
        "status": "ok",
        "collection": COLLECTION_NAME,
        "persist_dir": PERSIST_DIR,
        "vectors": get_vector_count_fast(),
    }


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

        db = get_db()
        if get_vector_count(db) == 0:
            raise QueryAPIError(
                code="VECTORSTORE_EMPTY",
                status_code=400,
                message="Vector store is empty. Run /reindex first.",
                hint="POST /reindex를 먼저 호출해 인덱스를 생성하세요.",
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
            "query request_id=%s code=OK provider=%s model=%s elapsed_ms=%d",
            request_id,
            log_provider,
            log_model,
            elapsed_ms,
        )
        return QueryResponse(answer=answer, provider=provider, model=model)
    except QueryAPIError as exc:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.warning(
            "query request_id=%s code=%s provider=%s model=%s elapsed_ms=%d",
            request_id,
            exc.code,
            log_provider,
            log_model,
            elapsed_ms,
        )
        raise exc
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.exception(
            "query request_id=%s code=INTERNAL_ERROR provider=%s model=%s elapsed_ms=%d",
            request_id,
            log_provider,
            log_model,
            elapsed_ms,
        )
        raise QueryAPIError(
            code="INTERNAL_ERROR",
            status_code=500,
            message="요청 처리 중 내부 오류가 발생했습니다.",
            hint="잠시 후 다시 시도하거나 서버 로그에서 request_id를 확인하세요.",
        ) from exc


@app.post("/reindex")
def reindex_endpoint(req: ReindexRequest) -> dict[str, int | str]:
    return reindex(reset=req.reset)


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


@app.get("/styles.css")
def styles_file() -> FileResponse:
    css_path = Path(__file__).resolve().parent / "web" / "styles.css"
    if not css_path.exists():
        raise HTTPException(status_code=404, detail="styles.css not found")
    return FileResponse(css_path, media_type="text/css")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app_api:app", host="127.0.0.1", port=8000, reload=False)
