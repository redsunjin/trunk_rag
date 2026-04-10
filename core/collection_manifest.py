from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


COLLECTION_MANIFEST_PATH = project_root() / "config" / "collection_manifest.json"

_FALLBACK_COLLECTION_MANIFEST: dict[str, Any] = {
    "default_collection_key": "all",
    "default_runtime_collection_keys": ["all"],
    "compatibility_bundle": {
        "key": "sample_pack",
        "label": "sample-pack 호환 번들",
        "collection_keys": ["eu", "fr", "ge", "it", "uk"],
        "optional": True,
    },
    "seed_corpus": {
        "key": "sample_pack_bootstrap",
        "label": "sample-pack demo/bootstrap corpus",
        "role": "demo_bootstrap",
        "dataset": "sample-eu-science-history",
        "description": (
            "First-run demo corpus used to populate the core all collection and the optional "
            "sample-pack compatibility collections. It is bundled example data, not product-domain data."
        ),
    },
    "seed_documents": {
        "eu_summry": {
            "file_name": "eu_summry.md",
            "route_collection_key": "eu",
            "metadata": {
                "dataset": "sample-eu-science-history",
                "source_type": "seed_markdown",
                "country": "all",
                "doc_type": "summary",
                "tags": ["sample-pack", "summary"],
            },
        },
        "fr": {
            "file_name": "fr.md",
            "route_collection_key": "fr",
            "metadata": {
                "dataset": "sample-eu-science-history",
                "source_type": "seed_markdown",
                "country": "france",
                "doc_type": "country",
                "tags": ["sample-pack", "country:france"],
            },
        },
        "ge": {
            "file_name": "ge.md",
            "route_collection_key": "ge",
            "metadata": {
                "dataset": "sample-eu-science-history",
                "source_type": "seed_markdown",
                "country": "germany",
                "doc_type": "country",
                "tags": ["sample-pack", "country:germany"],
            },
        },
        "it": {
            "file_name": "it.md",
            "route_collection_key": "it",
            "metadata": {
                "dataset": "sample-eu-science-history",
                "source_type": "seed_markdown",
                "country": "italy",
                "doc_type": "country",
                "tags": ["sample-pack", "country:italy"],
            },
        },
        "uk": {
            "file_name": "uk.md",
            "route_collection_key": "uk",
            "metadata": {
                "dataset": "sample-eu-science-history",
                "source_type": "seed_markdown",
                "country": "uk",
                "doc_type": "country",
                "tags": ["sample-pack", "country:uk"],
            },
        },
    },
    "collections": {
        "all": {
            "name": "w2_007_header_rag",
            "label": "전체 (기본)",
            "seed_doc_keys": ["eu_summry", "fr", "ge", "it", "uk"],
            "keywords": [],
            "default_country": "all",
            "default_doc_type": "summary",
        },
        "eu": {
            "name": "rag_science_history_eu",
            "label": "유럽 요약",
            "seed_doc_keys": ["eu_summry"],
            "keywords": ["유럽", "europe"],
            "default_country": "all",
            "default_doc_type": "summary",
        },
        "fr": {
            "name": "rag_science_history_fr",
            "label": "프랑스",
            "seed_doc_keys": ["fr"],
            "keywords": ["프랑스", "france", "french"],
            "default_country": "france",
            "default_doc_type": "country",
        },
        "ge": {
            "name": "rag_science_history_ge",
            "label": "독일",
            "seed_doc_keys": ["ge"],
            "keywords": ["독일", "germany", "german"],
            "default_country": "germany",
            "default_doc_type": "country",
        },
        "it": {
            "name": "rag_science_history_it",
            "label": "이탈리아",
            "seed_doc_keys": ["it"],
            "keywords": ["이탈리아", "italy", "italian"],
            "default_country": "italy",
            "default_doc_type": "country",
        },
        "uk": {
            "name": "rag_science_history_uk",
            "label": "영국",
            "seed_doc_keys": ["uk"],
            "keywords": ["영국", "britain", "united kingdom", "england"],
            "default_country": "uk",
            "default_doc_type": "country",
        },
    },
}


