from __future__ import annotations

from dataclasses import dataclass

from core.actor_policy_manifest import ACTOR_POLICY_MANIFEST_PATH, get_actor_policy_manifest


@dataclass(frozen=True)
class ActorPolicyDecision:
    actor: str
    actor_category: str
    read_allowed_tools: tuple[str, ...]
    mutation_candidate_tools: tuple[str, ...]
    effective_allowed_tools: tuple[str, ...]
    requires_admin_auth: bool
    requires_mutation_intent: bool
    requires_preview_before_apply: bool
    audit_scope: str
    source_schema_version: str
    source_path: str
    used_fallback: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "actor": self.actor,
            "actor_category": self.actor_category,
            "read_allowed_tools": list(self.read_allowed_tools),
            "mutation_candidate_tools": list(self.mutation_candidate_tools),
            "effective_allowed_tools": list(self.effective_allowed_tools),
            "requires_admin_auth": self.requires_admin_auth,
            "requires_mutation_intent": self.requires_mutation_intent,
            "requires_preview_before_apply": self.requires_preview_before_apply,
            "audit_scope": self.audit_scope,
            "source_schema_version": self.source_schema_version,
            "source_path": self.source_path,
            "used_fallback": self.used_fallback,
        }


def resolve_allowed_tools(
    policy_decision: ActorPolicyDecision,
    *,
    tool_name: str,
    requested_allowed_tools: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    permitted_tools = list(policy_decision.effective_allowed_tools)
    normalized_tool_name = str(tool_name or "").strip()
    if normalized_tool_name and normalized_tool_name in policy_decision.mutation_candidate_tools:
        if normalized_tool_name not in permitted_tools:
            permitted_tools.append(normalized_tool_name)

    if requested_allowed_tools is None:
        return tuple(permitted_tools)

    return tuple(tool for tool in requested_allowed_tools if tool in permitted_tools)


def _expand_tool_groups(group_names: list[str], tool_groups: dict[str, list[str]]) -> tuple[str, ...]:
    tools: list[str] = []
    for group_name in group_names:
        for tool_name in tool_groups.get(group_name, []):
            if tool_name not in tools:
                tools.append(tool_name)
    return tuple(tools)


def _resolve_actor_category(actor: str, manifest: dict[str, object]) -> tuple[str, bool]:
    normalized_actor = str(actor or "").strip().lower()
    if not normalized_actor:
        return str(manifest["default_actor_category"]), False

    actor_aliases = dict(manifest.get("actor_aliases") or {})
    if normalized_actor in actor_aliases:
        return str(actor_aliases[normalized_actor]), False

    prefix_aliases = dict(manifest.get("actor_prefix_aliases") or {})
    for prefix, actor_category in prefix_aliases.items():
        if normalized_actor.startswith(str(prefix)):
            return str(actor_category), False

    return str(manifest["fallback_actor_category"]), True


def resolve_actor_policy(actor: str, *, manifest: dict[str, object] | None = None) -> ActorPolicyDecision:
    resolved_manifest = manifest or get_actor_policy_manifest()
    actor_category, used_fallback = _resolve_actor_category(actor, resolved_manifest)
    actors = dict(resolved_manifest.get("actors") or {})
    actor_config = dict(actors[actor_category])
    tool_groups = dict(resolved_manifest.get("tool_groups") or {})
    read_allowed_tools = _expand_tool_groups(list(actor_config.get("read_groups") or []), tool_groups)
    mutation_candidate_tools = _expand_tool_groups(list(actor_config.get("mutation_groups") or []), tool_groups)

    return ActorPolicyDecision(
        actor=str(actor or "").strip() or "internal_agent",
        actor_category=actor_category,
        read_allowed_tools=read_allowed_tools,
        mutation_candidate_tools=mutation_candidate_tools,
        effective_allowed_tools=read_allowed_tools,
        requires_admin_auth=bool(actor_config.get("requires_admin_auth", False)),
        requires_mutation_intent=bool(actor_config.get("requires_mutation_intent", False)),
        requires_preview_before_apply=bool(actor_config.get("requires_preview_before_apply", False)),
        audit_scope=str(actor_config.get("audit_scope") or "request_only"),
        source_schema_version=str(resolved_manifest.get("schema_version") or ""),
        source_path=str(ACTOR_POLICY_MANIFEST_PATH),
        used_fallback=used_fallback,
    )
