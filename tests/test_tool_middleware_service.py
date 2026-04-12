from __future__ import annotations

from services import actor_policy_service, tool_middleware_service, tool_trace_service
from services.tool_registry_service import ToolContext


def test_tool_middleware_wraps_read_tool_with_request_id_budget_and_audit():
    result = tool_middleware_service.invoke_tool_with_middlewares(
        "read_doc",
        {"collection": "fr", "doc_key": "fr"},
        context=ToolContext(request_id="", actor="internal_agent"),
        allowed_tools=("read_doc",),
        timeout_seconds=12,
    )

    assert result["ok"] is True
    assert result["result"]["origin"] == "seed"
    assert result["middleware"]["request_id"].startswith("tool-")
    assert result["middleware"]["actor"] == "internal_agent"
    assert result["middleware"]["timeout_seconds"] == 12.0
    assert result["middleware"]["allowed_tools"] == ["read_doc"]
    assert result["middleware"]["policy"]["actor_category"] == "internal_read_only"
    assert result["middleware"]["policy"]["mutation_candidate_tools"] == []
    assert "preview" not in result["middleware"]["contracts"]
    assert result["middleware"]["contracts"]["persisted_audit"]["request_id"] == result["middleware"]["request_id"]
    assert result["middleware"]["contracts"]["persisted_audit"]["tool"] == {
        "name": "read_doc",
        "side_effect": "read",
    }
    assert [item["middleware"] for item in result["middleware"]["trace"]] == [
        "request_id",
        "timeout_budget",
        "tool_allowlist",
        "mutation_policy_guard",
        "unsafe_action_guard",
        "audit_log",
    ]
    assert [item["event"] for item in result["middleware"]["audit_log"]] == [
        "tool.invoke.requested",
        "tool.invoke.completed",
    ]
    assert result["execution_trace"]["schema_version"] == tool_trace_service.TRACE_SCHEMA_VERSION
    assert result["execution_trace"]["request_id"] == result["middleware"]["request_id"]
    assert result["execution_trace"]["tool"]["name"] == "read_doc"
    assert result["execution_trace"]["policy"]["actor_category"] == "internal_read_only"
    assert result["execution_trace"]["contracts"]["persisted_audit"]["actor_category"] == "internal_read_only"
    assert result["execution_trace"]["tool"]["result_seed"]["origin"] == "seed"
    assert result["execution_trace"]["outcome"] == {"ok": True, "error": None}


def test_tool_allowlist_blocks_before_adapter(monkeypatch):
    def fail_if_invoked(*args, **kwargs):
        raise AssertionError("adapter must not be called when allowlist blocks")

    monkeypatch.setattr(tool_middleware_service.tool_registry_service, "invoke_tool", fail_if_invoked)

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "read_doc",
        {"collection": "fr", "doc_key": "fr"},
        allowed_tools=("health_check",),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "TOOL_NOT_ALLOWED"
    assert result["middleware"]["audit_log"][-1]["event"] == "tool.invoke.blocked"
    assert result["execution_trace"]["middleware"]["blocked_by"] == "tool_allowlist"
    assert result["execution_trace"]["outcome"]["error"]["code"] == "TOOL_NOT_ALLOWED"


def test_tool_allowlist_defaults_to_actor_policy_when_not_explicitly_provided(monkeypatch):
    def fail_if_invoked(*args, **kwargs):
        raise AssertionError("write adapter must not be called when actor policy blocks")

    monkeypatch.setattr(tool_middleware_service.tool_registry_service, "invoke_tool", fail_if_invoked)

    result = tool_middleware_service.invoke_tool_with_middlewares("reindex", {"collection": "all"})

    assert result["ok"] is False
    assert result["error"]["code"] == "TOOL_NOT_ALLOWED"
    assert result["middleware"]["policy"]["actor_category"] == "internal_read_only"
    assert result["middleware"]["policy"]["mutation_candidate_tools"] == []
    assert result["execution_trace"]["middleware"]["blocked_by"] == "tool_allowlist"


