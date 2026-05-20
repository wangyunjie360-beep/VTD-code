from __future__ import annotations

from typing import Any

from openscenario_mcp.generation.intent import normalize_scenario_intent


def build_normalize_scenario_intent_tool():
    def tool(
        request: str,
        locale: str | None = None,
        draft_assumptions: list[str] | None = None,
    ) -> dict[str, Any]:
        return normalize_scenario_intent(
            request,
            locale=locale,
            draft_assumptions=draft_assumptions,
        )

    return tool


__all__ = ["build_normalize_scenario_intent_tool"]
