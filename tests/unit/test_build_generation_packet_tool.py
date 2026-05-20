from __future__ import annotations

from openscenario_mcp.runtime import build_runtime_for_tests
from openscenario_mcp.tools.build_generation_packet import (
    build_generation_packet_tool,
)


def test_build_generation_packet_composes_intent_schema_vtd_and_validation_plans() -> None:
    runtime = build_runtime_for_tests()
    tool = build_generation_packet_tool(runtime)

    result = tool(
        request="生成一个主车触发变道的 VTD 场景",
        country_code="CN",
        stage="draft",
    )

    assert result["intent"]["entities"][0]["name"] == "ego"
    assert "LaneChangeAction" in result["schema_plan"]["primary_elements"]
    assert result["vtd_plan"]["country_code"] == "CN"
    assert result["validation_plan"]["stage"] == "draft"
    assert "naming_plan" in result
    assert "open_questions" in result
