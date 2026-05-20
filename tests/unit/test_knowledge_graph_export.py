from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from openscenario_mcp.knowledge.graph_export import (
    export_knowledge_graph,
    export_visual_knowledge_graph,
)


def test_export_knowledge_graph_writes_contract_bundle(
    tmp_path: Path,
    sample_project_root: Path,
) -> None:
    _write_element_record(
        sample_project_root / "knowledge" / "structured" / "elements" / "Init.json",
        {
            "element": "Init",
            "description": "Initialization actions.",
            "content_model_kind": "sequence",
            "child_groups": [],
            "semantic_constraints": [],
            "contextual_variants": [],
            "parent_contexts": ["Storyboard"],
            "required_attributes": [],
            "optional_attributes": [],
            "allowed_children": [],
            "child_order": [],
            "multiplicity": {},
            "enum_constraints": {},
            "source_path": "knowledge/raw/schema/OpenSCENARIO.xsd#L2200",
        },
    )
    _write_element_record(
        sample_project_root / "knowledge" / "structured" / "elements" / "Story.json",
        {
            "element": "Story",
            "description": "Story container.",
            "content_model_kind": "sequence",
            "child_groups": [],
            "semantic_constraints": [],
            "contextual_variants": [],
            "parent_contexts": ["Storyboard"],
            "required_attributes": [
                {
                    "name": "name",
                    "type": "String",
                }
            ],
            "optional_attributes": [],
            "allowed_children": [],
            "child_order": [],
            "multiplicity": {},
            "enum_constraints": {},
            "source_path": "knowledge/raw/schema/OpenSCENARIO.xsd#L2230",
        },
    )
    _write_element_record(
        sample_project_root
        / "knowledge"
        / "structured"
        / "elements"
        / "TrafficSignalStateAction.json",
        {
            "element": "TrafficSignalStateAction",
            "description": "Sets a traffic signal state.",
            "content_model_kind": "sequence",
            "child_groups": [],
            "semantic_constraints": [],
            "contextual_variants": [],
            "parent_contexts": ["TrafficSignalAction"],
            "required_attributes": [
                {
                    "name": "name",
                    "type": "String",
                    "reference_kind": "traffic_signal",
                },
                {
                    "name": "state",
                    "type": "String",
                },
            ],
            "optional_attributes": [],
            "allowed_children": [],
            "child_order": [],
            "multiplicity": {},
            "enum_constraints": {
                "state": ["red", "yellow", "green"],
            },
            "source_path": "knowledge/raw/schema/OpenSCENARIO.xsd#L3310",
        },
    )
    _write_patterns(sample_project_root / "knowledge" / "diagnostics" / "patterns.json")
    _write_bridge_files(sample_project_root / "knowledge" / "structured" / "bridges" / "osc_vtd")

    output_root = tmp_path / "knowledge-graph"
    manifest = export_knowledge_graph(
        project_root=sample_project_root,
        output_root=output_root,
    )

    required_files = {
        "README.md",
        "manifest.json",
        "ontology.md",
        "nodes.jsonl",
        "edges.jsonl",
        "graph.graphml",
        "traceability.md",
        "sample-subgraph.json",
        "examples/query-examples.md",
    }
    exported_files = {
        path.relative_to(output_root).as_posix()
        for path in output_root.rglob("*")
        if path.is_file()
    }

    assert required_files <= exported_files
    assert manifest["node_counts"]["OSCElement"] >= 4
    assert manifest["node_counts"]["BridgeRule"] == 1
    assert manifest["node_counts"]["DiagnosticPattern"] >= 3
    assert manifest["edge_counts"]["HAS_CHILD"] >= 2
    assert manifest["edge_counts"]["REQUIRES_CHILD"] >= 1
    assert manifest["edge_counts"]["HAS_ATTRIBUTE"] >= 3
    assert manifest["edge_counts"]["REFERENCES"] >= 1
    assert manifest["edge_counts"]["HAS_VARIANT"] >= 1
    assert manifest["edge_counts"]["VARIANT_OF_ASSET"] >= 1
    assert manifest["edge_counts"]["APPLIES_TO_COUNTRY"] >= 1
    assert manifest["edge_counts"]["CONSTRAINS_NAME"] >= 1
    assert manifest["edge_counts"]["BINDS_TO_VTD"] >= 1
    assert manifest["edge_counts"]["HAS_REPAIR_PATTERN"] >= 1
    assert (
        manifest["traceability_summary"]["nodes_with_traceability"]
        == manifest["traceability_summary"]["node_total"]
    )
    assert (
        manifest["traceability_summary"]["edges_with_traceability"]
        == manifest["traceability_summary"]["edge_total"]
    )

    nodes = _load_jsonl(output_root / "nodes.jsonl")
    edges = _load_jsonl(output_root / "edges.jsonl")
    node_types = {node["type"] for node in nodes}
    edge_types = {edge["type"] for edge in edges}

    assert {
        "OSCElement",
        "OSCAttribute",
        "VTDAsset",
        "VTDAssetFamily",
        "VTDAssetVariant",
        "Country",
        "NamePolicy",
        "BridgeRule",
        "DiagnosticPattern",
    } <= node_types
    assert {
        "HAS_CHILD",
        "REQUIRES_CHILD",
        "HAS_ATTRIBUTE",
        "REFERENCES",
        "HAS_VARIANT",
        "VARIANT_OF_ASSET",
        "APPLIES_TO_COUNTRY",
        "CONSTRAINS_NAME",
        "BINDS_TO_VTD",
        "HAS_REPAIR_PATTERN",
    } <= edge_types
    assert any(
        edge["type"] == "HAS_CHILD"
        and edge["source"] == "osc-element:Storyboard"
        and edge["target"] == "osc-element:Story"
        for edge in edges
    )
    assert any(
        edge["type"] == "HAS_ATTRIBUTE"
        and edge["source"] == "osc-element:TrafficSignalStateAction"
        and edge["target"] == "osc-attribute:TrafficSignalStateAction.name"
        for edge in edges
    )
    assert any(
        edge["type"] == "REFERENCES"
        and edge["source"] == "osc-attribute:TrafficSignalStateAction.name"
        and edge["target"] == "reference-kind:traffic_signal"
        for edge in edges
    )

    graphml_tree = ET.parse(output_root / "graph.graphml")
    root = graphml_tree.getroot()
    assert root.tag.endswith("graphml")

    traceability = (output_root / "traceability.md").read_text(encoding="utf-8")
    assert "knowledge/raw/schema/OpenSCENARIO.xsd" in traceability
    assert "knowledge/structured/bridges/osc_vtd/field-bindings.jsonl" in traceability
    assert "knowledge/diagnostics/patterns.json" in traceability

    sample_subgraph = json.loads(
        (output_root / "sample-subgraph.json").read_text(encoding="utf-8")
    )
    assert sample_subgraph["focus_node"] == "osc-element:TrafficSignalStateAction"
    assert sample_subgraph["nodes"]
    assert sample_subgraph["edges"]


