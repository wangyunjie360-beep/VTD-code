from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SourceEntry:
    id: str
    kind: str
    path: str


@dataclass(slots=True)
class ElementRecord:
    element: str
    description: str
    content_model_kind: str = ""
    child_groups: list[dict[str, Any]] = field(default_factory=list)
    semantic_constraints: list[str] = field(default_factory=list)
    contextual_variants: list[dict[str, Any]] = field(default_factory=list)
    parent_contexts: list[str] = field(default_factory=list)
    required_attributes: list[dict[str, Any]] = field(default_factory=list)
    optional_attributes: list[dict[str, Any]] = field(default_factory=list)
    allowed_children: list[dict[str, Any]] = field(default_factory=list)
    child_order: list[str] = field(default_factory=list)
    multiplicity: dict[str, str] = field(default_factory=dict)
    enum_constraints: dict[str, list[str]] = field(default_factory=dict)
    source_path: str = ""


@dataclass(slots=True)
class ValidationError:
    line: int | None
    column: int | None
    message: str
    rule_hint: str | None = None


@dataclass(slots=True)
class KnowledgeBase:
    records_by_element: dict[str, ElementRecord] = field(default_factory=dict)

    def search(
        self,
        query: str,
        kind: str | None = None,
        top_k: int = 5,
    ) -> list[ElementRecord]:
        normalized_query = query.strip().lower()
        matches: list[ElementRecord] = []

        for record in self.records_by_element.values():
            if normalized_query and normalized_query not in record.element.lower():
                if normalized_query not in record.description.lower():
                    continue
            matches.append(record)

        if kind is not None:
            _ = kind

        return matches[:top_k]


@dataclass(slots=True)
class VtdAssetRecord:
    asset_id: str
    asset_kind: str
    canonical_name: str
    display_name: str
    filename: str
    relative_path: str
    source_path: str
    group_path: str
    runtime_family: str
    aliases: list[str] = field(default_factory=list)
    country_codes: list[str] = field(default_factory=list)
    variant_tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class VtdNameRule:
    name: str
    rule_kind: str
    severity: str
    canonical_target: str
    asset_kind: str
    reason: str
    source_path: str
    scope: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class VtdKnowledgeBase:
    runtime_root: str = ""
    assets_by_id: dict[str, VtdAssetRecord] = field(default_factory=dict)
    assets_by_canonical_name: dict[str, list[VtdAssetRecord]] = field(default_factory=dict)
    rules_by_name: dict[str, VtdNameRule] = field(default_factory=dict)
    sources: list[SourceEntry] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class VtdAssetFamily:
    family_id: str
    canonical_key: str
    asset_kind: str
    preferred_variant_id: str
    variant_ids: list[str] = field(default_factory=list)
    country_scopes: list[str] = field(default_factory=list)
    semantic_tags: list[str] = field(default_factory=list)
    selection_policy: str = ""
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class VtdAssetVariant:
    variant_id: str
    family_id: str
    asset_id: str
    country_scope: str
    variant_tags: list[str] = field(default_factory=list)
    source_type: str = ""
    source_rank: int = 0
    referencable_as: list[str] = field(default_factory=list)
    usage_tags: list[str] = field(default_factory=list)
    quality_flags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class VtdNamePolicy:
    policy_id: str
    namespace: str
    asset_kind: str
    country_scope: str
    rule_kind: str
    severity: str
    match_mode: str
    canonical_target: str
    safe_name_strategy: str
    reason: str
    source_paths: list[str] = field(default_factory=list)


@dataclass(slots=True)
class VtdSemanticKnowledgeBase:
    families_by_id: dict[str, VtdAssetFamily] = field(default_factory=dict)
    variants_by_id: dict[str, VtdAssetVariant] = field(default_factory=dict)
    name_policies_by_id: dict[str, VtdNamePolicy] = field(default_factory=dict)
    sources: list[SourceEntry] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OscVtdBindingRule:
    binding_id: str
    element: str
    attribute: str
    parent_context: str
    binding_kind: str
    namespace: str
    asset_kind: str
    family_selector: dict[str, Any] = field(default_factory=dict)
    constraint_mode: str = ""
    selection_recipe: dict[str, Any] = field(default_factory=dict)
    fallback_policy: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OscVtdBridgeKnowledgeBase:
    rules_by_id: dict[str, OscVtdBindingRule] = field(default_factory=dict)
    bindings_by_field: dict[tuple[str, str], list[OscVtdBindingRule]] = field(
        default_factory=dict
    )
    sources: list[SourceEntry] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ScenarioIntent:
    parameters: list[dict[str, Any]] = field(default_factory=list)
    entities: list[dict[str, Any]] = field(default_factory=list)
    environment: dict[str, Any] = field(default_factory=dict)
    map_context: dict[str, Any] = field(default_factory=dict)
    init_actions: list[dict[str, Any]] = field(default_factory=list)
    story_actions: list[dict[str, Any]] = field(default_factory=list)
    triggers: list[dict[str, Any]] = field(default_factory=list)
    stop_conditions: list[dict[str, Any]] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)


__all__ = [
    "ElementRecord",
    "KnowledgeBase",
    "OscVtdBindingRule",
    "OscVtdBridgeKnowledgeBase",
    "ScenarioIntent",
    "SourceEntry",
    "ValidationError",
    "VtdAssetFamily",
    "VtdAssetRecord",
    "VtdAssetVariant",
    "VtdKnowledgeBase",
    "VtdNamePolicy",
    "VtdNameRule",
    "VtdSemanticKnowledgeBase",
]
