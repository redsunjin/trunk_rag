from __future__ import annotations

import hashlib
import json
from pathlib import Path
import threading
import time

from fastapi import HTTPException
from langchain_chroma import Chroma
from langchain_core.documents import Document

from common import create_embeddings, split_by_markdown_headers
from core.collection_manifest import build_seed_document_metadata, get_seed_document_collection_key
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

EMBEDDING_FINGERPRINTS_FILE = "embedding_fingerprints.json"
VECTOR_COUNT_CACHE_TTL_SECONDS = 5.0
_EMBEDDINGS_CACHE: dict[str, object] = {}
_DB_CACHE: dict[tuple[str, str], Chroma] = {}
_COLLECTION_DOCS_CACHE: dict[tuple[str, str], list[Document]] = {}
_VECTOR_COUNT_CACHE: dict[str, tuple[float, int | None]] = {}
_CACHE_LOCK = threading.RLock()


def _get_embeddings_cached(model_name: str):
    with _CACHE_LOCK:
        cached = _EMBEDDINGS_CACHE.get(model_name)
        if cached is not None:
            return cached
        embeddings = create_embeddings(model_name)
        _EMBEDDINGS_CACHE[model_name] = embeddings
        return embeddings


def get_embeddings(model_name: str | None = None):
    resolved_model = (model_name or runtime_service.get_embedding_model()).strip()
    return _get_embeddings_cached(resolved_model)


def _db_cache_key(collection_key: str, embedding_model: str) -> tuple[str, str]:
    return collection_key, embedding_model


def _set_cached_db(collection_key: str, embedding_model: str, db: Chroma) -> None:
    with _CACHE_LOCK:
        _DB_CACHE[_db_cache_key(collection_key, embedding_model)] = db


def get_db(collection_key: str = DEFAULT_COLLECTION_KEY) -> Chroma:
    persist_path = Path(PERSIST_DIR)
    persist_path.mkdir(parents=True, exist_ok=True)
    collection_name = collection_service.get_collection_name(collection_key)
    embedding_model = runtime_service.get_embedding_model()
    cache_key = _db_cache_key(collection_key, embedding_model)
    with _CACHE_LOCK:
        cached = _DB_CACHE.get(cache_key)
    if cached is not None:
        return cached

    db = Chroma(
        collection_name=collection_name,
        embedding_function=get_embeddings(embedding_model),
        persist_directory=str(persist_path),
    )
    _set_cached_db(collection_key, embedding_model, db)
    return db


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


def _set_vector_count_snapshot(collection_name: str, vectors: int | None) -> None:
    with _CACHE_LOCK:
        _VECTOR_COUNT_CACHE[collection_name] = (time.monotonic(), vectors)


def get_vector_count_snapshot(
    collection_key: str = DEFAULT_COLLECTION_KEY,
    *,
    max_age_seconds: float = VECTOR_COUNT_CACHE_TTL_SECONDS,
) -> int | None:
    collection_name = collection_service.get_collection_name(collection_key)
    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _VECTOR_COUNT_CACHE.get(collection_name)
        if cached is not None:
            cached_at, vectors = cached
            if (now - cached_at) <= max_age_seconds:
                return vectors

    vectors = get_vector_count_fast(collection_name)
    _set_vector_count_snapshot(collection_name, vectors)
    return vectors


def _clone_documents(docs: list[Document]) -> list[Document]:
    return [
        Document(page_content=str(doc.page_content), metadata=dict(doc.metadata))
        for doc in docs
    ]


def get_collection_documents_from_store(collection_key: str = DEFAULT_COLLECTION_KEY) -> list[Document]:
    embedding_model = runtime_service.get_embedding_model()
    cache_key = _db_cache_key(collection_key, embedding_model)
    with _CACHE_LOCK:
        cached = _COLLECTION_DOCS_CACHE.get(cache_key)
    if cached is not None:
        return _clone_documents(cached)

    try:
        db = get_db(collection_key)
        payload = db._collection.get(include=["documents", "metadatas"])
    except Exception:
        return []

    if not isinstance(payload, dict):
        return []

    documents = payload.get("documents", [])
    metadatas = payload.get("metadatas", [])
    if not isinstance(documents, list):
        return []
    if not isinstance(metadatas, list):
        metadatas = []

    loaded_docs: list[Document] = []
    for index, text in enumerate(documents):
        if not isinstance(text, str) or not text.strip():
            continue
        metadata = metadatas[index] if index < len(metadatas) and isinstance(metadatas[index], dict) else {}
        loaded_docs.append(Document(page_content=text, metadata=dict(metadata)))

    with _CACHE_LOCK:
        _COLLECTION_DOCS_CACHE[cache_key] = _clone_documents(loaded_docs)
    return loaded_docs


