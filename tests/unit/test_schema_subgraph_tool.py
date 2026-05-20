from __future__ import annotations

from openscenario_mcp.models import ElementRecord, KnowledgeBase
from openscenario_mcp.tools.retrieve_schema_subgraph import (
    build_retrieve_schema_subgraph_tool,
)


def test_retrieve_schema_subgraph_returns_required_paths_and_choice_points() -> None:
    knowledge_base = KnowledgeBase(
        records_by_element={
            "Storyboard": ElementRecord(
                element="Storyboard",
                description="Scenario execution container.",
                allowed_children=[
                    {"name": "Init", "cardinality": "1..1"},
                    {"name": "Story", "cardinality": "0..*"},
                ],
                child_order=["Init", "Story"],
                multiplicity={"Init": "1..1", "Story": "0..*"},
                source_path="knowledge/raw/schema/OpenSCENARIO.xsd#L2206",
            ),
            "Story": ElementRecord(
                element="Story",
                description="Story container.",
                allowed_children=[{"name": "Act", "cardinality": "1..*"}],
                child_order=["Act"],
                multiplicity={"Act": "1..*"},
                source_path="knowledge/raw/schema/OpenSCENARIO.xsd#L2230",
            ),
            "LaneChangeAction": ElementRecord(
                element="LaneChangeAction",
                description="Lane change action.",
                parent_contexts=["LateralAction"],
                child_groups=[{"members": ["LaneChangeTarget"], "cardinality": "1..1"}],
                source_path="knowledge/raw/schema/OpenSCENARIO.xsd#L2600",
            ),
        }
    )

    tool = build_retrieve_schema_subgraph_tool(knowledge_base)
    result = tool(query="lane change", roots=["Storyboard", "LaneChangeAction"], depth=2)

    assert result["required_paths"]
    assert result["choice_points"]
    assert "Storyboard" in result["nodes"]
    assert "LaneChangeAction" in result["nodes"]
    assert result["assembly_order"][0] == "Storyboard"
