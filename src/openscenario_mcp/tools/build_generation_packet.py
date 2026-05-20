from __future__ import annotations

from typing import Any

from openscenario_mcp.generation.intent import normalize_scenario_intent
from openscenario_mcp.generation.reference_closure import build_reference_closure
from openscenario_mcp.runtime import Runtime


def build_generation_packet_tool(runtime: Runtime):
    def build_generation_packet(
        request: str,
        country_code: str | None = None,
        stage: str = "draft",
    ) -> dict[str, Any]:
        normalized = normalize_scenario_intent(request)
        intent = normalized["intent"]
        primary_elements = ["ScenarioObject", "Storyboard"]
        action_types = {
            str(action.get("type", "")).strip()
            for action in intent.get("story_actions", [])
            if isinstance(action, dict)
        }
        if "lane_change" in action_types:
            primary_elements.append("LaneChangeAction")
        if "speed_change" in action_types:
            primary_elements.append("SpeedAction")

        return {
            "intent": intent,
            "schema_plan": {
                "primary_elements": primary_elements,
                "reference_closure": build_reference_closure(intent),
            },
            "vtd_plan": {
                "country_code": country_code,
                "semantic_family_count": len(
                    runtime.vtd_semantic_knowledge_base.families_by_id
                ),
                "bridge_binding_count": len(
                    runtime.osc_vtd_bridge_knowledge_base.rules_by_id
                ),
            },
            "naming_plan": {
                "country_code": country_code,
                "namespaces": ["scenario_object", "runtime_asset"],
            },
            "validation_plan": {
                "stage": stage,
                "validate_tool": "validate_xml",
                "consistency_tool": "check_xml_intent_consistency",
                "repair_budget": 3,
            },
            "open_questions": normalized["open_questions"],
        }

    return build_generation_packet


__all__ = ["build_generation_packet_tool"]
