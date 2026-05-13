from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from services import collection_service

DEFAULT_TOPIC = "europe_science_history"


def _normalize_text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_document_metadata(
    metadata: Mapping[str, object] | None,
    *,
    fallback_source: str | None = None,
    fallback_country: str | None = None,
    fallback_doc_type: str | None = None,
    default_topic: str = DEFAULT_TOPIC,
    enable_extended_fields: bool = True,
) -> dict[str, Any]:
    normalized: dict[str, Any] = dict(metadata or {})

    source_value = _normalize_text(normalized.get("source"))
    source_file_value = _normalize_text(normalized.get("source_file"))
    country_value = _normalize_text(normalized.get("country"))
    doc_type_value = _normalize_text(normalized.get("doc_type"))
    topic_value = _normalize_text(normalized.get("topic"))

    source = source_value or source_file_value or _normalize_text(fallback_source) or "unknown"
    country = country_value or _normalize_text(fallback_country) or "all"
    doc_type = doc_type_value or _normalize_text(fallback_doc_type) or "country"
    source_file = source_file_value or source

    normalized["source"] = source
    normalized["country"] = country
    normalized["doc_type"] = doc_type

    if enable_extended_fields:
        normalized["source_file"] = source_file
        normalized["topic"] = topic_value or default_topic
    else:
        if source_file_value:
            normalized["source_file"] = source_file_value
        else:
            normalized.pop("source_file", None)
        if topic_value:
            normalized["topic"] = topic_value
        else:
            normalized.pop("topic", None)

    year_text = _normalize_text(normalized.get("year_text"))
    scientist = _normalize_text(normalized.get("scientist"))
    if year_text:
        normalized["year_text"] = year_text
    else:
        normalized.pop("year_text", None)
    if scientist:
        normalized["scientist"] = scientist
    else:
        normalized.pop("scientist", None)

    return normalized


def normalize_document_metadata_for_collection(
    metadata: Mapping[str, object] | None,
    *,
    collection_key: str,
    fallback_source: str | None = None,
    default_topic: str = DEFAULT_TOPIC,
    enable_extended_fields: bool = True,
) -> dict[str, Any]:
    return normalize_document_metadata(
        metadata,
        fallback_source=fallback_source,
        fallback_country=collection_service.default_country_for_collection(collection_key),
        fallback_doc_type=collection_service.default_doc_type_for_collection(collection_key),
        default_topic=default_topic,
        enable_extended_fields=enable_extended_fields,
    )
