from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException
from langchain_chroma import Chroma
from langchain_core.documents import Document

from common import (
    create_embeddings,
    load_markdown_documents,
    split_by_markdown_headers,
)
from core.settings import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_HARD_CAP,
    DATA_DIR,
    DEFAULT_COLLECTION_KEY,
    DEFAULT_FILE_NAMES,
    EMBEDDING_MODEL,
    PERSIST_DIR,
)
from scripts.validate_rag_doc import validate_loaded_documents
from services import collection_service, runtime_service


@lru_cache(maxsize=1)
def get_embeddings():
    return create_embeddings(EMBEDDING_MODEL)


def get_db(collection_key: str = DEFAULT_COLLECTION_KEY) -> Chroma:
    persist_path = Path(PERSIST_DIR)
    persist_path.mkdir(parents=True, exist_ok=True)
    collection_name = collection_service.get_collection_name(collection_key)
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


def get_vector_count_fast(collection_name: str) -> int | None:
    try:
        import chromadb

        client = chromadb.PersistentClient(path=PERSIST_DIR)
        collection = client.get_collection(name=collection_name)
        return collection.count()
    except Exception:
        return None


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


def build_validation_summary(
    *,
    total_docs: int,
    usable_docs: int,
    rejected_items: list[dict[str, object]],
    warning_docs: int,
) -> dict[str, object]:
    rejected_docs = len(rejected_items)
    usable_ratio = round((usable_docs / total_docs), 4) if total_docs else 0.0
    summary_text = (
        f"total={total_docs}, usable={usable_docs}, rejected={rejected_docs}, "
        f"warnings={warning_docs}, usable_ratio={usable_ratio:.2%}"
    )
    return {
        "total_docs": total_docs,
        "usable_docs": usable_docs,
        "rejected_docs": rejected_docs,
        "warning_docs": warning_docs,
        "usable_ratio": usable_ratio,
        "summary_text": summary_text,
        "rejected": rejected_items,
    }


def index_documents_for_collection(
    docs: list[Document],
    *,
    collection_key: str,
    reset: bool,
) -> dict[str, object]:
    collection_name = collection_service.get_collection_name(collection_key)
    chunking = runtime_service.get_chunking_config()
    chunks = split_by_markdown_headers(
        docs,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        chunking_mode=chunking["mode"],
        token_encoding=chunking["token_encoding"],
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
    cap_status = collection_service.calculate_cap_status(vectors)
    return {
        "chunks_added": len(chunks),
        "vectors": vectors,
        "cap": cap_status,
        "collection": collection_name,
        "collection_key": collection_key,
        "chunking": {
            "mode": chunking["mode"],
            "token_encoding": chunking["token_encoding"],
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
        },
    }


def reindex(reset: bool = True, collection_key: str = DEFAULT_COLLECTION_KEY) -> dict[str, object]:
    config = collection_service.get_collection_config(collection_key)
    file_names = list(config["file_names"])
    collection_name = str(config["name"])

    docs = load_markdown_documents(Path(DATA_DIR), file_names)
    if not docs:
        raise HTTPException(status_code=400, detail=f"No markdown files found in {DATA_DIR}")

    validation_reports = validate_loaded_documents(docs)
    usable_docs = [doc for doc, report in zip(docs, validation_reports) if report["usable"]]
    rejected_items = collect_rejected_items(validation_reports)
    warning_docs = sum(1 for report in validation_reports if report.get("warnings"))
    validation_summary = build_validation_summary(
        total_docs=len(docs),
        usable_docs=len(usable_docs),
        rejected_items=rejected_items,
        warning_docs=warning_docs,
    )

    if not usable_docs:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "No usable markdown files after validation.",
                "validation": validation_summary,
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
        "chunking": ingest_result["chunking"],
        "validation": validation_summary,
    }


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
    if doc_name not in set(DEFAULT_FILE_NAMES):
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_name}")
    path = Path(DATA_DIR) / doc_name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_name}")
    return path