def test_mutation_policy_guard_requires_admin_auth_for_candidate_write(monkeypatch):
    def fail_if_invoked(*args, **kwargs):
        raise AssertionError("write adapter must not be called before auth")

    monkeypatch.setattr(tool_middleware_service.tool_registry_service, "invoke_tool", fail_if_invoked)

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all"},
        context=ToolContext(actor="maintenance", allow_mutation=True),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "ADMIN_AUTH_REQUIRED"
    assert result["middleware"]["trace"][-1]["middleware"] == "mutation_policy_guard"
    assert result["execution_trace"]["middleware"]["blocked_by"] == "mutation_policy_guard"


def test_mutation_policy_guard_requires_intent_after_admin_auth(monkeypatch):
    def fail_if_invoked(*args, **kwargs):
        raise AssertionError("write adapter must not be called before mutation intent")

    monkeypatch.setattr(tool_middleware_service.tool_registry_service, "invoke_tool", fail_if_invoked)
    monkeypatch.setattr(tool_middleware_service.runtime_service, "verify_admin_code", lambda code: None)

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all"},
        context=ToolContext(actor="maintenance", admin_code="admin1234", allow_mutation=True),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "MUTATION_INTENT_REQUIRED"
    assert result["middleware"]["trace"][-1]["middleware"] == "mutation_policy_guard"
    assert result["execution_trace"]["middleware"]["blocked_by"] == "mutation_policy_guard"


def test_mutation_policy_guard_requires_preview_after_auth_and_intent(monkeypatch):
    def fail_if_invoked(*args, **kwargs):
        raise AssertionError("write adapter must not be called before preview")

    monkeypatch.setattr(tool_middleware_service.tool_registry_service, "invoke_tool", fail_if_invoked)
    monkeypatch.setattr(tool_middleware_service.runtime_service, "verify_admin_code", lambda code: None)

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all"},
        context=ToolContext(
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            allow_mutation=True,
        ),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "PREVIEW_REQUIRED"
    assert result["error"]["preview_contract"] == {
        "schema_version": tool_trace_service.PREVIEW_CONTRACT_SCHEMA_VERSION,
        "request_id": result["middleware"]["request_id"],
        "actor_category": "maintenance_mutation",
        "audit_scope": "maintenance",
        "tool": {
            "name": "reindex",
            "side_effect": "write",
        },
        "target": {
            "collection_key": "all",
            "reset": True,
            "include_compatibility_bundle": False,
            "impact_scope": "core_all_only",
        },
        "preview_fields": [
            "collection_key",
            "reset",
            "include_compatibility_bundle",
            "impact_summary",
        ],
        "expected_side_effect": "Reindex all collection contents.",
        "redaction": {
            "audiences": ["internal", "public", "persisted"],
            "raw_content_allowed": False,
            "admin_code_allowed": False,
            "document_body_allowed": False,
        },
    }
    assert result["middleware"]["trace"][-1]["middleware"] == "mutation_policy_guard"
    assert result["execution_trace"]["middleware"]["blocked_by"] == "mutation_policy_guard"
    assert result["execution_trace"]["contracts"]["preview"] == result["error"]["preview_contract"]
    assert result["execution_trace"]["contracts"]["persisted_audit"]["actor_category"] == "maintenance_mutation"


def test_unsafe_action_guard_blocks_write_without_mutation_context(monkeypatch):
    def fail_if_invoked(*args, **kwargs):
        raise AssertionError("write adapter must not be called without mutation context")

    monkeypatch.setattr(tool_middleware_service.tool_registry_service, "invoke_tool", fail_if_invoked)
    policy_decision = actor_policy_service.ActorPolicyDecision(
        actor="maintenance",
        actor_category="maintenance_mutation",
        read_allowed_tools=("health_check",),
        mutation_candidate_tools=("reindex",),
        effective_allowed_tools=("reindex",),
        requires_admin_auth=False,
        requires_mutation_intent=False,
        requires_preview_before_apply=False,
        audit_scope="maintenance",
        source_schema_version="v1.5.actor_policy_source.v1",
        source_path="config/actor_policy_manifest.json",
        used_fallback=False,
    )

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all"},
        context=ToolContext(actor="maintenance"),
        policy_decision=policy_decision,
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "MUTATION_NOT_ALLOWED"
    assert result["middleware"]["trace"][-1]["middleware"] == "unsafe_action_guard"
    assert result["middleware"]["trace"][-1]["status"] == "blocked"
    assert result["execution_trace"]["middleware"]["blocked_by"] == "unsafe_action_guard"