def invalidate_runtime_state(collection_keys: list[str] | None = None) -> None:
    with _CACHE_LOCK:
        if collection_keys is None:
            _DB_CACHE.clear()
            _COLLECTION_DOCS_CACHE.clear()
            _VECTOR_COUNT_CACHE.clear()
            return

        key_set = set(collection_keys)
        collection_names = {
            collection_service.get_collection_name(key)
            for key in collection_keys
        }
        db_keys = [key for key in _DB_CACHE if key[0] in key_set]
        for key in db_keys:
            _DB_CACHE.pop(key, None)
        doc_keys = [key for key in _COLLECTION_DOCS_CACHE if key[0] in key_set]
        for key in doc_keys:
            _COLLECTION_DOCS_CACHE.pop(key, None)
        for collection_name in collection_names:
            _VECTOR_COUNT_CACHE.pop(collection_name, None)


def embedding_fingerprint_manifest_path() -> Path:
    persist_path = Path(PERSIST_DIR)
    persist_path.mkdir(parents=True, exist_ok=True)
    return persist_path / EMBEDDING_FINGERPRINTS_FILE


def _load_embedding_fingerprint_manifest_unlocked() -> dict[str, object]:
    path = embedding_fingerprint_manifest_path()
    if not path.exists():
        return {"items": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"items": {}}
    if isinstance(payload, dict) and isinstance(payload.get("items"), dict):
        return payload
    return {"items": {}}


def _save_embedding_fingerprint_manifest_unlocked(payload: dict[str, object]) -> None:
    embedding_fingerprint_manifest_path().write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def normalize_embedding_identity(model_name: str) -> str:
    value = model_name.strip()
    path = Path(value).expanduser()
    if path.exists():
        return str(path.resolve())
    return value


def build_embedding_fingerprint(model_name: str) -> str:
    normalized = normalize_embedding_identity(model_name)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def record_collection_embedding_fingerprint(
    collection_key: str,
    *,
    model_name: str | None = None,
    vector_count: int | None = None,
) -> dict[str, object]:
    resolved_model = (model_name or runtime_service.get_embedding_model()).strip()
    item = {
        "collection_key": collection_key,
        "collection_name": collection_service.get_collection_name(collection_key),
        "embedding_model": normalize_embedding_identity(resolved_model),
        "embedding_fingerprint": build_embedding_fingerprint(resolved_model),
        "updated_at": runtime_service.utc_now_iso(),
        "vector_count": vector_count,
    }
    with _CACHE_LOCK:
        payload = _load_embedding_fingerprint_manifest_unlocked()
        items = payload.setdefault("items", {})
        if not isinstance(items, dict):
            items = {}
            payload["items"] = items
        items[collection_key] = item
        _save_embedding_fingerprint_manifest_unlocked(payload)
    return item


def get_collection_embedding_record(collection_key: str) -> dict[str, object] | None:
    with _CACHE_LOCK:
        payload = _load_embedding_fingerprint_manifest_unlocked()
        items = payload.get("items", {})
        if not isinstance(items, dict):
            return None
        item = items.get(collection_key)
        if isinstance(item, dict):
            return item
        return None


