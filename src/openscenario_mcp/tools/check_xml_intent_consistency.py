from __future__ import annotations

from typing import Any

from openscenario_mcp.generation.intent_consistency import check_xml_intent_consistency


def build_check_xml_intent_consistency_tool():
    def tool(
        xml: str,
        intent: dict[str, Any],
        checklist: list[str] | None = None,
    ) -> dict[str, Any]:
        return check_xml_intent_consistency(xml, intent, checklist=checklist)

    return tool


__all__ = ["build_check_xml_intent_consistency_tool"]
