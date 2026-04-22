from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from common import load_project_env
from core.settings import DEFAULT_COLLECTION_KEY
from services import collection_service, index_service, mutation_executor_service, tool_audit_sink_service
from scripts import smoke_agent_runtime

REINDEX_ROLLBACK_DRILL_SCHEMA_VERSION = "v1.5.reindex_live_adapter_rollback_drill.v1"
ERROR_ROLLBACK_DRILL_ENV_NOT_ENABLED = "ROLLBACK_DRILL_ENV_NOT_ENABLED"


def _parse_bool_env(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_guard() -> dict[str, object]:
    mutation_execution_enabled = _parse_bool_env(os.getenv(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY))
    audit_backend = str(os.getenv(tool_audit_sink_service.AUDIT_SINK_BACKEND_ENV_KEY, "")).strip()
    audit_dir = str(os.getenv(tool_audit_sink_service.AUDIT_SINK_DIR_ENV_KEY, "")).strip()
    errors: list[str] = []
    if not mutation_execution_enabled:
        errors.append(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY)
    if audit_backend != "local_file":
        errors.append(tool_audit_sink_service.AUDIT_SINK_BACKEND_ENV_KEY)
    if not audit_dir:
        errors.append(tool_audit_sink_service.AUDIT_SINK_DIR_ENV_KEY)
    return {
        "ok": not errors,
        "mutation_execution_enabled": mutation_execution_enabled,
        "audit_backend": audit_backend or None,
        "audit_dir": audit_dir or None,
        "missing_or_invalid": errors,
    }


def _capture_collection_state(collection_key: str) -> dict[str, object]:
    collection_name = collection_service.get_collection_name(collection_key)
    vector_count = index_service.get_vector_count_fast(collection_name)
    return {
        "collection_key": collection_key,
        "collection_name": collection_name,
        "vector_count": vector_count if isinstance(vector_count, int) else None,
    }


def _apply_summary(smoke_result: dict[str, object]) -> dict[str, object]:
    checks = smoke_result.get("checks")
    if not isinstance(checks, list):
        return {}
    for check in checks:
        if isinstance(check, dict) and check.get("name") == "write_tool_apply_not_enabled":
            summary = check.get("summary")
            return dict(summary) if isinstance(summary, dict) else {}
    return {}


def _audit_linkage_ok(summary: dict[str, object]) -> bool:
    audit_receipt = summary.get("mutation_executor_audit_receipt")
    executor_result = summary.get("mutation_executor_result")
    if not isinstance(audit_receipt, dict) or not isinstance(executor_result, dict):
        return False
    return (
        audit_receipt.get("record_kind") == "mutation_executor_post_execution"
        and audit_receipt.get("pre_executor_audit_sequence_id") == executor_result.get("audit_sequence_id")
        and audit_receipt.get("sequence_id") is not None
    )


def run_drill(collection_key: str = DEFAULT_COLLECTION_KEY) -> dict[str, object]:
    load_project_env()
    resolved_collection_key = collection_service.resolve_collection_key(collection_key) or DEFAULT_COLLECTION_KEY
    guard = _env_guard()
    if guard["ok"] is not True:
        return {
            "schema_version": REINDEX_ROLLBACK_DRILL_SCHEMA_VERSION,
            "ok": False,
            "error": {
                "code": ERROR_ROLLBACK_DRILL_ENV_NOT_ENABLED,
                "message": "Rollback drill requires explicit local mutation execution and local-file audit env.",
                "missing_or_invalid": guard["missing_or_invalid"],
            },
            "env_guard": guard,
            "collection_key": resolved_collection_key,
            "checks": [
                {
                    "name": "env_guard",
                    "ok": False,
                    "summary": guard,
                }
            ],
        }

    pre_state = _capture_collection_state(resolved_collection_key)
    guarded_smoke = smoke_agent_runtime.run_smoke(
        opt_in_live_binding=True,
        opt_in_live_binding_stage_guarded=True,
        opt_in_top_level_promotion=True,
    )
    guarded_summary = _apply_summary(guarded_smoke)
    recovery_result = index_service.reindex(
        reset=True,
        collection_key=resolved_collection_key,
        include_compatibility_bundle=False,
    )
    post_recovery_state = _capture_collection_state(resolved_collection_key)
    recovery_chunks = recovery_result.get("chunks") if isinstance(recovery_result, dict) else None
    recovery_vectors = recovery_result.get("vectors") if isinstance(recovery_result, dict) else None
    checks = [
        {
            "name": "env_guard",
            "ok": True,
            "summary": guard,
        },
        {
            "name": "pre_state_captured",
            "ok": pre_state.get("vector_count") is not None,
            "summary": pre_state,
        },
        {
            "name": "guarded_top_level_promotion_smoke",
            "ok": guarded_smoke.get("ok") is True and guarded_summary.get("ok") is True,
            "summary": guarded_summary,
        },
        {
            "name": "post_executor_audit_linkage",
            "ok": _audit_linkage_ok(guarded_summary),
            "summary": guarded_summary.get("mutation_executor_audit_receipt"),
        },
        {
            "name": "recovery_rebuild_from_source",
            "ok": isinstance(recovery_chunks, int)
            and recovery_chunks > 0
            and isinstance(recovery_vectors, int)
            and recovery_vectors > 0,
            "summary": recovery_result,
        },
        {
            "name": "post_recovery_state_captured",
            "ok": post_recovery_state.get("vector_count") is not None,
            "summary": post_recovery_state,
        },
    ]
    return {
        "schema_version": REINDEX_ROLLBACK_DRILL_SCHEMA_VERSION,
        "ok": all(check["ok"] for check in checks),
        "collection_key": resolved_collection_key,
        "env_guard": guard,
        "pre_state": pre_state,
        "guarded_top_level_promotion": guarded_summary,
        "recovery_result": recovery_result,
        "post_recovery_state": post_recovery_state,
        "checks": checks,
    }


def main() -> int:
    args = sys.argv[1:]
    collection_key = DEFAULT_COLLECTION_KEY
    if "--collection" in args:
        index = args.index("--collection")
        try:
            collection_key = args[index + 1]
        except IndexError:
            print("--collection requires a value", file=sys.stderr)
            return 2
    result = run_drill(collection_key=collection_key)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result.get("ok") is True:
        return 0
    error = result.get("error")
    if isinstance(error, dict) and error.get("code") == ERROR_ROLLBACK_DRILL_ENV_NOT_ENABLED:
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