def get_embedding_fingerprint_status(
    collection_keys: list[str] | None = None,
    *,
    model_name: str | None = None,
) -> dict[str, object]:
    keys = collection_keys or collection_service.list_collection_keys()
    resolved_model = (model_name or runtime_service.get_embedding_model()).strip()
    expected_fingerprint = build_embedding_fingerprint(resolved_model)
    expected_model = normalize_embedding_identity(resolved_model)

    items: list[dict[str, object]] = []
    aggregate_status = "ready"
    any_ready = False
    missing_keys: list[str] = []
    mismatch_keys: list[str] = []

    for key in keys:
        vectors = get_vector_count_snapshot(key, max_age_seconds=0.0)
        record = get_collection_embedding_record(key)
        if not vectors or vectors <= 0:
            status = "empty"
        elif record is None:
            status = "missing"
            missing_keys.append(key)
        elif str(record.get("embedding_fingerprint", "")) != expected_fingerprint:
            status = "mismatch"
            mismatch_keys.append(key)
        else:
            status = "ready"
            any_ready = True

        items.append(
            {
                "collection_key": key,
                "vectors": vectors or 0,
                "status": status,
                "stored_embedding_model": None if record is None else record.get("embedding_model"),
                "stored_embedding_fingerprint": None if record is None else record.get("embedding_fingerprint"),
            }
        )

    if mismatch_keys:
        aggregate_status = "mismatch"
    elif missing_keys:
        aggregate_status = "missing"
    elif any_ready:
        aggregate_status = "ready"
    else:
        aggregate_status = "empty"

    if aggregate_status == "mismatch":
        message = (
            "현재 임베딩 모델과 저장된 컬렉션 fingerprint가 다릅니다. "
            "Reindex 또는 build_index.py --reset이 필요합니다."
        )
    elif aggregate_status == "missing":
        message = (
            "현재 컬렉션의 embedding fingerprint 메타데이터가 없습니다. "
            "운영 게이트 전에 Reindex를 다시 실행하세요."
        )
    elif aggregate_status == "empty":
        message = "아직 fingerprint 비교 대상이 되는 벡터가 없습니다."
    else:
        message = "현재 임베딩 모델과 저장된 컬렉션 fingerprint가 일치합니다."

    return {
        "status": aggregate_status,
        "message": message,
        "expected_embedding_model": expected_model,
        "expected_embedding_fingerprint": expected_fingerprint,
        "missing_keys": missing_keys,
        "mismatch_keys": mismatch_keys,
        "items": items,
    }


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
    return get_seed_document_collection_key(file_name)


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
        metadata = build_seed_document_metadata(path.name, doc_key=stem.lower())
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
                    **metadata,
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
    embedding_model = runtime_service.get_embedding_model()
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
    embeddings = get_embeddings(embedding_model)

    if reset:
        invalidate_runtime_state([collection_key])
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
        _set_cached_db(collection_key, embedding_model, db)
    else:
        db = get_db(collection_key)
        if chunks:
            db.add_documents(chunks)

    vectors = get_vector_count(db)
    _set_vector_count_snapshot(collection_name, vectors)
    record_collection_embedding_fingerprint(
        collection_key,
        model_name=embedding_model,
        vector_count=vectors,
    )
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


def reindex(
    reset: bool = True,
    collection_key: str = DEFAULT_COLLECTION_KEY,
    *,
    include_compatibility_bundle: bool = False,
) -> dict[str, object]:
    return reindex_with_related(
        reset=reset,
        collection_key=collection_key,
        include_compatibility_bundle=include_compatibility_bundle,
    )


def expand_reindex_collection_keys(
    collection_key: str = DEFAULT_COLLECTION_KEY,
    *,
    include_compatibility_bundle: bool = False,
) -> list[str]:
    if collection_key == DEFAULT_COLLECTION_KEY:
        target_keys = collection_service.list_default_runtime_collection_keys()
        if include_compatibility_bundle:
            compatibility_keys = collection_service.list_compatibility_collection_keys()
            target_keys = collection_service.dedupe_collection_keys(target_keys + compatibility_keys)
        return target_keys
    return collection_service.dedupe_collection_keys([collection_key, DEFAULT_COLLECTION_KEY])


def reindex_single_collection(reset: bool = True, collection_key: str = DEFAULT_COLLECTION_KEY) -> dict[str, object]:
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


def reindex_with_related(
    reset: bool = True,
    collection_key: str = DEFAULT_COLLECTION_KEY,
    *,
    include_compatibility_bundle: bool = False,
) -> dict[str, object]:
    target_keys = expand_reindex_collection_keys(
        collection_key,
        include_compatibility_bundle=include_compatibility_bundle,
    )
    invalidate_runtime_state(target_keys)
    results: dict[str, dict[str, object]] = {}
    for key in target_keys:
        results[key] = reindex_single_collection(reset=reset, collection_key=key)

    primary = dict(results[collection_key])
    primary["collections"] = results
    primary["related_collection_keys"] = target_keys
    if collection_key == DEFAULT_COLLECTION_KEY:
        primary["reindex_scope"] = (
            "default_plus_compatibility_bundle" if include_compatibility_bundle else "default_runtime_only"
        )
        compatibility_bundle = collection_service.get_compatibility_bundle_config()
        primary["compatibility_bundle"] = {
            **compatibility_bundle,
            "included": include_compatibility_bundle,
        }
    else:
        primary["reindex_scope"] = "selected_plus_default"
    return primary


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
