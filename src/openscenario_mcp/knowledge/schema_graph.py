from __future__ import annotations

from collections import deque
from typing import Any

from openscenario_mcp.models import ElementRecord, KnowledgeBase


def build_schema_subgraph(
    knowledge_base: KnowledgeBase,
    *,
    roots: list[str],
    depth: int = 2,
) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []
    required_paths: list[str] = []
    choice_points: list[dict[str, Any]] = []
    reference_bindings: list[dict[str, str]] = []
    assembly_order: list[str] = []

    queue = deque((root, 0) for root in roots if root in knowledge_base.records_by_element)
    seen: set[str] = set()
    while queue:
        element_name, level = queue.popleft()
        if element_name in seen:
            continue
        seen.add(element_name)
        record = knowledge_base.records_by_element[element_name]
        nodes[element_name] = _node_payload(record)
        assembly_order.append(element_name)

        for child in record.allowed_children:
            child_name = str(child.get("name", "")).strip()
            if not child_name:
                continue
            edges.append({"source": element_name, "target": child_name})
            cardinality = str(
                child.get("cardinality") or record.multiplicity.get(child_name, "")
            ).strip()
            if cardinality.startswith("1..") or cardinality == "1":
                required_paths.append(f"{element_name}->{child_name}")
            if level < depth and child_name in knowledge_base.records_by_element:
                queue.append((child_name, level + 1))

        if record.child_groups:
            for group in record.child_groups:
                choice_points.append(
                    {
                        "element": element_name,
                        "members": list(group.get("members", [])),
                        "cardinality": str(group.get("cardinality", "")).strip(),
                    }
                )

        for attribute in (*record.required_attributes, *record.optional_attributes):
            name = str(attribute.get("name", "")).strip()
            reference_kind = str(attribute.get("reference_kind", "")).strip()
            if not name or not reference_kind:
                continue
            reference_bindings.append(
                {
                    "element": element_name,
                    "attribute": name,
                    "reference_kind": reference_kind,
                }
            )

    return {
        "nodes": nodes,
        "edges": edges,
        "required_paths": required_paths,
        "choice_points": choice_points,
        "reference_bindings": reference_bindings,
        "assembly_order": assembly_order,
    }


def _node_payload(record: ElementRecord) -> dict[str, Any]:
    return {
        "element": record.element,
        "description": record.description,
        "parent_contexts": list(record.parent_contexts),
    }


__all__ = ["build_schema_subgraph"]
