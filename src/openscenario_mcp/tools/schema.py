from __future__ import annotations

from dataclasses import asdict
from typing import Any

from openscenario_mcp.generation.strategy import build_element_strategy
from openscenario_mcp.models import KnowledgeBase


def build_get_element_schema_tool(knowledge_base: KnowledgeBase):
    def get_element_schema(
        element: str,
        parent_context: str | None = None,
    ) -> dict[str, Any]:
        try:
            record = knowledge_base.records_by_element[element]
        except KeyError as exc:
            raise ValueError(f"Unknown element: {element}") from exc
        payload = asdict(record)
        payload["strategy"] = build_element_strategy(record, parent_context=parent_context)
        return payload

    return get_element_schema
