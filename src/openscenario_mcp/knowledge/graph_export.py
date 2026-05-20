from __future__ import annotations

import json
import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import xml.etree.ElementTree as ET

from openscenario_mcp.config import get_project_root
from openscenario_mcp.knowledge.bridge_loader import load_osc_vtd_bridge
from openscenario_mcp.knowledge.loader import load_element_record
from openscenario_mcp.knowledge.vtd_loader import (
    load_vtd_semantic_snapshot,
    load_vtd_snapshot,
)
from openscenario_mcp.knowledge.vtd_semantic import build_vtd_semantic_knowledge_base
from openscenario_mcp.models import (
    ElementRecord,
    OscVtdBridgeKnowledgeBase,
    VtdAssetFamily,
    VtdAssetRecord,
    VtdAssetVariant,
    VtdKnowledgeBase,
    VtdNamePolicy,
    VtdSemanticKnowledgeBase,
)

_ELEMENTS_RELATIVE_PATH = Path("knowledge") / "structured" / "elements"
_VTD_RELATIVE_PATH = Path("knowledge") / "structured" / "vtd"
_SEMANTIC_RELATIVE_PATH = _VTD_RELATIVE_PATH / "semantic"
_BRIDGE_RELATIVE_PATH = Path("knowledge") / "structured" / "bridges" / "osc_vtd"
_PATTERNS_RELATIVE_PATH = Path("knowledge") / "diagnostics" / "patterns.json"

_SAMPLE_SUBGRAPH_TARGET = "osc-element:TrafficSignalStateAction"
_SAMPLE_SUBGRAPH_FALLBACK = "osc-element:ScenarioObject"

_NODE_TYPE_DESCRIPTIONS = {
    "OSCElement": "Structured OpenSCENARIO element record derived from the local XSD.",
    "OSCAttribute": "Attribute slot on an OpenSCENARIO element, including required/reference metadata.",
    "VTDAsset": "Concrete VTD runtime asset from the repository snapshot.",
    "VTDAssetFamily": "Semantic family that groups VTD assets by canonical name and asset kind.",
    "VTDAssetKind": "Visualization aggregate that groups VTD semantic families by asset kind.",
    "VTDAssetVariant": "Country-scoped or source-scoped semantic variant of a VTD asset family.",
    "Country": "Normalized country scope from the VTD taxonomy.",
    "NamePolicy": "Name collision / safe-name rule derived from VTD runtime naming constraints.",
    "BridgeRule": "OSC-to-VTD field binding rule used during generation and repair guidance.",
    "DiagnosticPattern": "Validator diagnostic classification pattern used for repair guidance.",
    "ReferenceKind": "Reference target category carried by OpenSCENARIO attributes.",
}

_EDGE_TYPE_DESCRIPTIONS = {
    "HAS_CHILD": "Element allows a child element.",
    "REQUIRES_CHILD": "Element requires the target child element or choice member.",
    "HAS_ATTRIBUTE": "Element exposes an attribute node.",
    "REFERENCES": "Attribute points at a named reference kind.",
    "HAS_VARIANT": "VTD family exposes a semantic variant.",
    "VARIANT_OF_ASSET": "Semantic variant resolves to a concrete VTD asset record.",
    "APPLIES_TO_COUNTRY": "Node is scoped to a normalized country node.",
    "CONSTRAINS_NAME": "Name policy protects or constrains a runtime asset family or asset.",
    "BINDS_TO_VTD": "Bridge rule binds an OSC field to VTD semantic families.",
    "BINDS_TO_VTD_KIND": "Bridge rule binds to an aggregated VTD asset kind for visualization.",
    "HAS_REPAIR_PATTERN": "Element is associated with a validator repair pattern.",
}

_VISUAL_CORE_NODE_TYPES = frozenset(
    {
        "OSCElement",
        "OSCAttribute",
        "ReferenceKind",
        "BridgeRule",
        "DiagnosticPattern",
        "Country",
    }
)
_VISUAL_CORE_EDGE_TYPES = frozenset(
    {
        "HAS_CHILD",
        "REQUIRES_CHILD",
        "HAS_ATTRIBUTE",
        "REFERENCES",
        "HAS_REPAIR_PATTERN",
    }
)


@dataclass(slots=True)
class GraphNode:
    id: str
    type: str
    label: str
    source_paths: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GraphEdge:
    id: str
    type: str
    source: str
    target: str
    source_paths: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)


class GraphBuilder:
    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[tuple[str, str, str], GraphEdge] = {}

    def add_node(
        self,
        node_id: str,
        node_type: str,
        label: str,
        *,
        source_paths: Iterable[str] | None = None,
        properties: dict[str, Any] | None = None,
    ) -> None:
        normalized_sources = _dedupe_strings(source_paths or ())
        normalized_properties = dict(properties or {})
        existing = self._nodes.get(node_id)
        if existing is None:
            self._nodes[node_id] = GraphNode(
                id=node_id,
                type=node_type,
                label=label,
                source_paths=normalized_sources,
                properties=normalized_properties,
            )
            return

        if existing.type != node_type:
            raise ValueError(
                f"Node id '{node_id}' reused with conflicting types: "
                f"{existing.type} vs {node_type}."
            )
        existing.label = existing.label or label
        existing.source_paths = _dedupe_strings([*existing.source_paths, *normalized_sources])
        existing.properties = _merge_values(existing.properties, normalized_properties)

    def add_edge(
        self,
        edge_type: str,
        source: str,
        target: str,
        *,
        source_paths: Iterable[str] | None = None,
        properties: dict[str, Any] | None = None,
    ) -> None:
        edge_key = (edge_type, source, target)
        normalized_sources = _dedupe_strings(source_paths or ())
        normalized_properties = dict(properties or {})
        existing = self._edges.get(edge_key)
        if existing is None:
            self._edges[edge_key] = GraphEdge(
                id=_edge_id(edge_type, source, target),
                type=edge_type,
                source=source,
                target=target,
                source_paths=normalized_sources,
                properties=normalized_properties,
            )
            return

        existing.source_paths = _dedupe_strings([*existing.source_paths, *normalized_sources])
        existing.properties = _merge_values(existing.properties, normalized_properties)

    def nodes(self) -> list[GraphNode]:
        return sorted(
            self._nodes.values(),
            key=lambda node: (node.type, node.label.casefold(), node.id),
        )

    def edges(self) -> list[GraphEdge]:
        return sorted(
            self._edges.values(),
            key=lambda edge: (edge.type, edge.source, edge.target),
        )