def test_mutation_context_and_timeout_budget_are_passed_to_registry(monkeypatch):
    captured = {}

    def fake_invoke_tool(name, payload, *, context=None):
        captured["name"] = name
        captured["payload"] = payload
        captured["context"] = context
        return {"tool": name, "ok": True, "result": {"status": "queued"}, "error": None}

    monkeypatch.setattr(tool_middleware_service.tool_registry_service, "invoke_tool", fake_invoke_tool)
    policy_decision = actor_policy_service.ActorPolicyDecision(
        actor="maintenance",
        actor_category="maintenance_mutation",
        read_allowed_tools=("health_check", "list_collections"),
        mutation_candidate_tools=("reindex",),
        effective_allowed_tools=("health_check", "list_collections", "reindex"),
        requires_admin_auth=False,
        requires_mutation_intent=False,
        requires_preview_before_apply=False,
        audit_scope="maintenance",
        source_schema_version="v1.5.actor_policy_source.v1",
        source_path="config/actor_policy_manifest.json",
        used_fallback=False,
    )

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all"},
        context=ToolContext(request_id="req-1", actor="maintenance", allow_mutation=True),
        policy_decision=policy_decision,
        timeout_seconds=7,
    )

    assert result["ok"] is True
    assert captured["name"] == "reindex"
    assert captured["payload"] == {"collection": "all"}
    assert captured["context"].request_id == "req-1"
    assert captured["context"].actor == "maintenance"
    assert captured["context"].allow_mutation is True
    assert captured["context"].timeout_seconds == 7.0
    assert result["middleware"]["policy"]["actor_category"] == "maintenance_mutation"
    assert result["middleware"]["policy"]["mutation_candidate_tools"] == ["reindex"]
    assert result["middleware"]["audit_log"][-1]["event"] == "tool.invoke.completed"


def test_execution_trace_includes_search_docs_routing_seed(monkeypatch):
    def fake_build_collection_context(*, question, collection_keys, trace, budget):
        trace.update({"collections": list(collection_keys), "sources": [{"source": "fr.md"}]})
        return "context"

    monkeypatch.setattr(
        tool_middleware_service.tool_registry_service.query_service,
        "build_collection_context",
        fake_build_collection_context,
    )

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "search_docs",
        {"query": "프랑스 과학 인재 양성을 요약해줘.", "query_profile": "sample_pack"},
        context=ToolContext(request_id="req-search"),
        allowed_tools=("search_docs",),
        timeout_seconds=9,
    )

    assert result["ok"] is True
    assert result["execution_trace"]["routing"]["route_reason"] == "compatibility_keyword"
    assert result["execution_trace"]["routing"]["collections"] == ["fr"]
    assert result["execution_trace"]["routing"]["query_profile"] == "sample_pack"
    assert result["execution_trace"]["tool"]["result_seed"]["source_count"] == 1


def test_custom_middlewares_run_in_sequence(monkeypatch):
    calls = []

    def first(state):
        calls.append("first")
        tool_middleware_service.request_id_middleware(state)

    def second(state):
        calls.append("second")
        tool_middleware_service.audit_log_middleware(state)

    monkeypatch.setattr(
        tool_middleware_service.tool_registry_service,
        "invoke_tool",
        lambda name, payload, *, context=None: {
            "tool": name,
            "ok": True,
            "result": {"request_id": context.request_id},
            "error": None,
        },
    )

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "health_check",
        middlewares=(first, second),
    )

    assert result["ok"] is True
    assert calls == ["first", "second"]
    assert [item["middleware"] for item in result["middleware"]["trace"]] == ["request_id", "audit_log"]
