from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from openscenario_mcp.models import KnowledgeBase
from openscenario_mcp.tools.diagnostics import build_explain_validation_errors_tool
from openscenario_mcp.tools.retrieve_spec import build_retrieve_spec_tool
from openscenario_mcp.tools.schema import build_get_element_schema_tool
from openscenario_mcp.tools.summarize_validation_repairs import (
    build_summarize_validation_repairs_tool,
)


def build_xml_guidance_tool(
    knowledge_base: KnowledgeBase,
    diagnostic_patterns: list[Mapping[str, Any]] | None = None,
):
    retrieve_spec = build_retrieve_spec_tool(knowledge_base, diagnostic_patterns)
    get_element_schema = build_get_element_schema_tool(knowledge_base)
    explain_validation_errors = build_explain_validation_errors_tool(diagnostic_patterns)
    summarize_validation_repairs = build_summarize_validation_repairs_tool(
        diagnostic_patterns
    )

    def build_xml_guidance(
        query: str,
        element: str,
        parent_context: str | None = None,
        top_k: int = 3,
        errors: list[Mapping[str, Any] | object] | None = None,
    ) -> dict[str, Any]:
        retrieval = retrieve_spec(
            query=query,
            kind=None,
            top_k=top_k,
            parent_context=parent_context,
        )
        element_schema = get_element_schema(
            element=element,
            parent_context=parent_context,
        )

        draft_checklist = _dedupe_strings(
            item
            for hit in retrieval["hits"]
            for item in hit.get("strategy_summary", [])
        )

        repair_diagnostics: list[dict[str, Any]] = []
        repair_actions: list[str] = []
        repair_batches: list[dict[str, Any]] = []
        if errors:
            repair_diagnostics = explain_validation_errors(errors)["diagnostics"]
            repair_summary = summarize_validation_repairs(errors)
            repair_batches = repair_summary["repair_batches"]
            repair_actions = _dedupe_strings(
                action
                for batch in repair_batches
                for action in batch.get("recommended_actions", [])
            )

        return {
            "query": query,
            "element": element,
            "parent_context": parent_context,
            "retrieval_hits": retrieval["hits"],
            "element_schema": element_schema,
            "draft_checklist": draft_checklist,
            "repair_diagnostics": repair_diagnostics,
            "repair_batches": repair_batches,
            "repair_actions": repair_actions,
        }

    return build_xml_guidance


def _dedupe_strings(values: Any) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        text = value.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        deduped.append(text)
    return deduped


__all__ = ["build_xml_guidance_tool"]
