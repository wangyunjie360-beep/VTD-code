from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from openscenario_mcp.knowledge.search import search_spec_records
from openscenario_mcp.models import KnowledgeBase
from openscenario_mcp.validator.classifier import load_patterns


def build_retrieve_spec_tool(
    knowledge_base: KnowledgeBase,
    diagnostic_patterns: list[Mapping[str, Any]] | None = None,
):
    loaded_patterns = (
        list(load_patterns()) if diagnostic_patterns is None else list(diagnostic_patterns)
    )

    def retrieve_spec(
        query: str,
        kind: str | None = None,
        top_k: int = 5,
        parent_context: str | None = None,
    ) -> dict[str, Any]:
        return {
            "hits": search_spec_records(
                query,
                knowledge_base,
                loaded_patterns,
                kind=kind,
                top_k=top_k,
                parent_context=parent_context,
            )
        }

    return retrieve_spec