def export_knowledge_graph(
    *,
    project_root: str | Path | None = None,
    output_root: str | Path | None = None,
) -> dict[str, Any]:
    resolved_project_root = (
        Path(project_root).resolve() if project_root is not None else get_project_root()
    )
    resolved_output_root = (
        Path(output_root).resolve()
        if output_root is not None
        else resolved_project_root / "knowledge" / "graph_export"
    )

    nodes, edges = _build_graph_records(
        project_root=resolved_project_root,
        output_root=resolved_output_root,
    )
    focus_node = _choose_focus_node(nodes)
    sample_subgraph = _build_sample_subgraph(nodes, edges, focus_node=focus_node)
    manifest = _build_manifest(
        project_root=resolved_project_root,
        output_root=resolved_output_root,
        nodes=nodes,
        edges=edges,
        focus_node=focus_node,
    )

    _write_bundle(
        output_root=resolved_output_root,
        project_root=resolved_project_root,
        nodes=nodes,
        edges=edges,
        manifest=manifest,
        focus_node=focus_node,
        sample_subgraph=sample_subgraph,
        profile="full",
    )
    return manifest


def export_visual_knowledge_graph(
    *,
    project_root: str | Path | None = None,
    output_root: str | Path | None = None,
) -> dict[str, Any]:
    resolved_project_root = (
        Path(project_root).resolve() if project_root is not None else get_project_root()
    )
    resolved_output_root = (
        Path(output_root).resolve()
        if output_root is not None
        else resolved_project_root / "knowledge" / "graph_visual"
    )

    full_nodes, full_edges = _build_graph_records(
        project_root=resolved_project_root,
        output_root=resolved_output_root,
    )
    nodes, edges, visual_summary = _build_visual_core_records(full_nodes, full_edges)
    focus_node = _choose_focus_node(nodes)
    sample_subgraph = _build_sample_subgraph(nodes, edges, focus_node=focus_node)
    manifest = _build_manifest(
        project_root=resolved_project_root,
        output_root=resolved_output_root,
        nodes=nodes,
        edges=edges,
        focus_node=focus_node,
    )
    manifest["profile"] = "visual_core"
    manifest["visual_summary"] = visual_summary

    _write_bundle(
        output_root=resolved_output_root,
        project_root=resolved_project_root,
        nodes=nodes,
        edges=edges,
        manifest=manifest,
        focus_node=focus_node,
        sample_subgraph=sample_subgraph,
        profile="visual_core",
    )
    return manifest


