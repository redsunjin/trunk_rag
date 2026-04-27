from __future__ import annotations

from scripts import smoke_reindex_rollback_drill


def test_rollback_drill_refuses_without_explicit_local_env(monkeypatch):
    def fail_smoke(**kwargs):
        raise AssertionError("guarded smoke must not run when env guard fails")

    def fail_reindex(**kwargs):
        raise AssertionError("recovery reindex must not run when env guard fails")

    monkeypatch.setattr(smoke_reindex_rollback_drill, "load_project_env", lambda: None)
    monkeypatch.delenv(
        smoke_reindex_rollback_drill.mutation_executor_service.MUTATION_EXECUTION_ENV_KEY,
        raising=False,
    )
    monkeypatch.delenv(
        smoke_reindex_rollback_drill.tool_audit_sink_service.AUDIT_SINK_BACKEND_ENV_KEY,
        raising=False,
    )
    monkeypatch.delenv(
        smoke_reindex_rollback_drill.tool_audit_sink_service.AUDIT_SINK_DIR_ENV_KEY,
        raising=False,
    )
    monkeypatch.setattr(smoke_reindex_rollback_drill.smoke_agent_runtime, "run_smoke", fail_smoke)
    monkeypatch.setattr(smoke_reindex_rollback_drill.index_service, "reindex", fail_reindex)

    result = smoke_reindex_rollback_drill.run_drill()

    assert result["ok"] is False
    assert result["error"]["code"] == smoke_reindex_rollback_drill.ERROR_ROLLBACK_DRILL_ENV_NOT_ENABLED
    assert result["checks"] == [
        {
            "name": "env_guard",
            "ok": False,
            "summary": result["env_guard"],
        }
    ]
    assert result["env_guard"]["missing_or_invalid"] == [
        smoke_reindex_rollback_drill.mutation_executor_service.MUTATION_EXECUTION_ENV_KEY,
        smoke_reindex_rollback_drill.tool_audit_sink_service.AUDIT_SINK_BACKEND_ENV_KEY,
        smoke_reindex_rollback_drill.tool_audit_sink_service.AUDIT_SINK_DIR_ENV_KEY,
    ]


def test_rollback_drill_runs_guarded_promotion_and_recovery(monkeypatch, tmp_path):
    calls = []
    vector_counts = iter([10, 12])

    def fake_get_vector_count_fast(collection_name):
        calls.append(("count", collection_name))
        return next(vector_counts)

    def fake_run_smoke(**kwargs):
        calls.append(("smoke", kwargs))
        return {
            "ok": True,
            "checks": [
                {
                    "name": "write_tool_apply_not_enabled",
                    "ok": True,
                    "summary": {
                        "ok": True,
                        "error_code": None,
                        "mutation_executor_result": {
                            "audit_sequence_id": 5,
                            "runtime_chunks": 12,
                            "runtime_vectors": 12,
                        },
                        "mutation_executor_audit_receipt": {
                            "record_kind": "mutation_executor_post_execution",
                            "pre_executor_audit_sequence_id": 5,
                            "sequence_id": 6,
                        },
                    },
                }
            ],
        }

    def fake_reindex(**kwargs):
        calls.append(("reindex", kwargs))
        return {
            "collection_key": kwargs["collection_key"],
            "collection": "doc_rag_main",
            "chunks": 12,
            "vectors": 12,
            "reindex_scope": "default_runtime_only",
        }

    monkeypatch.setattr(smoke_reindex_rollback_drill, "load_project_env", lambda: None)
    monkeypatch.setenv(
        smoke_reindex_rollback_drill.mutation_executor_service.MUTATION_EXECUTION_ENV_KEY,
        "1",
    )
    monkeypatch.setenv(
        smoke_reindex_rollback_drill.tool_audit_sink_service.AUDIT_SINK_BACKEND_ENV_KEY,
        "local_file",
    )
    monkeypatch.setenv(
        smoke_reindex_rollback_drill.tool_audit_sink_service.AUDIT_SINK_DIR_ENV_KEY,
        str(tmp_path / "audit"),
    )
    monkeypatch.setattr(smoke_reindex_rollback_drill.collection_service, "get_collection_name", lambda key: "doc_rag_main")
    monkeypatch.setattr(smoke_reindex_rollback_drill.collection_service, "resolve_collection_key", lambda key: key)
    monkeypatch.setattr(smoke_reindex_rollback_drill.index_service, "get_vector_count_fast", fake_get_vector_count_fast)
    monkeypatch.setattr(smoke_reindex_rollback_drill.smoke_agent_runtime, "run_smoke", fake_run_smoke)
    monkeypatch.setattr(smoke_reindex_rollback_drill.index_service, "reindex", fake_reindex)

    result = smoke_reindex_rollback_drill.run_drill(collection_key="all")

    assert result["ok"] is True
    assert result["pre_state"]["vector_count"] == 10
    assert result["post_recovery_state"]["vector_count"] == 12
    assert result["guarded_top_level_promotion"]["mutation_executor_audit_receipt"]["sequence_id"] == 6
    assert [check["name"] for check in result["checks"]] == [
        "env_guard",
        "pre_state_captured",
        "guarded_top_level_promotion_smoke",
        "post_executor_audit_linkage",
        "recovery_rebuild_from_source",
        "post_recovery_state_captured",
    ]
    assert calls == [
        ("count", "doc_rag_main"),
        (
            "smoke",
            {
                "opt_in_live_binding": True,
                "opt_in_live_binding_stage_guarded": True,
                "opt_in_top_level_promotion": True,
            },
        ),
        (
            "reindex",
            {
                "reset": True,
                "collection_key": "all",
                "include_compatibility_bundle": False,
            },
        ),
        ("count", "doc_rag_main"),
    ]
