from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
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
def query(req: QueryRequest) -> QueryResponse:
    db = get_db()
    if get_vector_count(db) == 0:
        raise HTTPException(status_code=400, detail="Vector store is empty. Run /reindex first.")

    retriever = db.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": SEARCH_K,
            "fetch_k": SEARCH_FETCH_K,
            "lambda_mult": SEARCH_LAMBDA,
        },
    )

    provider, model, api_key, base_url = resolve_llm_config(
        provider=req.llm_provider,
        model=req.llm_model or default_llm_model(req.llm_provider),
        api_key=req.llm_api_key,
        base_url=req.llm_base_url,
    )
    llm = create_chat_llm(
        provider=provider,
        model=model,
        temperature=0.0,
        api_key=api_key,
        base_url=base_url,
    )

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | PROMPT
        | llm
        | StrOutputParser()
    )
    answer = chain.invoke(req.query)

    return QueryResponse(answer=answer, provider=provider, model=model)


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
