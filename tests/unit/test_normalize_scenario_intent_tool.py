from __future__ import annotations

from openscenario_mcp.tools.normalize_scenario_intent import (
    build_normalize_scenario_intent_tool,
)


def test_normalize_scenario_intent_returns_partial_ir_with_unresolved_slots() -> None:
    tool = build_normalize_scenario_intent_tool()

    result = tool(request="一辆主车在高速上触发变道", locale="zh-CN")

    assert result["intent"]["entities"][0]["name"] == "ego"
    assert result["intent"]["map_context"]["road_type"] == "highway"
    assert any(
        action["type"] == "lane_change" for action in result["intent"]["story_actions"]
    )
    assert result["unresolved_slots"] == ["trigger_detail", "target_lane"]
    assert "lane_change" in result["intent_checklist"]


def test_normalize_scenario_intent_preserves_draft_assumptions() -> None:
    tool = build_normalize_scenario_intent_tool()

    result = tool(
        request="ego vehicle on highway",
        draft_assumptions=["use default local map"],
    )

    assert "use default local map" in result["assumptions"]
    assert "use default local map" in result["intent"]["assumptions"]
