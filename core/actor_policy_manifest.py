from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


ACTOR_POLICY_MANIFEST_PATH = project_root() / "config" / "actor_policy_manifest.json"

_FALLBACK_ACTOR_POLICY_MANIFEST: dict[str, Any] = {
    "schema_version": "v1.5.actor_policy_source.v1",
    "default_actor_category": "internal_read_only",
    "fallback_actor_category": "unknown_read_only",
    "tool_groups": {
        "read_query": [
            "search_docs",
            "read_doc",
            "list_collections",
            "health_check",
        ],
        "read_admin": ["list_upload_requests"],
        "maintenance_read": ["health_check", "list_collections"],
        "fallback_runtime": ["health_check"],
        "write_upload_review": [
            "approve_upload_request",
            "reject_upload_request",
        ],
        "write_index_maintenance": ["reindex"],
    },
    "actor_aliases": {
        "internal": "internal_read_only",
        "internal_agent": "internal_read_only",
        "admin": "admin_review_mutation",
        "admin_read_only": "admin_read_only",
        "admin_review": "admin_review_mutation",
        "maintenance": "maintenance_mutation",
        "operator": "maintenance_mutation",
    },
    "actor_prefix_aliases": {
        "internal": "internal_read_only",
        "admin": "admin_review_mutation",
        "maintenance": "maintenance_mutation",
        "operator": "maintenance_mutation",
    },
    "actors": {
        "internal_read_only": {
            "read_groups": ["read_query"],
            "mutation_groups": [],
            "requires_admin_auth": False,
            "requires_mutation_intent": False,
            "requires_preview_before_apply": False,
            "audit_scope": "request_only",
        },
        "admin_read_only": {
            "read_groups": ["read_query", "read_admin"],
            "mutation_groups": [],
            "requires_admin_auth": True,
            "requires_mutation_intent": False,
            "requires_preview_before_apply": False,
            "audit_scope": "request_only",
        },
        "admin_review_mutation": {
            "read_groups": ["read_query", "read_admin"],
            "mutation_groups": ["write_upload_review"],
            "requires_admin_auth": True,
            "requires_mutation_intent": True,
            "requires_preview_before_apply": True,
            "audit_scope": "mutation_review",
        },
        "maintenance_mutation": {
            "read_groups": ["maintenance_read"],
            "mutation_groups": ["write_index_maintenance"],
            "requires_admin_auth": True,
            "requires_mutation_intent": True,
            "requires_preview_before_apply": True,
            "audit_scope": "maintenance",
        },
        "unknown_read_only": {
            "read_groups": ["fallback_runtime"],
            "mutation_groups": [],
            "requires_admin_auth": False,
            "requires_mutation_intent": False,
            "requires_preview_before_apply": False,
            "audit_scope": "request_only",
        },
    },
}

_ACTOR_POLICY_MANIFEST_CACHE: dict[str, Any] | None = None


def _normalize_string_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    items: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in items:
            items.append(text)
    return items


def _normalize_string_map(values: object) -> dict[str, str]:
    if not isinstance(values, dict):
        return {}
    items: dict[str, str] = {}
    for raw_key, raw_value in values.items():
        key = str(raw_key).strip().lower()
        value = str(raw_value).strip()
        if key and value:
            items[key] = value
    return items


def _normalize_tool_groups(raw_groups: object) -> dict[str, list[str]]:
    if not isinstance(raw_groups, dict) or not raw_groups:
        raise ValueError("actor policy manifest requires a non-empty tool_groups mapping")

    normalized: dict[str, list[str]] = {}
    for raw_key, raw_value in raw_groups.items():
        group_name = str(raw_key).strip()
        if not group_name:
            raise ValueError("actor policy manifest contains an empty tool group")
        tools = _normalize_string_list(raw_value)
        if not tools:
            raise ValueError(f"actor policy tool group requires at least one tool: {group_name}")
        normalized[group_name] = tools
    return normalized


def _normalize_actors(raw_actors: object, *, tool_groups: dict[str, list[str]]) -> dict[str, dict[str, object]]:
    if not isinstance(raw_actors, dict) or not raw_actors:
        raise ValueError("actor policy manifest requires a non-empty actors mapping")

    normalized: dict[str, dict[str, object]] = {}
    for raw_key, raw_value in raw_actors.items():
        actor_category = str(raw_key).strip()
        if not actor_category:
            raise ValueError("actor policy manifest contains an empty actor category")
        if not isinstance(raw_value, dict):
            raise ValueError(f"actor policy category must be an object: {actor_category}")

        read_groups = _normalize_string_list(raw_value.get("read_groups"))
        mutation_groups = _normalize_string_list(raw_value.get("mutation_groups"))
        if not read_groups:
            raise ValueError(f"actor policy category requires read_groups: {actor_category}")
        for group_name in read_groups + mutation_groups:
            if group_name not in tool_groups:
                raise ValueError(
                    f"actor policy category references unknown tool group `{group_name}`: {actor_category}"
                )

        normalized[actor_category] = {
            "read_groups": read_groups,
            "mutation_groups": mutation_groups,
            "requires_admin_auth": bool(raw_value.get("requires_admin_auth", False)),
            "requires_mutation_intent": bool(raw_value.get("requires_mutation_intent", False)),
            "requires_preview_before_apply": bool(raw_value.get("requires_preview_before_apply", False)),
            "audit_scope": str(raw_value.get("audit_scope") or "request_only").strip() or "request_only",
        }
    return normalized


def _normalize_manifest(raw_manifest: object) -> dict[str, Any]:
    if not isinstance(raw_manifest, dict):
        raise ValueError("actor policy manifest must be an object")

    tool_groups = _normalize_tool_groups(raw_manifest.get("tool_groups"))
    actors = _normalize_actors(raw_manifest.get("actors"), tool_groups=tool_groups)
    default_actor_category = str(raw_manifest.get("default_actor_category") or "").strip() or "internal_read_only"
    fallback_actor_category = str(raw_manifest.get("fallback_actor_category") or "").strip() or "unknown_read_only"
    if default_actor_category not in actors:
        raise ValueError(f"default_actor_category is unknown: {default_actor_category}")
    if fallback_actor_category not in actors:
        raise ValueError(f"fallback_actor_category is unknown: {fallback_actor_category}")

    return {
        "schema_version": str(raw_manifest.get("schema_version") or "v1.5.actor_policy_source.v1").strip(),
        "default_actor_category": default_actor_category,
        "fallback_actor_category": fallback_actor_category,
        "tool_groups": tool_groups,
        "actor_aliases": _normalize_string_map(raw_manifest.get("actor_aliases")),
        "actor_prefix_aliases": _normalize_string_map(raw_manifest.get("actor_prefix_aliases")),
        "actors": actors,
    }


def get_actor_policy_manifest(*, force_reload: bool = False) -> dict[str, Any]:
    global _ACTOR_POLICY_MANIFEST_CACHE
    if _ACTOR_POLICY_MANIFEST_CACHE is not None and not force_reload:
        return _ACTOR_POLICY_MANIFEST_CACHE

    if ACTOR_POLICY_MANIFEST_PATH.exists():
        raw_manifest = json.loads(ACTOR_POLICY_MANIFEST_PATH.read_text(encoding="utf-8"))
    else:
        raw_manifest = _FALLBACK_ACTOR_POLICY_MANIFEST
    _ACTOR_POLICY_MANIFEST_CACHE = _normalize_manifest(raw_manifest)
    return _ACTOR_POLICY_MANIFEST_CACHE
