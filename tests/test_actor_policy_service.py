from __future__ import annotations

from core.actor_policy_manifest import get_actor_policy_manifest
from services import actor_policy_service


def test_actor_policy_manifest_defaults_are_loaded():
    manifest = get_actor_policy_manifest(force_reload=True)

    assert manifest["schema_version"] == "v1.5.actor_policy_source.v1"
    assert manifest["default_actor_category"] == "internal_read_only"
    assert manifest["fallback_actor_category"] == "unknown_read_only"
    assert manifest["tool_groups"]["read_query"] == [
        "search_docs",
        "read_doc",
        "list_collections",
        "health_check",
    ]


def test_resolve_actor_policy_returns_internal_read_only_baseline():
    decision = actor_policy_service.resolve_actor_policy("internal_agent")

    assert decision.actor_category == "internal_read_only"
    assert decision.read_allowed_tools == (
        "search_docs",
        "read_doc",
        "list_collections",
        "health_check",
    )
    assert decision.mutation_candidate_tools == ()
    assert decision.effective_allowed_tools == decision.read_allowed_tools
    assert decision.used_fallback is False


def test_resolve_actor_policy_uses_fallback_for_unknown_actor():
    decision = actor_policy_service.resolve_actor_policy("guest-bot")

    assert decision.actor_category == "unknown_read_only"
    assert decision.read_allowed_tools == ("health_check",)
    assert decision.mutation_candidate_tools == ()
    assert decision.used_fallback is True