def test_export_visual_knowledge_graph_removes_name_policy_noise(
    tmp_path: Path,
    sample_project_root: Path,
) -> None:
    _write_element_record(
        sample_project_root
        / "knowledge"
        / "structured"
        / "elements"
        / "TrafficSignalStateAction.json",
        {
            "element": "TrafficSignalStateAction",
            "description": "Sets a traffic signal state.",
            "content_model_kind": "sequence",
            "child_groups": [],
            "semantic_constraints": [],
            "contextual_variants": [],
            "parent_contexts": ["TrafficSignalAction"],
            "required_attributes": [
                {
                    "name": "name",
                    "type": "String",
                    "reference_kind": "traffic_signal",
                }
            ],
            "optional_attributes": [],
            "allowed_children": [],
            "child_order": [],
            "multiplicity": {},
            "enum_constraints": {},
            "source_path": "knowledge/raw/schema/OpenSCENARIO.xsd#L3310",
        },
    )
    _write_patterns(sample_project_root / "knowledge" / "diagnostics" / "patterns.json")
    _write_bridge_files(sample_project_root / "knowledge" / "structured" / "bridges" / "osc_vtd")

    output_root = tmp_path / "visual-graph"
    manifest = export_visual_knowledge_graph(
        project_root=sample_project_root,
        output_root=output_root,
    )

    assert manifest["profile"] == "visual_core"
    assert "NamePolicy" not in manifest["node_counts"]
    assert "VTDAsset" not in manifest["node_counts"]
    assert "VTDAssetFamily" not in manifest["node_counts"]
    assert "VTDAssetVariant" not in manifest["node_counts"]
    assert manifest["node_counts"]["VTDAssetKind"] == 1
    assert "CONSTRAINS_NAME" not in manifest["edge_counts"]
    assert "HAS_VARIANT" not in manifest["edge_counts"]
    assert "VARIANT_OF_ASSET" not in manifest["edge_counts"]
    assert manifest["edge_counts"]["BINDS_TO_VTD_KIND"] == 1

    nodes = _load_jsonl(output_root / "nodes.jsonl")
    edges = _load_jsonl(output_root / "edges.jsonl")
    assert all(node["type"] != "NamePolicy" for node in nodes)
    assert all(edge["type"] != "CONSTRAINS_NAME" for edge in edges)
    assert any(
        node["type"] == "VTDAssetKind"
        and node["id"] == "vtd-asset-kind:signal"
        and node["properties"]["family_count"] >= 1
        for node in nodes
    )
    assert any(
        edge["type"] == "BINDS_TO_VTD_KIND"
        and edge["source"] == "bridge-rule:osc-vtd-binding:TrafficSignalStateAction:name"
        and edge["target"] == "vtd-asset-kind:signal"
        for edge in edges
    )

    graphml_tree = ET.parse(output_root / "graph.graphml")
    assert graphml_tree.getroot().tag.endswith("graphml")


