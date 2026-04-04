from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from common import DEFAULT_FILE_NAMES, default_data_dir, default_persist_dir, project_root

PERSIST_DIR = str(default_persist_dir())
DATA_DIR = str(default_data_dir())
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_MODEL_ENV_KEY = "DOC_RAG_EMBEDDING_MODEL"
EMBEDDING_MODEL = DEFAULT_EMBEDDING_MODEL
SEARCH_K = 3
SEARCH_FETCH_K = 10
SEARCH_LAMBDA = 0.3
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
MAX_QUERY_COLLECTIONS = 2
DEFAULT_QUERY_TIMEOUT_SECONDS = 30
DEFAULT_MAX_CONTEXT_CHARS = 1500
COLLECTION_SOFT_CAP = 30_000
COLLECTION_HARD_CAP = 50_000
ADMIN_CODE_ENV_KEY = "DOC_RAG_ADMIN_CODE"
AUTO_APPROVE_ENV_KEY = "DOC_RAG_AUTO_APPROVE"
CHUNKING_MODE_ENV_KEY = "DOC_RAG_CHUNKING_MODE"
CHUNK_TOKEN_ENCODING_ENV_KEY = "DOC_RAG_CHUNK_TOKEN_ENCODING"
QUERY_TIMEOUT_SECONDS_ENV_KEY = "DOC_RAG_QUERY_TIMEOUT_SECONDS"
MAX_CONTEXT_CHARS_ENV_KEY = "DOC_RAG_MAX_CONTEXT_CHARS"
UPLOAD_REQUEST_STORE_FILE = "upload_requests.json"
REQUEST_STATUS_PENDING = "pending"
REQUEST_STATUS_APPROVED = "approved"
REQUEST_STATUS_REJECTED = "rejected"
REQUEST_STATUSES = {REQUEST_STATUS_PENDING, REQUEST_STATUS_APPROVED, REQUEST_STATUS_REJECTED}
UPLOAD_REQUEST_LOCK = threading.RLock()

COLLECTION_MANIFEST_PATH = project_root() / "config" / "collection_manifest.json"

_FALLBACK_COLLECTION_MANIFEST: dict[str, Any] = {
    "default_collection_key": "all",
    "collections": {
        "all": {
            "name": "w2_007_header_rag",
            "label": "전체 (기본)",
            "file_names": DEFAULT_FILE_NAMES,
            "keywords": [],
            "default_country": "all",
            "default_doc_type": "summary",
        },
        "eu": {
            "name": "rag_science_history_eu",
            "label": "유럽 요약",
            "file_names": ["eu_summry.md"],
            "keywords": ["유럽", "europe"],
            "default_country": "all",
            "default_doc_type": "summary",
        },
        "fr": {
            "name": "rag_science_history_fr",
            "label": "프랑스",
            "file_names": ["fr.md"],
            "keywords": ["프랑스", "france", "french"],
            "default_country": "france",
            "default_doc_type": "country",
        },
        "ge": {
            "name": "rag_science_history_ge",
            "label": "독일",
            "file_names": ["ge.md"],
            "keywords": ["독일", "germany", "german"],
            "default_country": "germany",
            "default_doc_type": "country",
        },
        "it": {
            "name": "rag_science_history_it",
            "label": "이탈리아",
            "file_names": ["it.md"],
            "keywords": ["이탈리아", "italy", "italian"],
            "default_country": "italy",
            "default_doc_type": "country",
        },
        "uk": {
            "name": "rag_science_history_uk",
            "label": "영국",
            "file_names": ["uk.md"],
            "keywords": ["영국", "britain", "united kingdom", "england"],
            "default_country": "uk",
            "default_doc_type": "country",
        },
    },
}


def _normalize_collection_manifest(payload: dict[str, Any]) -> tuple[str, dict[str, dict[str, object]]]:
    default_collection_key = str(payload.get("default_collection_key") or "").strip() or "all"
    raw_collections = payload.get("collections")
    if not isinstance(raw_collections, dict) or not raw_collections:
        raise ValueError("collection manifest requires a non-empty collections mapping")

    normalized: dict[str, dict[str, object]] = {}
    for key, raw_item in raw_collections.items():
        collection_key = str(key).strip().lower()
        if not collection_key:
            raise ValueError("collection manifest contains an empty key")
        if not isinstance(raw_item, dict):
            raise ValueError(f"collection manifest entry must be an object: {collection_key}")

        name = str(raw_item.get("name") or "").strip()
        label = str(raw_item.get("label") or "").strip()
        if not name or not label:
            raise ValueError(f"collection manifest entry requires name/label: {collection_key}")

        file_names = [
            str(item).strip()
            for item in raw_item.get("file_names", [])
            if str(item).strip()
        ]
        keywords = [
            str(item).strip()
            for item in raw_item.get("keywords", [])
            if str(item).strip()
        ]
        normalized[collection_key] = {
            "name": name,
            "label": label,
            "file_names": file_names,
            "keywords": keywords,
            "default_country": str(raw_item.get("default_country") or "all").strip() or "all",
            "default_doc_type": str(raw_item.get("default_doc_type") or "summary").strip() or "summary",
        }

    if default_collection_key not in normalized:
        raise ValueError(f"default collection key is missing from manifest: {default_collection_key}")
    return default_collection_key, normalized


def _load_collection_manifest(path: Path) -> tuple[str, dict[str, dict[str, object]]]:
    if not path.exists():
        return _normalize_collection_manifest(_FALLBACK_COLLECTION_MANIFEST)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("collection manifest root must be an object")
    return _normalize_collection_manifest(payload)


DEFAULT_COLLECTION_KEY, COLLECTION_CONFIGS = _load_collection_manifest(COLLECTION_MANIFEST_PATH)
COLLECTION_NAME = str(COLLECTION_CONFIGS[DEFAULT_COLLECTION_KEY]["name"])
COUNTRY_BY_COLLECTION_KEY = {
    key: str(config.get("default_country", "all"))
    for key, config in COLLECTION_CONFIGS.items()
}
