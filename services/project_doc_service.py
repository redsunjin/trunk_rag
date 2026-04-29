from __future__ import annotations

import json
from pathlib import Path

PROJECT_DOC_COLLECTION_KEY = "project_docs"
PROJECT_DOC_MANIFEST_FILE = "config/project_doc_manifest.json"
PROJECT_DOC_MANIFEST_VERSION = "project_doc_manifest.v1"


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def project_doc_manifest_path() -> Path:
    return project_root() / PROJECT_DOC_MANIFEST_FILE


def _normalize_tags(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in items:
            items.append(text)
    return items


def _normalize_metadata(raw: object) -> dict[str, object]:
    if not isinstance(raw, dict):
        raw = {}

    metadata: dict[str, object] = {}
    for key, value in raw.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            continue
        if normalized_key == "tags":
            metadata["tags"] = _normalize_tags(value)
            continue
        text = str(value).strip()
        if text:
            metadata[normalized_key] = text

    metadata.setdefault("source_type", "project_operator_doc")
    metadata.setdefault("doc_type", "operator_guide")
    metadata.setdefault("country", "all")
    metadata.setdefault("tags", [])
    return metadata


def _resolve_project_doc_path(value: object) -> Path:
    relative = Path(str(value or "").strip())
    if not str(relative):
        raise ValueError("project doc requires path")
    if relative.is_absolute():
        raise ValueError("project doc path must be relative to the project root")

    root = project_root().resolve()
    resolved = (root / relative).resolve()
    if root not in resolved.parents and resolved != root:
        raise ValueError(f"project doc path escapes project root: {relative}")
    return resolved


def load_project_doc_manifest(path: str | Path | None = None) -> dict[str, object]:
    manifest_path = Path(path) if path is not None else project_doc_manifest_path()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("project doc manifest must be an object")

    version = str(payload.get("version") or PROJECT_DOC_MANIFEST_VERSION).strip()
    collection_key = str(payload.get("collection_key") or PROJECT_DOC_COLLECTION_KEY).strip().lower()
    if collection_key != PROJECT_DOC_COLLECTION_KEY:
        raise ValueError(f"project doc manifest must target {PROJECT_DOC_COLLECTION_KEY}")

    documents: list[dict[str, object]] = []
    raw_documents = payload.get("documents")
    if not isinstance(raw_documents, list):
        raw_documents = []

    seen_doc_keys: set[str] = set()
    for raw_doc in raw_documents:
        if not isinstance(raw_doc, dict):
            continue
        doc_key = str(raw_doc.get("doc_key") or "").strip().lower()
        if not doc_key:
            raise ValueError("project doc requires doc_key")
        if doc_key in seen_doc_keys:
            raise ValueError(f"duplicate project doc_key: {doc_key}")
        seen_doc_keys.add(doc_key)

        path_value = _resolve_project_doc_path(raw_doc.get("path"))
        source_name = str(raw_doc.get("source_name") or path_value.name).strip() or path_value.name
        documents.append(
            {
                "doc_key": doc_key,
                "path": path_value,
                "source_name": source_name,
                "metadata": _normalize_metadata(raw_doc.get("metadata")),
            }
        )

    return {
        "version": version,
        "collection_key": collection_key,
        "documents": documents,
    }


def list_project_doc_source_records(collection_key: str = PROJECT_DOC_COLLECTION_KEY) -> list[dict[str, object]]:
    if collection_key != PROJECT_DOC_COLLECTION_KEY:
        return []

    manifest = load_project_doc_manifest()
    records: list[dict[str, object]] = []
    for item in manifest["documents"]:
        path = Path(str(item["path"]))
        if not path.exists():
            continue
        stat = path.stat()
        metadata = item.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        doc_key = str(item["doc_key"])
        source_name = str(item["source_name"])
        records.append(
            {
                "name": source_name,
                "path": path,
                "origin": "project_doc",
                "doc_key": doc_key,
                "collection_key": PROJECT_DOC_COLLECTION_KEY,
                "size": stat.st_size,
                "updated_at": int(stat.st_mtime),
                "metadata": {
                    **metadata,
                    "source": source_name,
                    "doc_key": doc_key,
                    "origin": "project_doc",
                    "collection_key": PROJECT_DOC_COLLECTION_KEY,
                },
            }
        )
    return records