def _write_element_record(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_patterns(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            [
                {
                    "category": "missing_required_child",
                    "regex": "^dummy$",
                    "fix_advice_template": "Add {required_child_description} under {element}.",
                },
                {
                    "category": "missing_required_attribute",
                    "regex": "^dummy$",
                    "fix_advice_template": "Add the required attribute '{attribute}' to {element}.",
                },
                {
                    "category": "wrong_child_order",
                    "regex": "^dummy$",
                    "fix_advice_template": "Move {element} after the required earlier child element(s): {expected_text}.",
                },
            ],
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_bridge_files(bridge_root: Path) -> None:
    bridge_root.mkdir(parents=True, exist_ok=True)
    (bridge_root / "field-bindings.jsonl").write_text(
        json.dumps(
            {
                "binding_id": "osc-vtd-binding:TrafficSignalStateAction:name",
                "element": "TrafficSignalStateAction",
                "attribute": "name",
                "parent_context": "TrafficSignalAction",
                "binding_kind": "asset_reference",
                "namespace": "runtime_asset",
                "asset_kind": "signal",
                "family_selector": {"semantic_tags": ["signal"]},
                "constraint_mode": "required",
                "selection_recipe": {
                    "prefer_country": True,
                    "selection_policy": "prefer_exact_country",
                },
                "fallback_policy": {
                    "on_missing": "surface_runtime_asset_warning",
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (bridge_root / "generation-policies.jsonl").write_text(
        json.dumps(
            {
                "policy_id": "osc-vtd-generation:runtime-assets",
                "binding_id": "osc-vtd-binding:TrafficSignalStateAction:name",
                "stage": "draft",
                "policy": {
                    "apply_to": ["TrafficSignalStateAction.name"],
                    "prefer_runtime_asset_resolution": True,
                },
                "source_paths": [
                    "knowledge/structured/bridges/osc_vtd/field-bindings.jsonl#osc-vtd-binding:TrafficSignalStateAction:name"
                ],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (bridge_root / "guidance-recipes.jsonl").write_text(
        json.dumps(
            {
                "recipe_id": "osc-vtd-guidance:traffic-signal-state-name",
                "binding_id": "osc-vtd-binding:TrafficSignalStateAction:name",
                "stage": "draft",
                "instruction": "Resolve the referenced traffic signal name to a VTD runtime signal candidate.",
                "expected_output": "Resolve to a runtime signal candidate.",
                "source_paths": [
                    "knowledge/structured/bridges/osc_vtd/field-bindings.jsonl#osc-vtd-binding:TrafficSignalStateAction:name"
                ],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
