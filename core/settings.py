from __future__ import annotations

import threading

from common import DEFAULT_FILE_NAMES, default_data_dir, default_persist_dir

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
MAX_QUERY_COLLECTIONS = 2
DEFAULT_QUERY_TIMEOUT_SECONDS = 15
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
