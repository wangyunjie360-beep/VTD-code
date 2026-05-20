from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from openscenario_mcp.tools.diagnostics import build_explain_validation_errors_tool


def build_summarize_validation_repairs_tool(
    patterns: list[Mapping[str, Any]] | None = None,
):
    explain_validation_errors = build_explain_validation_errors_tool(patterns)

    def summarize_validation_repairs(
        errors: list[Mapping[str, Any] | object],
        xml: str | None = None,
        intent: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        diagnostics = explain_validation_errors(errors)["diagnostics"]
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for diagnostic in diagnostics:
            focus_element = diagnostic.get("repair_strategy", {}).get(
                "focus_element",
                diagnostic.get("element", "unknown"),
            )
            grouped[str(focus_element)].append(diagnostic)

        repair_batches: list[dict[str, Any]] = []
        root_causes: list[dict[str, Any]] = []
        for focus_element, batch_diagnostics in grouped.items():
            recommended_actions = _unique(
                action
                for diagnostic in batch_diagnostics
                for action in diagnostic.get("repair_strategy", {}).get(
                    "recommended_actions",
                    [],
                )
            )
            categories = _unique(
                diagnostic.get("category", "") for diagnostic in batch_diagnostics
            )
            repair_batches.append(
                {
                    "focus_element": focus_element,
                    "categories": categories,
                    "minimal_patch_scope": focus_element,
                    "recommended_actions": recommended_actions,
                    "diagnostics": batch_diagnostics,
                }
            )
            root_causes.append(
                {
                    "focus_element": focus_element,
                    "categories": categories,
                }
            )

        return {
            "root_causes": root_causes,
            "repair_batches": repair_batches,
            "minimal_patch_scope": repair_batches[0]["minimal_patch_scope"]
            if repair_batches
            else "",
            "followup_queries": [batch["focus_element"] for batch in repair_batches],
            "intent_risk": {
                "intent_present": intent is not None,
                "requires_recheck": bool(repair_batches),
                "xml_present": xml is not None,
            },
        }

    return summarize_validation_repairs


def _unique(values: Any) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        text = value.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


__all__ = ["build_summarize_validation_repairs_tool"]
