from __future__ import annotations

from openscenario_mcp.tools.summarize_validation_repairs import (
    build_summarize_validation_repairs_tool,
)
from openscenario_mcp.validator.classifier import load_patterns


def test_summarize_validation_repairs_groups_cascaded_errors_under_one_root_cause() -> None:
    tool = build_summarize_validation_repairs_tool(load_patterns())

    result = tool(
        errors=[
            {"message": "Element 'Storyboard': Missing child element(s). Expected is ( Init )."},
            {"message": "Element 'StopTrigger': This element is not expected. Expected is ( Story )."},
        ]
    )

    assert result["root_causes"]
    assert result["repair_batches"][0]["minimal_patch_scope"] == "Storyboard"
    assert "add_required_children" in result["repair_batches"][0]["recommended_actions"]
