from __future__ import annotations

from typing import Callable

from core.settings import (
    COLLECTION_CONFIGS,
    COLLECTION_HARD_CAP,
    COLLECTION_SOFT_CAP,
    COUNTRY_BY_COLLECTION_KEY,
    DEFAULT_COLLECTION_KEY,
    MAX_QUERY_COLLECTIONS,
)


def default_country_for_collection(collection_key: str) -> str:
    return COUNTRY_BY_COLLECTION_KEY.get(collection_key, "all")


def default_doc_type_for_collection(collection_key: str) -> str:
    if collection_key in {"all", "eu"}:
        return "summary"
    return "country"


def resolve_collection_key(collection: str | None) -> str | None:
    if collection is None:
        return None

    value = collection.strip().lower()
    if not value:
        return None

    if value in COLLECTION_CONFIGS:
        return value

    for key, config in COLLECTION_CONFIGS.items():
        if value == str(config["name"]).strip().lower():
            return key

    raise ValueError(f"Unsupported collection: {collection}")


def get_collection_config(collection_key: str) -> dict[str, object]:
    config = COLLECTION_CONFIGS.get(collection_key)
    if config is None:
        raise ValueError(f"Unsupported collection key: {collection_key}")
    return config


def guess_collection_key_from_query(query: str) -> str:
    normalized = query.strip().lower()
    for key, config in COLLECTION_CONFIGS.items():
        if key == DEFAULT_COLLECTION_KEY:
            continue
        for keyword in config.get("keywords", ()):
            if str(keyword).lower() in normalized:
                return key
    return DEFAULT_COLLECTION_KEY


def resolve_collection_for_query(query: str, requested_collection: str | None) -> tuple[str, str]:
    explicit_key = resolve_collection_key(requested_collection)
    if explicit_key:
        return explicit_key, "explicit"

    guessed_key = guess_collection_key_from_query(query)
    if guessed_key != DEFAULT_COLLECTION_KEY:
        return guessed_key, "keyword"
    return DEFAULT_COLLECTION_KEY, "default"


def dedupe_collection_keys(collection_keys: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for key in collection_keys:
        if key in seen:
            continue
        seen.add(key)
        deduped.append(key)
    return deduped


def resolve_collection_keys_for_query(
    query: str,
    requested_collection: str | None,
    requested_collections: list[str] | None,
) -> tuple[list[str], str, bool]:
    explicit_values = [value.strip() for value in (requested_collections or []) if value.strip()]
    if explicit_values:
        keys: list[str] = []
        for value in explicit_values:
            key = resolve_collection_key(value)
            if key is None:
                continue
            keys.append(key)
        keys = dedupe_collection_keys(keys)
        if not keys:
            raise ValueError("No valid collections provided.")
        if len(keys) > MAX_QUERY_COLLECTIONS:
            raise ValueError(f"Too many collections. up to {MAX_QUERY_COLLECTIONS} collections are allowed.")
        route_reason = "explicit_multi" if len(keys) > 1 else "explicit"
        return keys, route_reason, False

    key, route_reason = resolve_collection_for_query(query, requested_collection)
    allow_default_fallback = route_reason == "keyword" and requested_collection is None
    return [key], route_reason, allow_default_fallback


def list_collection_keys() -> list[str]:
    return list(COLLECTION_CONFIGS.keys())


def get_collection_name(collection_key: str) -> str:
    return str(get_collection_config(collection_key)["name"])


def calculate_cap_status(vector_count: int) -> dict[str, int | float | bool]:
    soft_usage = (vector_count / COLLECTION_SOFT_CAP) if COLLECTION_SOFT_CAP else 0.0
    hard_usage = (vector_count / COLLECTION_HARD_CAP) if COLLECTION_HARD_CAP else 0.0
    return {
        "soft_cap": COLLECTION_SOFT_CAP,
        "hard_cap": COLLECTION_HARD_CAP,
        "soft_usage_ratio": round(soft_usage, 4),
        "hard_usage_ratio": round(hard_usage, 4),
        "soft_exceeded": vector_count >= COLLECTION_SOFT_CAP,
        "hard_exceeded": vector_count >= COLLECTION_HARD_CAP,
    }


def list_collection_statuses(get_vector_count_fast: Callable[[str], int | None]) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for key in list_collection_keys():
        config = get_collection_config(key)
        collection_name = str(config["name"])
        vector_count = get_vector_count_fast(collection_name)
        vectors = vector_count if isinstance(vector_count, int) else 0
        cap_status = calculate_cap_status(vectors)
        items.append(
            {
                "key": key,
                "name": collection_name,
                "label": config["label"],
                "file_names": list(config["file_names"]),
                "vectors": vectors,
                **cap_status,
            }
        )
    return items
