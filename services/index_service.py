from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException
from langchain_chroma import Chroma
from langchain_core.documents import Document

from common import (
    COUNTRY_BY_STEM,
    create_embeddings,
    split_by_markdown_headers,
)
from core.settings import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_HARD_CAP,
    DATA_DIR,
    DEFAULT_COLLECTION_KEY,
    PERSIST_DIR,
)
from scripts.validate_rag_doc import validate_loaded_documents
from services import collection_service, runtime_service, upload_service


@lru_cache(maxsize=4)
def _get_embeddings_cached(model_name: str):
    return create_embeddings(model_name)


def get_embeddings(model_name: str | None = None):
    resolved_model = (model_name or runtime_service.get_embedding_model()).strip()
    return _get_embeddings_cached(resolved_model)


def get_db(collection_key: str = DEFAULT_COLLECTION_KEY) -> Chroma:
    persist_path = Path(PERSIST_DIR)
    persist_path.mkdir(parents=True, exist_ok=True)
    collection_name = collection_service.get_collection_name(collection_key)
    embedding_model = runtime_service.get_embedding_model()
    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embeddings(embedding_model),
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


def _collection_key_for_seed_file(file_name: str) -> str:
    for key in collection_service.list_collection_keys():
        if key == DEFAULT_COLLECTION_KEY:
            continue
        config = collection_service.get_collection_config(key)
        if file_name in set(config.get("file_names", [])):
            return key
    return DEFAULT_COLLECTION_KEY


def _load_seed_source_records(collection_key: str) -> list[dict[str, object]]:
    config = collection_service.get_collection_config(collection_key)
    file_names = list(config.get("file_names", []))
    data_dir = Path(DATA_DIR)
    records: list[dict[str, object]] = []

    for name in file_names:
        path = data_dir / str(name)
        if not path.exists():
            continue

        stem = path.stem
        stat = path.stat()
        records.append(
            {
                "name": path.name,
                "path": path,
                "origin": "seed",
                "doc_key": stem.lower(),
                "collection_key": _collection_key_for_seed_file(path.name),
                "size": stat.st_size,
                "updated_at": int(stat.st_mtime),
                "metadata": {
                    "source": path.name,
                    "topic": "europe_science_history",
                    "country": COUNTRY_BY_STEM.get(stem, "unknown"),
                    "doc_type": "summary" if stem == "eu_summry" else "country",
                    "doc_key": stem.lower(),
                    "origin": "seed",
                },
            }
        )

    return records


def _load_managed_source_records(collection_key: str) -> list[dict[str, object]]:
    if collection_key == DEFAULT_COLLECTION_KEY:
        items = upload_service.list_active_managed_docs(None)
    else:
        items = upload_service.list_active_managed_docs(collection_key)

    records: list[dict[str, object]] = []
    for item in items:
        path = Path(str(item.get("file_path", "")))
        if not path.exists():
            continue

        metadata = item.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        stat = path.stat()
        records.append(
            {
                "name": str(item.get("source_name", path.name)),
                "path": path,
                "origin": "managed",
                "doc_key": str(item.get("doc_key", "")).lower(),
                "collection_key": str(item.get("collection_key", "")),
                "size": stat.st_size,
                "updated_at": int(stat.st_mtime),
                "metadata": {
                    **metadata,
                    "source": str(item.get("source_name", path.name)),
                    "doc_key": str(item.get("doc_key", "")).lower(),
                    "origin": "managed",
                    "collection_key": str(item.get("collection_key", "")),
                    "request_type": str(item.get("request_type", "")),
                    "change_summary": str(item.get("change_summary", "")),
                },
            }
        )

    return records


def build_collection_source_records(collection_key: str = DEFAULT_COLLECTION_KEY) -> list[dict[str, object]]:
    merged: dict[str, dict[str, object]] = {}
    for record in _load_seed_source_records(collection_key):
        merged[str(record["doc_key"])] = record
    for record in _load_managed_source_records(collection_key):
        merged[str(record["doc_key"])] = record
    return sorted(
        merged.values(),
        key=lambda item: (str(item.get("collection_key", "")), str(item.get("doc_key", ""))),
    )


def build_collection_documents(collection_key: str = DEFAULT_COLLECTION_KEY) -> list[Document]:
    docs: list[Document] = []
    for record in build_collection_source_records(collection_key):
        path = record["path"]
        if not isinstance(path, Path):
            continue
        docs.append(
            Document(
                page_content=path.read_text(encoding="utf-8"),
                metadata=dict(record.get("metadata", {})),
            )
        )
    return docs


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
    embeddings = get_embeddings(runtime_service.get_embedding_model())

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
    collection_name = str(config["name"])

    docs = build_collection_documents(collection_key)
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
    docs: list[dict[str, int | str]] = []
    for record in build_collection_source_records(DEFAULT_COLLECTION_KEY):
        docs.append(
            {
                "name": str(record.get("name", "")),
                "size": int(record.get("size", 0)),
                "updated_at": int(record.get("updated_at", 0)),
                "origin": str(record.get("origin", "seed")),
                "doc_key": str(record.get("doc_key", "")),
                "collection_key": str(record.get("collection_key", DEFAULT_COLLECTION_KEY)),
            }
        )
    return docs


def resolve_doc_path(doc_name: str) -> Path:
    for record in build_collection_source_records(DEFAULT_COLLECTION_KEY):
        if str(record.get("name", "")) != doc_name:
            continue
        path = record.get("path")
        if isinstance(path, Path) and path.exists():
            return path
    raise HTTPException(status_code=404, detail=f"Document not found: {doc_name}")
