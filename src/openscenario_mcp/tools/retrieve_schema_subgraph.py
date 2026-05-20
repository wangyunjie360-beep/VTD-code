from __future__ import annotations

from typing import Any

from openscenario_mcp.knowledge.schema_graph import build_schema_subgraph
from openscenario_mcp.knowledge.search import search_spec_records
from openscenario_mcp.models import KnowledgeBase


def build_retrieve_schema_subgraph_tool(knowledge_base: KnowledgeBase):
    def retrieve_schema_subgraph(
        query: str,
        intent: dict[str, Any] | None = None,
        roots: list[str] | None = None,
        parent_context: str | None = None,
        depth: int = 2,
    ) -> dict[str, Any]:
        if roots:
            focus_roots = [root for root in roots if root in knowledge_base.records_by_element]
        else:
            hits = search_spec_records(
                query,
                knowledge_base,
                kind="element",
                top_k=3,
                parent_context=parent_context,
            )
            focus_roots = [
                hit["title"]
                for hit in hits
                if hit["title"] in knowledge_base.records_by_element
            ]

        graph = build_schema_subgraph(knowledge_base, roots=focus_roots, depth=depth)
        return {
            "focus_blocks": focus_roots,
            "nodes": graph["nodes"],
            "edges": graph["edges"],
            "required_paths": graph["required_paths"],
            "choice_points": graph["choice_points"],
            "reference_bindings": graph["reference_bindings"],
            "assembly_order": graph["assembly_order"],
            "evidence": {
                "query": query,
                "parent_context": parent_context,
                "intent_present": intent is not None,
            },
        }

    return retrieve_schema_subgraph


__all__ = ["build_retrieve_schema_subgraph_tool"]