def _normalize_string_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    items: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in items:
            items.append(text)
    return items


def _normalize_metadata(raw_metadata: object) -> dict[str, object]:
    if not isinstance(raw_metadata, dict):
        raw_metadata = {}

    metadata: dict[str, object] = {}
    for key, value in raw_metadata.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            continue
        if isinstance(value, list):
            metadata[normalized_key] = _normalize_string_list(value)
            continue
        text = str(value).strip()
        if text:
            metadata[normalized_key] = text

    tags = metadata.get("tags")
    metadata["tags"] = list(tags) if isinstance(tags, list) else []
    metadata.setdefault("source_type", "seed_markdown")
    return metadata


def _normalize_seed_documents(
    raw_documents: object,
    *,
    default_collection_key: str,
) -> dict[str, dict[str, object]]:
    if not isinstance(raw_documents, dict) or not raw_documents:
        raise ValueError("collection manifest requires a non-empty seed_documents mapping")

    normalized: dict[str, dict[str, object]] = {}
    for raw_key, raw_item in raw_documents.items():
        doc_key = str(raw_key).strip().lower()
        if not doc_key:
            raise ValueError("collection manifest contains an empty seed document key")
        if not isinstance(raw_item, dict):
            raise ValueError(f"seed document entry must be an object: {doc_key}")

        file_name = str(raw_item.get("file_name") or raw_item.get("name") or "").strip()
        if not file_name:
            raise ValueError(f"seed document entry requires file_name: {doc_key}")

        route_collection_key = (
            str(raw_item.get("route_collection_key") or raw_item.get("collection_key") or default_collection_key)
            .strip()
            .lower()
            or default_collection_key
        )
        normalized[doc_key] = {
            "doc_key": doc_key,
            "file_name": file_name,
            "route_collection_key": route_collection_key,
            "metadata": _normalize_metadata(raw_item.get("metadata")),
        }
    return normalized