def _build_graph_records(
    *,
    project_root: Path,
    output_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    element_records = _load_element_records(project_root / _ELEMENTS_RELATIVE_PATH)
    vtd_knowledge_base = load_vtd_snapshot(project_root / _VTD_RELATIVE_PATH)
    vtd_semantic_knowledge_base = _load_vtd_semantic_knowledge_base(
        project_root,
        vtd_knowledge_base,
    )
    bridge_knowledge_base = _load_bridge_knowledge_base(project_root)
    diagnostic_patterns = _load_diagnostic_patterns(project_root / _PATTERNS_RELATIVE_PATH)

    builder = GraphBuilder()
    context = _GraphContext(
        project_root=project_root,
        output_root=output_root,
        elements=element_records,
        vtd_knowledge_base=vtd_knowledge_base,
        vtd_semantic_knowledge_base=vtd_semantic_knowledge_base,
        bridge_knowledge_base=bridge_knowledge_base,
        diagnostic_patterns=diagnostic_patterns,
    )
    _populate_graph(builder, context)
    nodes = [_serialize_node(node) for node in builder.nodes()]
    edges = [_serialize_edge(edge) for edge in builder.edges()]
    return nodes, edges


@dataclass(slots=True)
class _GraphContext:
    project_root: Path
    output_root: Path
    elements: dict[str, ElementRecord]
    vtd_knowledge_base: VtdKnowledgeBase
    vtd_semantic_knowledge_base: VtdSemanticKnowledgeBase
    bridge_knowledge_base: OscVtdBridgeKnowledgeBase
    diagnostic_patterns: list[dict[str, Any]]


def _populate_graph(builder: GraphBuilder, context: _GraphContext) -> None:
    variant_provenance = _index_variant_provenance(
        context.vtd_semantic_knowledge_base.metadata.get("source_provenance", [])
    )
    family_index = _index_families_by_kind_and_name(
        context.vtd_semantic_knowledge_base.families_by_id.values()
    )
    asset_index = _index_assets_by_kind_and_name(context.vtd_knowledge_base.assets_by_id.values())
    bridge_policies = _index_bridge_records(
        context.bridge_knowledge_base.metadata.get("generation_policies", []),
        key_name="binding_id",
    )
    guidance_recipes = _index_bridge_records(
        context.bridge_knowledge_base.metadata.get("guidance_recipes", []),
        key_name="binding_id",
    )

    for record in context.elements.values():
        element_id = _element_node_id(record.element)
        builder.add_node(
            element_id,
            "OSCElement",
            record.element,
            source_paths=_split_source_paths(record.source_path),
            properties={
                "description": record.description,
                "content_model_kind": record.content_model_kind,
                "parent_contexts": list(record.parent_contexts),
                "child_order": list(record.child_order),
                "semantic_constraints": list(record.semantic_constraints),
                "contextual_variants": list(record.contextual_variants),
            },
        )

        required_attribute_names = {
            _attribute_name(attribute)
            for attribute in record.required_attributes
            if _attribute_name(attribute)
        }
        for attribute in (*record.required_attributes, *record.optional_attributes):
            attribute_name = _attribute_name(attribute)
            if not attribute_name:
                continue
            attribute_id = _attribute_node_id(record.element, attribute_name)
            enum_values = list(record.enum_constraints.get(attribute_name, []))
            builder.add_node(
                attribute_id,
                "OSCAttribute",
                f"{record.element}.{attribute_name}",
                source_paths=_split_source_paths(record.source_path),
                properties={
                    "element": record.element,
                    "attribute": attribute_name,
                    "required": attribute_name in required_attribute_names,
                    "type": str(attribute.get("type", "")).strip(),
                    "reference_kind": str(attribute.get("reference_kind", "")).strip(),
                    "enum_values": enum_values,
                },
            )
            builder.add_edge(
                "HAS_ATTRIBUTE",
                element_id,
                attribute_id,
                source_paths=_split_source_paths(record.source_path),
                properties={"required": attribute_name in required_attribute_names},
            )

            reference_kind = str(attribute.get("reference_kind", "")).strip()
            if reference_kind:
                reference_node_id = _reference_kind_node_id(reference_kind)
                builder.add_node(
                    reference_node_id,
                    "ReferenceKind",
                    reference_kind,
                    source_paths=_split_source_paths(record.source_path),
                    properties={"reference_kind": reference_kind},
                )
                builder.add_edge(
                    "REFERENCES",
                    attribute_id,
                    reference_node_id,
                    source_paths=_split_source_paths(record.source_path),
                    properties={"reference_kind": reference_kind},
                )

        for child in record.allowed_children:
            child_name = str(child.get("name", "")).strip()
            if not child_name:
                continue
            child_id = _element_node_id(child_name)
            if child_name not in context.elements:
                builder.add_node(
                    child_id,
                    "OSCElement",
                    child_name,
                    source_paths=_split_source_paths(record.source_path),
                    properties={"stub": True},
                )
            cardinality = str(
                child.get("cardinality") or record.multiplicity.get(child_name, "")
            ).strip()
            builder.add_edge(
                "HAS_CHILD",
                element_id,
                child_id,
                source_paths=_split_source_paths(record.source_path),
                properties={"cardinality": cardinality},
            )
            if _is_required_cardinality(cardinality):
                builder.add_edge(
                    "REQUIRES_CHILD",
                    element_id,
                    child_id,
                    source_paths=_split_source_paths(record.source_path),
                    properties={"cardinality": cardinality},
                )

        for pattern in context.diagnostic_patterns:
            if _record_matches_pattern(record, pattern):
                category = str(pattern.get("category", "")).strip()
                if not category:
                    continue
                builder.add_edge(
                    "HAS_REPAIR_PATTERN",
                    element_id,
                    _diagnostic_pattern_node_id(category),
                    source_paths=[
                        *_split_source_paths(record.source_path),
                        _diagnostic_pattern_source_path(category),
                    ],
                    properties={"category": category},
                )

    for asset in context.vtd_knowledge_base.assets_by_id.values():
        asset_id = _asset_node_id(asset.asset_id)
        builder.add_node(
            asset_id,
            "VTDAsset",
            asset.canonical_name,
            source_paths=_asset_source_paths(asset),
            properties={
                "asset_id": asset.asset_id,
                "asset_kind": asset.asset_kind,
                "canonical_name": asset.canonical_name,
                "display_name": asset.display_name,
                "filename": asset.filename,
                "relative_path": asset.relative_path,
                "group_path": asset.group_path,
                "runtime_family": asset.runtime_family,
                "aliases": list(asset.aliases),
                "country_codes": list(asset.country_codes),
                "variant_tags": list(asset.variant_tags),
                "metadata": dict(asset.metadata),
            },
        )
        for country_code in asset.country_codes:
            builder.add_node(
                _country_node_id(country_code),
                "Country",
                country_code,
                source_paths=[_country_source_path(country_code)],
                properties=_country_payload(
                    country_code,
                    context.vtd_knowledge_base.metadata.get("country_taxonomy", {}),
                ),
            )
            builder.add_edge(
                "APPLIES_TO_COUNTRY",
                asset_id,
                _country_node_id(country_code),
                source_paths=_asset_source_paths(asset),
                properties={"country_code": country_code},
            )

    for family in context.vtd_semantic_knowledge_base.families_by_id.values():
        family_id = _family_node_id(family.family_id)
        builder.add_node(
            family_id,
            "VTDAssetFamily",
            family.canonical_key,
            source_paths=[_family_source_path(family.family_id)],
            properties={
                "family_id": family.family_id,
                "canonical_key": family.canonical_key,
                "asset_kind": family.asset_kind,
                "preferred_variant_id": family.preferred_variant_id,
                "variant_ids": list(family.variant_ids),
                "country_scopes": list(family.country_scopes),
                "semantic_tags": list(family.semantic_tags),
                "selection_policy": family.selection_policy,
                "notes": list(family.notes),
            },
        )
        for country_scope in family.country_scopes:
            for country_code in _split_country_scope(country_scope):
                builder.add_node(
                    _country_node_id(country_code),
                    "Country",
                    country_code,
                    source_paths=[_country_source_path(country_code)],
                    properties=_country_payload(
                        country_code,
                        context.vtd_knowledge_base.metadata.get("country_taxonomy", {}),
                    ),
                )
                builder.add_edge(
                    "APPLIES_TO_COUNTRY",
                    family_id,
                    _country_node_id(country_code),
                    source_paths=[_family_source_path(family.family_id)],
                    properties={"country_code": country_code},
                )

    for variant in context.vtd_semantic_knowledge_base.variants_by_id.values():
        variant_id = _variant_node_id(variant.variant_id)
        provenance = variant_provenance.get(variant.variant_id, {})
        variant_sources = _variant_source_paths(variant, provenance)
        builder.add_node(
            variant_id,
            "VTDAssetVariant",
            variant.variant_id,
            source_paths=variant_sources,
            properties={
                "variant_id": variant.variant_id,
                "family_id": variant.family_id,
                "asset_id": variant.asset_id,
                "country_scope": variant.country_scope,
                "variant_tags": list(variant.variant_tags),
                "source_type": variant.source_type,
                "source_rank": variant.source_rank,
                "referencable_as": list(variant.referencable_as),
                "usage_tags": list(variant.usage_tags),
                "quality_flags": list(variant.quality_flags),
            },
        )
        builder.add_edge(
            "HAS_VARIANT",
            _family_node_id(variant.family_id),
            variant_id,
            source_paths=variant_sources,
            properties={"preferred": variant.variant_id == context.vtd_semantic_knowledge_base.families_by_id[variant.family_id].preferred_variant_id},
        )
        builder.add_edge(
            "VARIANT_OF_ASSET",
            variant_id,
            _asset_node_id(variant.asset_id),
            source_paths=variant_sources,
            properties={"asset_id": variant.asset_id},
        )
        for country_code in _split_country_scope(variant.country_scope):
            builder.add_node(
                _country_node_id(country_code),
                "Country",
                country_code,
                source_paths=[_country_source_path(country_code)],
                properties=_country_payload(
                    country_code,
                    context.vtd_knowledge_base.metadata.get("country_taxonomy", {}),
                ),
            )
            builder.add_edge(
                "APPLIES_TO_COUNTRY",
                variant_id,
                _country_node_id(country_code),
                source_paths=variant_sources,
                properties={"country_code": country_code},
            )

    for country_code, payload in _iter_countries(
        context.vtd_knowledge_base.metadata.get("country_taxonomy", {})
    ):
        builder.add_node(
            _country_node_id(country_code),
            "Country",
            country_code,
            source_paths=[_country_source_path(country_code)],
            properties=payload,
        )

    for raw_policy in context.vtd_knowledge_base.metadata.get("name_policies", []):
        policy = _build_name_policy(raw_policy)
        if not policy.policy_id:
            continue
        policy_id = _name_policy_node_id(policy.policy_id)
        builder.add_node(
            policy_id,
            "NamePolicy",
            policy.policy_id,
            source_paths=list(policy.source_paths),
            properties={
                "policy_id": policy.policy_id,
                "namespace": policy.namespace,
                "asset_kind": policy.asset_kind,
                "country_scope": policy.country_scope,
                "rule_kind": policy.rule_kind,
                "severity": policy.severity,
                "match_mode": policy.match_mode,
                "canonical_target": policy.canonical_target,
                "safe_name_strategy": policy.safe_name_strategy,
                "reason": policy.reason,
            },
        )
        for country_code in _split_country_scope(policy.country_scope):
            builder.add_node(
                _country_node_id(country_code),
                "Country",
                country_code,
                source_paths=[_country_source_path(country_code)],
                properties=_country_payload(
                    country_code,
                    context.vtd_knowledge_base.metadata.get("country_taxonomy", {}),
                ),
            )
            builder.add_edge(
                "APPLIES_TO_COUNTRY",
                policy_id,
                _country_node_id(country_code),
                source_paths=list(policy.source_paths),
                properties={"country_code": country_code},
            )

        for family in family_index.get((policy.asset_kind, policy.canonical_target), []):
            builder.add_edge(
                "CONSTRAINS_NAME",
                policy_id,
                _family_node_id(family.family_id),
                source_paths=list(policy.source_paths),
                properties={"canonical_target": policy.canonical_target},
            )
        for asset in asset_index.get((policy.asset_kind, policy.canonical_target), []):
            builder.add_edge(
                "CONSTRAINS_NAME",
                policy_id,
                _asset_node_id(asset.asset_id),
                source_paths=list(policy.source_paths),
                properties={"canonical_target": policy.canonical_target},
            )

    for rule in context.bridge_knowledge_base.rules_by_id.values():
        if not rule.binding_id:
            continue
        rule_id = _bridge_rule_node_id(rule.binding_id)
        linked_policies = bridge_policies.get(rule.binding_id, [])
        linked_guidance = guidance_recipes.get(rule.binding_id, [])
        bridge_sources = _bridge_rule_source_paths(rule.binding_id, linked_policies, linked_guidance)
        builder.add_node(
            rule_id,
            "BridgeRule",
            rule.binding_id,
            source_paths=bridge_sources,
            properties={
                "binding_id": rule.binding_id,
                "element": rule.element,
                "attribute": rule.attribute,
                "parent_context": rule.parent_context,
                "binding_kind": rule.binding_kind,
                "namespace": rule.namespace,
                "asset_kind": rule.asset_kind,
                "family_selector": dict(rule.family_selector),
                "constraint_mode": rule.constraint_mode,
                "selection_recipe": dict(rule.selection_recipe),
                "fallback_policy": dict(rule.fallback_policy),
                "generation_policy_ids": [
                    str(policy.get("policy_id", "")).strip()
                    for policy in linked_policies
                    if str(policy.get("policy_id", "")).strip()
                ],
                "guidance_recipe_ids": [
                    str(recipe.get("recipe_id", "")).strip()
                    for recipe in linked_guidance
                    if str(recipe.get("recipe_id", "")).strip()
                ],
            },
        )
        builder.add_node(
            _attribute_node_id(rule.element, rule.attribute),
            "OSCAttribute",
            f"{rule.element}.{rule.attribute}",
        )
        builder.add_edge(
            "HAS_ATTRIBUTE",
            _element_node_id(rule.element),
            _attribute_node_id(rule.element, rule.attribute),
            source_paths=bridge_sources,
            properties={"bridge_inferred": True},
        )

        matched_families = _match_bridge_families(
            rule,
            context.vtd_semantic_knowledge_base.families_by_id.values(),
        )
        for family in matched_families:
            builder.add_edge(
                "BINDS_TO_VTD",
                rule_id,
                _family_node_id(family.family_id),
                source_paths=bridge_sources,
                properties={
                    "asset_kind": rule.asset_kind,
                    "binding_kind": rule.binding_kind,
                    "namespace": rule.namespace,
                },
            )

    for pattern in context.diagnostic_patterns:
        category = str(pattern.get("category", "")).strip()
        if not category:
            continue
        builder.add_node(
            _diagnostic_pattern_node_id(category),
            "DiagnosticPattern",
            category,
            source_paths=[_diagnostic_pattern_source_path(category)],
            properties={
                "category": category,
                "regex": str(pattern.get("regex", "")).strip(),
                "fix_advice_template": str(
                    pattern.get("fix_advice_template", "")
                ).strip(),
            },
        )


def _load_element_records(elements_dir: Path) -> dict[str, ElementRecord]:
    if not elements_dir.is_dir():
        raise FileNotFoundError(f"Structured element directory not found at {elements_dir}.")
    records: dict[str, ElementRecord] = {}
    for path in sorted(elements_dir.glob("*.json")):
        record = load_element_record(path)
        records[record.element] = record
    if not records:
        raise FileNotFoundError(f"No structured element records found in {elements_dir}.")
    return records


def _load_vtd_semantic_knowledge_base(
    project_root: Path,
    vtd_knowledge_base: VtdKnowledgeBase,
) -> VtdSemanticKnowledgeBase:
    semantic_root = project_root / _SEMANTIC_RELATIVE_PATH
    if semantic_root.is_dir():
        required = (
            semantic_root / "asset-families.jsonl",
            semantic_root / "asset-variants.jsonl",
            semantic_root / "source-provenance.jsonl",
        )
        if all(path.is_file() for path in required):
            return load_vtd_semantic_snapshot(project_root / _VTD_RELATIVE_PATH)

    semantic_knowledge_base, provenance = build_vtd_semantic_knowledge_base(vtd_knowledge_base)
    semantic_knowledge_base.metadata = {
        **semantic_knowledge_base.metadata,
        "source_provenance": provenance,
        "root": semantic_root.as_posix(),
        "exists": semantic_root.is_dir(),
        "status": "derived",
    }
    return semantic_knowledge_base


def _load_bridge_knowledge_base(project_root: Path) -> OscVtdBridgeKnowledgeBase:
    bridge_root = project_root / _BRIDGE_RELATIVE_PATH
    required = (
        bridge_root / "field-bindings.jsonl",
        bridge_root / "generation-policies.jsonl",
        bridge_root / "guidance-recipes.jsonl",
    )
    if bridge_root.is_dir() and all(path.is_file() for path in required):
        return load_osc_vtd_bridge(bridge_root)
    return OscVtdBridgeKnowledgeBase(
        sources=[],
        metadata={"root": bridge_root.as_posix(), "exists": bridge_root.is_dir(), "status": "placeholder"},
    )


def _load_diagnostic_patterns(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Diagnostic pattern file must be a JSON array.")
    return [entry for entry in payload if isinstance(entry, dict)]


def _record_matches_pattern(record: ElementRecord, pattern: dict[str, Any]) -> bool:
    category = str(pattern.get("category", "")).strip()
    if category == "missing_required_child":
        return any(
            _is_required_cardinality(
                str(
                    child.get("cardinality")
                    or record.multiplicity.get(str(child.get("name", "")).strip(), "")
                ).strip()
            )
            for child in record.allowed_children
            if str(child.get("name", "")).strip()
        )
    if category == "missing_required_attribute":
        return bool(record.required_attributes)
    if category == "wrong_child_order":
        return len(record.child_order) > 1
    if category == "unexpected_element":
        return bool(record.allowed_children)
    if category == "invalid_attribute":
        return bool(record.required_attributes or record.optional_attributes)
    if category == "invalid_enum_value":
        return any(record.enum_constraints.values())
    if category == "namespace_or_root_issue":
        return record.element in {"OpenSCENARIO", "OpenScenario"}
    return False


def _iter_countries(country_taxonomy: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    raw_countries = country_taxonomy.get("countries", {})
    if not isinstance(raw_countries, dict):
        return []
    countries: list[tuple[str, dict[str, Any]]] = []
    for country_code, payload in raw_countries.items():
        if not isinstance(country_code, str) or not isinstance(payload, dict):
            continue
        countries.append((country_code, dict(payload)))
    return countries


def _country_payload(country_code: str, country_taxonomy: dict[str, Any]) -> dict[str, Any]:
    raw_countries = country_taxonomy.get("countries", {})
    if not isinstance(raw_countries, dict):
        return {"canonical_code": country_code}
    payload = raw_countries.get(country_code, {})
    if not isinstance(payload, dict):
        return {"canonical_code": country_code}
    return dict(payload)


def _build_name_policy(raw_policy: dict[str, Any]) -> VtdNamePolicy:
    return VtdNamePolicy(
        policy_id=str(raw_policy.get("policy_id", "")).strip(),
        namespace=str(raw_policy.get("namespace", "")).strip(),
        asset_kind=str(raw_policy.get("asset_kind", "")).strip(),
        country_scope=str(raw_policy.get("country_scope", "")).strip(),
        rule_kind=str(raw_policy.get("rule_kind", "")).strip(),
        severity=str(raw_policy.get("severity", "")).strip(),
        match_mode=str(raw_policy.get("match_mode", "")).strip(),
        canonical_target=str(raw_policy.get("canonical_target", "")).strip(),
        safe_name_strategy=str(raw_policy.get("safe_name_strategy", "")).strip(),
        reason=str(raw_policy.get("reason", "")).strip(),
        source_paths=_dedupe_strings(raw_policy.get("source_paths", [])),
    )


def _index_variant_provenance(
    records: Any,
) -> dict[str, dict[str, Any]]:
    if not isinstance(records, list):
        return {}
    provenance_by_id: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        variant_id = str(record.get("variant_id", "")).strip()
        if not variant_id:
            continue
        provenance_by_id[variant_id] = record
    return provenance_by_id


def _index_families_by_kind_and_name(
    families: Iterable[VtdAssetFamily],
) -> dict[tuple[str, str], list[VtdAssetFamily]]:
    indexed: dict[tuple[str, str], list[VtdAssetFamily]] = defaultdict(list)
    for family in families:
        indexed[(family.asset_kind, family.canonical_key)].append(family)
    return indexed


def _index_assets_by_kind_and_name(
    assets: Iterable[VtdAssetRecord],
) -> dict[tuple[str, str], list[VtdAssetRecord]]:
    indexed: dict[tuple[str, str], list[VtdAssetRecord]] = defaultdict(list)
    for asset in assets:
        indexed[(asset.asset_kind, asset.canonical_name)].append(asset)
    return indexed


def _index_bridge_records(
    records: Any,
    *,
    key_name: str,
) -> dict[str, list[dict[str, Any]]]:
    indexed: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not isinstance(records, list):
        return indexed
    for record in records:
        if not isinstance(record, dict):
            continue
        key_value = str(record.get(key_name, "")).strip()
        if key_value:
            indexed[key_value].append(record)
    return indexed


def _match_bridge_families(
    rule: Any,
    families: Iterable[VtdAssetFamily],
) -> list[VtdAssetFamily]:
    candidates = [family for family in families if family.asset_kind == rule.asset_kind]
    requested_tags = {
        str(tag).strip()
        for tag in rule.family_selector.get("semantic_tags", [])
        if str(tag).strip()
    }
    if not requested_tags:
        return candidates

    matched = [
        family
        for family in candidates
        if requested_tags & set(family.semantic_tags)
    ]
    return matched or candidates


def _bridge_rule_source_paths(
    binding_id: str,
    linked_policies: list[dict[str, Any]],
    linked_guidance: list[dict[str, Any]],
) -> list[str]:
    source_paths = [
        f"{_BRIDGE_RELATIVE_PATH.as_posix()}/field-bindings.jsonl#{binding_id}"
    ]
    for record in (*linked_policies, *linked_guidance):
        source_paths.extend(
            path
            for path in record.get("source_paths", [])
            if isinstance(path, str) and path.strip()
        )
    return _dedupe_strings(source_paths)


def _variant_source_paths(
    variant: VtdAssetVariant,
    provenance: dict[str, Any],
) -> list[str]:
    source_paths = [_variant_source_path(variant.variant_id)]
    direct_source = provenance.get("source_path")
    if isinstance(direct_source, str) and direct_source.strip():
        source_paths.append(direct_source)
    merged_source_paths = provenance.get("merged_source_paths", [])
    if isinstance(merged_source_paths, list):
        source_paths.extend(
            path
            for path in merged_source_paths
            if isinstance(path, str) and path.strip()
        )
    return _dedupe_strings(source_paths)


def _asset_source_paths(asset: VtdAssetRecord) -> list[str]:
    source_paths = [asset.source_path]
    merged = asset.metadata.get("merged_source_paths", [])
    if isinstance(merged, list):
        source_paths.extend(
            path for path in merged if isinstance(path, str) and path.strip()
        )
    return _dedupe_strings(source_paths)


def _build_manifest(
    *,
    project_root: Path,
    output_root: Path,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    focus_node: str,
) -> dict[str, Any]:
    node_counts = _count_types(nodes, key="type")
    edge_counts = _count_types(edges, key="type")
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "project_root": project_root.as_posix(),
        "output_root": _project_relative_path(project_root, output_root),
        "node_total": len(nodes),
        "edge_total": len(edges),
        "node_counts": node_counts,
        "edge_counts": edge_counts,
        "focus_node": focus_node,
        "artifacts": {
            "manifest": "manifest.json",
            "readme": "README.md",
            "ontology": "ontology.md",
            "nodes": "nodes.jsonl",
            "edges": "edges.jsonl",
            "graphml": "graph.graphml",
            "traceability": "traceability.md",
            "sample_subgraph": "sample-subgraph.json",
            "query_examples": "examples/query-examples.md",
        },
        "traceability_summary": _traceability_summary(nodes, edges),
    }


def _write_bundle(
    *,
    output_root: Path,
    project_root: Path,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    manifest: dict[str, Any],
    focus_node: str,
    sample_subgraph: dict[str, Any],
    profile: str,
) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "examples").mkdir(parents=True, exist_ok=True)

    _write_jsonl(output_root / "nodes.jsonl", nodes)
    _write_jsonl(output_root / "edges.jsonl", edges)
    _write_json(output_root / "manifest.json", manifest)
    _write_json(output_root / "sample-subgraph.json", sample_subgraph)
    (output_root / "README.md").write_text(
        _build_readme(project_root, manifest),
        encoding="utf-8",
    )
    (output_root / "ontology.md").write_text(
        _build_ontology_markdown(),
        encoding="utf-8",
    )
    (output_root / "traceability.md").write_text(
        _build_traceability_markdown(nodes, edges),
        encoding="utf-8",
    )
    (output_root / "examples" / "query-examples.md").write_text(
        _build_query_examples(focus_node, profile=profile),
        encoding="utf-8",
    )
    _write_graphml(output_root / "graph.graphml", nodes, edges)


def _build_readme(project_root: Path, manifest: dict[str, Any]) -> str:
    profile = str(manifest.get("profile", "full"))
    title = (
        "# OpenSCENARIO Visual Knowledge Graph Export"
        if profile == "visual_core"
        else "# OpenSCENARIO Knowledge Graph Export"
    )
    description = (
        [
            "This bundle exports a visualization-friendly OpenSCENARIO + VTD graph view.",
            "Name-policy nodes, concrete VTD assets, variants, and dense name-constraint",
            "edges are removed; VTD family bindings are aggregated by asset kind.",
        ]
        if profile == "visual_core"
        else [
            "This bundle exports the repository-local OpenSCENARIO + VTD knowledge base",
            "into line-oriented graph records plus GraphML for downstream analysis.",
        ]
    )
    command = (
        "py -3.14 scripts/export_visual_knowledge_graph.py"
        if profile == "visual_core"
        else "py -3.14 scripts/export_knowledge_graph.py"
    )
    return "\n".join(
        [
            title,
            "",
            *description,
            "",
            f"- Project root: `{project_root.as_posix()}`",
            f"- Nodes: `{manifest['node_total']}`",
            f"- Edges: `{manifest['edge_total']}`",
            f"- Focus node: `{manifest['focus_node']}`",
            "",
            "Regenerate with:",
            "",
            "```bash",
            command,
            "```",
            "",
        ]
    )


def _build_ontology_markdown() -> str:
    lines = ["# Ontology", "", "## Node Types", ""]
    lines.extend(
        f"- `{node_type}`: {description}"
        for node_type, description in _NODE_TYPE_DESCRIPTIONS.items()
    )
    lines.extend(["", "## Edge Types", ""])
    lines.extend(
        f"- `{edge_type}`: {description}"
        for edge_type, description in _EDGE_TYPE_DESCRIPTIONS.items()
    )
    lines.append("")
    return "\n".join(lines)


def _build_traceability_markdown(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> str:
    traceability = _traceability_summary(nodes, edges)
    lines = [
        "# Traceability",
        "",
        f"- Nodes with source paths: `{traceability['nodes_with_traceability']}` / `{traceability['node_total']}`",
        f"- Edges with source paths: `{traceability['edges_with_traceability']}` / `{traceability['edge_total']}`",
        f"- Distinct source files: `{len(traceability['source_files'])}`",
        "",
        "| Source file | Node refs | Edge refs |",
        "| --- | ---: | ---: |",
    ]
    for entry in traceability["source_files"]:
        lines.append(
            f"| `{entry['source_file']}` | {entry['node_refs']} | {entry['edge_refs']} |"
        )
    lines.append("")
    return "\n".join(lines)


def _build_query_examples(focus_node: str, *, profile: str) -> str:
    bridge_query = (
        [
            "## Follow a bridge rule into aggregated VTD asset kinds",
            "",
            "```cypher",
            "MATCH (rule:BridgeRule)-[:BINDS_TO_VTD_KIND]->(kind:VTDAssetKind)",
            "WHERE rule.label = 'osc-vtd-binding:TrafficSignalStateAction:name'",
            "RETURN kind.label, kind.family_count;",
            "```",
        ]
        if profile == "visual_core"
        else [
            "## Follow a bridge rule into VTD semantic families",
            "",
            "```cypher",
            "MATCH (rule:BridgeRule)-[:BINDS_TO_VTD]->(family:VTDAssetFamily)",
            "WHERE rule.label = 'osc-vtd-binding:TrafficSignalStateAction:name'",
            "RETURN family.label, family.asset_kind;",
            "```",
        ]
    )
    return "\n".join(
        [
            "# Query Examples",
            "",
            "## Find required children for a schema element",
            "",
            "```cypher",
            "MATCH (element {id: 'osc-element:Storyboard'})-[:REQUIRES_CHILD]->(child)",
            "RETURN child.id, child.label;",
            "```",
            "",
            *bridge_query,
            "",
            "## Inspect a sample focused neighborhood",
            "",
            "```json",
            json.dumps({"focus_node": focus_node}, ensure_ascii=False, sort_keys=True),
            "```",
            "",
        ]
    )


def _write_graphml(path: Path, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> None:
    namespace = "http://graphml.graphdrawing.org/xmlns"
    ET.register_namespace("", namespace)
    graphml = ET.Element(f"{{{namespace}}}graphml")
    key_specs = [
        ("node_type", "node", "string"),
        ("node_label", "node", "string"),
        ("node_properties", "node", "string"),
        ("node_source_paths", "node", "string"),
        ("edge_type", "edge", "string"),
        ("edge_properties", "edge", "string"),
        ("edge_source_paths", "edge", "string"),
    ]
    for index, (attr_name, scope, attr_type) in enumerate(key_specs, start=1):
        ET.SubElement(
            graphml,
            f"{{{namespace}}}key",
            id=f"d{index}",
            **{"for": scope, "attr.name": attr_name, "attr.type": attr_type},
        )

    graph = ET.SubElement(graphml, f"{{{namespace}}}graph", edgedefault="directed")
    for node in nodes:
        node_element = ET.SubElement(graph, f"{{{namespace}}}node", id=node["id"])
        _write_graphml_data(node_element, "d1", node["type"], namespace)
        _write_graphml_data(node_element, "d2", node["label"], namespace)
        _write_graphml_data(
            node_element,
            "d3",
            json.dumps(node["properties"], ensure_ascii=False, sort_keys=True),
            namespace,
        )
        _write_graphml_data(
            node_element,
            "d4",
            json.dumps(node["source_paths"], ensure_ascii=False, sort_keys=True),
            namespace,
        )

    for edge in edges:
        edge_element = ET.SubElement(
            graph,
            f"{{{namespace}}}edge",
            id=edge["id"],
            source=edge["source"],
            target=edge["target"],
        )
        _write_graphml_data(edge_element, "d5", edge["type"], namespace)
        _write_graphml_data(
            edge_element,
            "d6",
            json.dumps(edge["properties"], ensure_ascii=False, sort_keys=True),
            namespace,
        )
        _write_graphml_data(
            edge_element,
            "d7",
            json.dumps(edge["source_paths"], ensure_ascii=False, sort_keys=True),
            namespace,
        )

    path.write_text(
        ET.tostring(graphml, encoding="unicode"),
        encoding="utf-8",
    )


def _write_graphml_data(
    parent: ET.Element,
    key: str,
    value: str,
    namespace: str,
) -> None:
    element = ET.SubElement(parent, f"{{{namespace}}}data", key=key)
    element.text = value


def _build_visual_core_records(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    full_node_counts = _count_types(nodes, key="type")
    full_edge_counts = _count_types(edges, key="type")
    node_by_id = {
        str(node.get("id", "")).strip(): node
        for node in nodes
        if str(node.get("id", "")).strip()
    }

    visual_nodes: dict[str, dict[str, Any]] = {
        node["id"]: node
        for node in nodes
        if node.get("type") in _VISUAL_CORE_NODE_TYPES
    }
    visual_edges: dict[tuple[str, str, str], dict[str, Any]] = {}

    for edge in edges:
        edge_type = str(edge.get("type", "")).strip()
        source = str(edge.get("source", "")).strip()
        target = str(edge.get("target", "")).strip()
        if edge_type not in _VISUAL_CORE_EDGE_TYPES:
            continue
        if source not in visual_nodes or target not in visual_nodes:
            continue
        visual_edges[(edge_type, source, target)] = edge

    aggregated_edges: dict[tuple[str, str], dict[str, Any]] = {}
    aggregated_families_by_kind: dict[str, set[str]] = defaultdict(set)
    aggregated_sources_by_kind: dict[str, list[str]] = defaultdict(list)

    for edge in edges:
        if edge.get("type") != "BINDS_TO_VTD":
            continue
        source = str(edge.get("source", "")).strip()
        target = str(edge.get("target", "")).strip()
        if source not in visual_nodes:
            continue

        family_node = node_by_id.get(target, {})
        edge_properties = edge.get("properties", {})
        family_properties = family_node.get("properties", {})
        if not isinstance(edge_properties, dict):
            edge_properties = {}
        if not isinstance(family_properties, dict):
            family_properties = {}

        asset_kind = str(
            edge_properties.get("asset_kind")
            or family_properties.get("asset_kind")
            or "unknown"
        ).strip()
        if not asset_kind:
            asset_kind = "unknown"
        asset_kind_id = _asset_kind_node_id(asset_kind)

        aggregated_families_by_kind[asset_kind_id].add(target)
        aggregated_sources_by_kind[asset_kind_id].extend(_source_paths_from(family_node))
        aggregated_sources_by_kind[asset_kind_id].extend(_source_paths_from(edge))

        aggregate_key = (source, asset_kind_id)
        aggregate_edge = aggregated_edges.setdefault(
            aggregate_key,
            {
                "id": _edge_id("BINDS_TO_VTD_KIND", source, asset_kind_id),
                "type": "BINDS_TO_VTD_KIND",
                "source": source,
                "target": asset_kind_id,
                "source_paths": [],
                "properties": {
                    "aggregated": True,
                    "asset_kind": asset_kind,
                    "family_count": 0,
                    "original_edge_type": "BINDS_TO_VTD",
                },
            },
        )
        aggregate_edge["source_paths"] = _dedupe_strings(
            [
                *aggregate_edge["source_paths"],
                *_source_paths_from(edge),
                *_source_paths_from(family_node),
            ]
        )
        families = aggregate_edge["properties"].setdefault("family_ids", [])
        families.append(target)

    for asset_kind_id, family_ids in aggregated_families_by_kind.items():
        asset_kind = asset_kind_id.removeprefix("vtd-asset-kind:")
        visual_nodes[asset_kind_id] = {
            "id": asset_kind_id,
            "type": "VTDAssetKind",
            "label": asset_kind,
            "source_paths": _dedupe_strings(aggregated_sources_by_kind[asset_kind_id]),
            "properties": {
                "asset_kind": asset_kind,
                "family_count": len(family_ids),
                "aggregated": True,
                "aggregated_from": "VTDAssetFamily",
            },
        }

    for aggregate_edge in aggregated_edges.values():
        family_ids = sorted(set(aggregate_edge["properties"].get("family_ids", [])))
        aggregate_edge["properties"]["family_count"] = len(family_ids)
        aggregate_edge["properties"]["family_ids"] = family_ids[:20]
        if len(family_ids) > 20:
            aggregate_edge["properties"]["family_ids_truncated"] = True
        visual_edges[
            (
                aggregate_edge["type"],
                aggregate_edge["source"],
                aggregate_edge["target"],
            )
        ] = aggregate_edge

    visual_node_list = sorted(
        visual_nodes.values(),
        key=lambda node: (
            str(node.get("type", "")),
            str(node.get("label", "")).casefold(),
            str(node.get("id", "")),
        ),
    )
    visual_edge_list = sorted(
        visual_edges.values(),
        key=lambda edge: (
            str(edge.get("type", "")),
            str(edge.get("source", "")),
            str(edge.get("target", "")),
        ),
    )
    visual_summary = {
        "description": (
            "Visualization profile that removes name-policy and concrete VTD detail "
            "nodes, then aggregates bridge-to-family bindings by VTD asset kind."
        ),
        "included_node_types": sorted(_VISUAL_CORE_NODE_TYPES | {"VTDAssetKind"}),
        "included_edge_types": sorted(_VISUAL_CORE_EDGE_TYPES | {"BINDS_TO_VTD_KIND"}),
        "removed_node_counts": _subtract_counts(
            full_node_counts,
            _count_types(visual_node_list, key="type"),
        ),
        "removed_edge_counts": _subtract_counts(
            full_edge_counts,
            _count_types(visual_edge_list, key="type"),
        ),
        "aggregated": {
            "VTDAssetFamily": "VTDAssetKind",
            "BINDS_TO_VTD": "BINDS_TO_VTD_KIND",
        },
    }
    return visual_node_list, visual_edge_list, visual_summary


def _build_sample_subgraph(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    focus_node: str,
) -> dict[str, Any]:
    focus_and_neighbors = {focus_node}
    for edge in edges:
        if edge["source"] == focus_node:
            focus_and_neighbors.add(edge["target"])
        if edge["target"] == focus_node:
            focus_and_neighbors.add(edge["source"])

    expanded_ids = set(focus_and_neighbors)
    for edge in edges:
        if edge["source"] in focus_and_neighbors or edge["target"] in focus_and_neighbors:
            expanded_ids.add(edge["source"])
            expanded_ids.add(edge["target"])

    sub_nodes = [node for node in nodes if node["id"] in expanded_ids]
    sub_edges = [
        edge
        for edge in edges
        if edge["source"] in expanded_ids and edge["target"] in expanded_ids
    ]
    return {
        "focus_node": focus_node,
        "nodes": sub_nodes,
        "edges": sub_edges,
    }


def _choose_focus_node(nodes: list[dict[str, Any]]) -> str:
    node_ids = {node["id"] for node in nodes}
    for candidate in (_SAMPLE_SUBGRAPH_TARGET, _SAMPLE_SUBGRAPH_FALLBACK):
        if candidate in node_ids:
            return candidate
    for node in nodes:
        if node["type"] == "OSCElement":
            return node["id"]
    return nodes[0]["id"] if nodes else ""


def _traceability_summary(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[str, Any]:
    summary: dict[str, dict[str, int]] = defaultdict(lambda: {"node_refs": 0, "edge_refs": 0})
    nodes_with_traceability = 0
    edges_with_traceability = 0

    for node in nodes:
        source_paths = node.get("source_paths", [])
        if isinstance(source_paths, list) and source_paths:
            nodes_with_traceability += 1
        for source_path in source_paths:
            if not isinstance(source_path, str) or not source_path.strip():
                continue
            summary[_source_file_only(source_path)]["node_refs"] += 1

    for edge in edges:
        source_paths = edge.get("source_paths", [])
        if isinstance(source_paths, list) and source_paths:
            edges_with_traceability += 1
        for source_path in source_paths:
            if not isinstance(source_path, str) or not source_path.strip():
                continue
            summary[_source_file_only(source_path)]["edge_refs"] += 1

    return {
        "node_total": len(nodes),
        "edge_total": len(edges),
        "nodes_with_traceability": nodes_with_traceability,
        "edges_with_traceability": edges_with_traceability,
        "source_files": [
            {
                "source_file": source_file,
                "node_refs": counts["node_refs"],
                "edge_refs": counts["edge_refs"],
            }
            for source_file, counts in sorted(summary.items())
        ],
    }


def _count_types(records: list[dict[str, Any]], *, key: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for record in records:
        record_type = str(record.get(key, "")).strip()
        if record_type:
            counts[record_type] += 1
    return dict(sorted(counts.items()))


def _subtract_counts(
    minuend: dict[str, int],
    subtrahend: dict[str, int],
) -> dict[str, int]:
    return {
        key: count - subtrahend.get(key, 0)
        for key, count in sorted(minuend.items())
        if count - subtrahend.get(key, 0) > 0
    }


def _source_paths_from(record: dict[str, Any]) -> list[str]:
    source_paths = record.get("source_paths", [])
    if not isinstance(source_paths, list):
        return []
    return _dedupe_strings(
        path for path in source_paths if isinstance(path, str) and path.strip()
    )


def _serialize_node(node: GraphNode) -> dict[str, Any]:
    return {
        "id": node.id,
        "type": node.type,
        "label": node.label,
        "source_paths": node.source_paths,
        "properties": node.properties,
    }


def _serialize_edge(edge: GraphEdge) -> dict[str, Any]:
    return {
        "id": edge.id,
        "type": edge.type,
        "source": edge.source,
        "target": edge.target,
        "source_paths": edge.source_paths,
        "properties": edge.properties,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def _write_jsonl(path: Path, payloads: Iterable[dict[str, Any]]) -> None:
    lines = [
        json.dumps(payload, ensure_ascii=False, sort_keys=True)
        for payload in payloads
    ]
    path.write_text(("\n".join(lines) + "\n") if lines else "", encoding="utf-8")


def _merge_values(existing: Any, incoming: Any) -> Any:
    if isinstance(existing, dict) and isinstance(incoming, dict):
        merged = dict(existing)
        for key, value in incoming.items():
            if key not in merged:
                merged[key] = value
            else:
                merged[key] = _merge_values(merged[key], value)
        return merged
    if isinstance(existing, list) and isinstance(incoming, list):
        return _dedupe_any([*existing, *incoming])
    if _is_empty(existing) and not _is_empty(incoming):
        return incoming
    return existing


def _dedupe_strings(values: Iterable[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        text = value.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def _dedupe_any(values: Iterable[Any]) -> list[Any]:
    ordered: list[Any] = []
    seen: set[str] = set()
    for value in values:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if encoded in seen:
            continue
        seen.add(encoded)
        ordered.append(value)
    return ordered


def _split_source_paths(source_path: str) -> list[str]:
    return [part.strip() for part in source_path.split(";") if part.strip()]


def _split_country_scope(country_scope: str) -> list[str]:
    return [part.strip() for part in country_scope.split("+") if part.strip()]


def _attribute_name(attribute: Any) -> str:
    if not isinstance(attribute, dict):
        return ""
    return str(attribute.get("name", "")).strip()


def _is_required_cardinality(cardinality: str) -> bool:
    return cardinality == "1" or cardinality.startswith("1..")


def _is_empty(value: Any) -> bool:
    return value in ("", None, [], {})


def _source_file_only(source_path: str) -> str:
    return source_path.split("#", maxsplit=1)[0]


def _project_relative_path(project_root: Path, path: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return path.as_posix()


def _edge_id(edge_type: str, source: str, target: str) -> str:
    seed = f"{edge_type}\x1f{source}\x1f{target}".encode("utf-8")
    token = hashlib.sha1(seed).hexdigest()[:12]
    return f"edge:{edge_type.lower()}:{token}"


def _element_node_id(element: str) -> str:
    return f"osc-element:{element}"


def _attribute_node_id(element: str, attribute: str) -> str:
    return f"osc-attribute:{element}.{attribute}"


def _asset_node_id(asset_id: str) -> str:
    return f"vtd-asset:{asset_id}"


def _family_node_id(family_id: str) -> str:
    return f"vtd-family:{family_id}"


def _asset_kind_node_id(asset_kind: str) -> str:
    return f"vtd-asset-kind:{_slug(asset_kind)}"


def _slug(value: str) -> str:
    slug = "".join(
        character.lower() if character.isalnum() else "-"
        for character in value.strip()
    )
    return "-".join(part for part in slug.split("-") if part) or "unknown"


def _variant_node_id(variant_id: str) -> str:
    return f"vtd-variant:{variant_id}"


def _country_node_id(country_code: str) -> str:
    return f"country:{country_code}"


def _name_policy_node_id(policy_id: str) -> str:
    return f"name-policy:{policy_id}"


def _bridge_rule_node_id(binding_id: str) -> str:
    return f"bridge-rule:{binding_id}"


def _diagnostic_pattern_node_id(category: str) -> str:
    return f"diagnostic-pattern:{category}"


def _reference_kind_node_id(reference_kind: str) -> str:
    return f"reference-kind:{reference_kind}"


def _family_source_path(family_id: str) -> str:
    return f"{_SEMANTIC_RELATIVE_PATH.as_posix()}/asset-families.jsonl#{family_id}"


def _variant_source_path(variant_id: str) -> str:
    return f"{_SEMANTIC_RELATIVE_PATH.as_posix()}/asset-variants.jsonl#{variant_id}"


def _country_source_path(country_code: str) -> str:
    return f"{_SEMANTIC_RELATIVE_PATH.as_posix()}/country-taxonomy.json#{country_code}"


def _diagnostic_pattern_source_path(category: str) -> str:
    return f"{_PATTERNS_RELATIVE_PATH.as_posix()}#{category}"


__all__ = ["export_knowledge_graph"]