def _normalize_collections(
    raw_collections: object,
    *,
    default_collection_key: str,
    seed_documents: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    if not isinstance(raw_collections, dict) or not raw_collections:
        raise ValueError("collection manifest requires a non-empty collections mapping")

    file_name_to_doc_key = {
        str(item["file_name"]).lower(): key
        for key, item in seed_documents.items()
    }
    normalized: dict[str, dict[str, object]] = {}

    for raw_key, raw_item in raw_collections.items():
        collection_key = str(raw_key).strip().lower()
        if not collection_key:
            raise ValueError("collection manifest contains an empty key")
        if not isinstance(raw_item, dict):
            raise ValueError(f"collection manifest entry must be an object: {collection_key}")

        name = str(raw_item.get("name") or "").strip()
        label = str(raw_item.get("label") or "").strip()
        if not name or not label:
            raise ValueError(f"collection manifest entry requires name/label: {collection_key}")

        seed_doc_keys: list[str] = []
        file_names: list[str] = []
        for doc_key in _normalize_string_list(raw_item.get("seed_doc_keys")):
            normalized_doc_key = doc_key.lower()
            seed_document = seed_documents.get(normalized_doc_key)
            if seed_document is None:
                raise ValueError(f"collection references unknown seed_doc_key `{doc_key}`: {collection_key}")
            if normalized_doc_key not in seed_doc_keys:
                seed_doc_keys.append(normalized_doc_key)
            file_name = str(seed_document["file_name"])
            if file_name not in file_names:
                file_names.append(file_name)

        for file_name in _normalize_string_list(raw_item.get("file_names")):
            if file_name not in file_names:
                file_names.append(file_name)
            mapped_doc_key = file_name_to_doc_key.get(file_name.lower())
            if mapped_doc_key and mapped_doc_key not in seed_doc_keys:
                seed_doc_keys.append(mapped_doc_key)

        normalized[collection_key] = {
            "name": name,
            "label": label,
            "seed_doc_keys": seed_doc_keys,
            "file_names": file_names,
            "keywords": _normalize_string_list(raw_item.get("keywords")),
            "default_country": str(raw_item.get("default_country") or "all").strip() or "all",
            "default_doc_type": str(raw_item.get("default_doc_type") or "summary").strip() or "summary",
        }

    if default_collection_key not in normalized:
        raise ValueError(f"default collection key is missing from manifest: {default_collection_key}")
    return normalized


def _normalize_manifest_collection_keys(
    raw_keys: object,
    *,
    collection_keys: set[str],
    field_name: str,
    fallback: list[str],
) -> list[str]:
    normalized = _normalize_string_list(raw_keys)
    if not normalized:
        normalized = list(fallback)

    items: list[str] = []
    for value in normalized:
        key = value.strip().lower()
        if key not in collection_keys:
            raise ValueError(f"{field_name} references unknown collection key `{value}`")
        if key not in items:
            items.append(key)

    if not items:
        raise ValueError(f"{field_name} requires at least one collection key")
    return items


def _normalize_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y"}


def _normalize_compatibility_bundle(
    raw_bundle: object,
    *,
    collection_keys: set[str],
    fallback: dict[str, object],
) -> dict[str, object]:
    if not isinstance(raw_bundle, dict):
        raw_bundle = {}

    bundle_key = str(raw_bundle.get("key") or fallback.get("key") or "sample_pack").strip().lower() or "sample_pack"
    label = str(raw_bundle.get("label") or fallback.get("label") or "sample-pack 호환 번들").strip()
    if not label:
        raise ValueError("compatibility_bundle requires label")

    bundle_collection_keys = _normalize_manifest_collection_keys(
        raw_bundle.get("collection_keys"),
        collection_keys=collection_keys,
        field_name="compatibility_bundle.collection_keys",
        fallback=list(fallback.get("collection_keys", [])),
    )
    return {
        "key": bundle_key,
        "label": label,
        "collection_keys": bundle_collection_keys,
        "optional": _normalize_bool(raw_bundle.get("optional"), bool(fallback.get("optional", True))),
    }


def _normalize_seed_corpus(raw_corpus: object, *, fallback: dict[str, object]) -> dict[str, object]:
    if not isinstance(raw_corpus, dict):
        raw_corpus = {}

    corpus = {
        "key": str(raw_corpus.get("key") or fallback.get("key") or "bootstrap").strip(),
        "label": str(raw_corpus.get("label") or fallback.get("label") or "bootstrap corpus").strip(),
        "role": str(raw_corpus.get("role") or fallback.get("role") or "demo_bootstrap").strip(),
        "dataset": str(raw_corpus.get("dataset") or fallback.get("dataset") or "unknown").strip(),
        "description": str(raw_corpus.get("description") or fallback.get("description") or "").strip(),
    }
    if not corpus["key"] or not corpus["label"]:
        raise ValueError("seed_corpus requires key and label")
    return corpus


def _normalize_collection_manifest(
    payload: dict[str, Any],
) -> tuple[
    str,
    dict[str, dict[str, object]],
    dict[str, dict[str, object]],
    list[str],
    dict[str, object],
    dict[str, object],
]:
    fallback = _FALLBACK_COLLECTION_MANIFEST
    default_collection_key = str(payload.get("default_collection_key") or fallback["default_collection_key"]).strip().lower() or "all"
    raw_seed_documents = payload.get("seed_documents", fallback["seed_documents"])
    raw_collections = payload.get("collections", fallback["collections"])
    seed_documents = _normalize_seed_documents(raw_seed_documents, default_collection_key=default_collection_key)
    collections = _normalize_collections(
        raw_collections,
        default_collection_key=default_collection_key,
        seed_documents=seed_documents,
    )
    collection_keys = set(collections.keys())
    default_runtime_collection_keys = _normalize_manifest_collection_keys(
        payload.get("default_runtime_collection_keys"),
        collection_keys=collection_keys,
        field_name="default_runtime_collection_keys",
        fallback=list(fallback.get("default_runtime_collection_keys", [default_collection_key])),
    )
    compatibility_bundle = _normalize_compatibility_bundle(
        payload.get("compatibility_bundle"),
        collection_keys=collection_keys,
        fallback=dict(fallback.get("compatibility_bundle", {})),
    )
    seed_corpus = _normalize_seed_corpus(
        payload.get("seed_corpus"),
        fallback=dict(fallback.get("seed_corpus", {})),
    )
    return (
        default_collection_key,
        seed_documents,
        collections,
        default_runtime_collection_keys,
        compatibility_bundle,
        seed_corpus,
    )


def _load_collection_manifest(
    path: Path,
) -> tuple[
    str,
    dict[str, dict[str, object]],
    dict[str, dict[str, object]],
    list[str],
    dict[str, object],
    dict[str, object],
]:
    if not path.exists():
        return _normalize_collection_manifest(_FALLBACK_COLLECTION_MANIFEST)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("collection manifest root must be an object")
    return _normalize_collection_manifest(payload)


def _copy_metadata(metadata: dict[str, object]) -> dict[str, object]:
    copied: dict[str, object] = {}
    for key, value in metadata.items():
        if isinstance(value, list):
            copied[key] = list(value)
        else:
            copied[key] = value
    return copied


(
    DEFAULT_COLLECTION_KEY,
    SEED_DOCUMENTS,
    COLLECTION_CONFIGS,
    DEFAULT_RUNTIME_COLLECTION_KEYS,
    COMPATIBILITY_BUNDLE_CONFIG,
    SEED_CORPUS_CONFIG,
) = _load_collection_manifest(COLLECTION_MANIFEST_PATH)
DEFAULT_FILE_NAMES = list(COLLECTION_CONFIGS[DEFAULT_COLLECTION_KEY]["file_names"])
COUNTRY_BY_STEM = {
    Path(str(item["file_name"])).stem.lower(): str(item.get("metadata", {}).get("country", "unknown"))
    for item in SEED_DOCUMENTS.values()
}
_SEED_DOCUMENTS_BY_FILE_NAME = {
    str(item["file_name"]).strip().lower(): item
    for item in SEED_DOCUMENTS.values()
}


def get_seed_document_config(doc_key: str) -> dict[str, object] | None:
    item = SEED_DOCUMENTS.get(doc_key.strip().lower())
    if item is None:
        return None
    return {
        **item,
        "metadata": _copy_metadata(item.get("metadata", {})),
    }


def get_seed_document_config_by_file_name(file_name: str) -> dict[str, object] | None:
    item = _SEED_DOCUMENTS_BY_FILE_NAME.get(file_name.strip().lower())
    if item is None:
        return None
    return {
        **item,
        "metadata": _copy_metadata(item.get("metadata", {})),
    }


def get_seed_document_collection_key(file_name: str) -> str:
    item = get_seed_document_config_by_file_name(file_name)
    if item is None:
        return DEFAULT_COLLECTION_KEY
    return str(item.get("route_collection_key") or DEFAULT_COLLECTION_KEY)


def build_seed_document_metadata(file_name: str, *, doc_key: str | None = None) -> dict[str, object]:
    resolved_doc_key = (doc_key or Path(file_name).stem).strip().lower()
    item = get_seed_document_config_by_file_name(file_name)
    metadata = _copy_metadata(item.get("metadata", {})) if item else {}
    metadata["source"] = file_name
    metadata["doc_key"] = resolved_doc_key
    metadata.setdefault("country", "unknown")
    metadata.setdefault("doc_type", "document")
    metadata.setdefault("source_type", "seed_markdown")
    tags = metadata.get("tags")
    metadata["tags"] = list(tags) if isinstance(tags, list) else []
    return metadata
