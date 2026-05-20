from __future__ import annotations

from collections.abc import Mapping

import openscenario_mcp.tools.retrieve_spec as retrieve_spec_module
from openscenario_mcp.models import ElementRecord, KnowledgeBase
from openscenario_mcp.tools.guidance import build_xml_guidance_tool


def _build_knowledge_base() -> KnowledgeBase:
    return KnowledgeBase(
        records_by_element={
            "SetAction": ElementRecord(
                element="SetAction",
                description="Set-action leaf shared by parameter and variable action paths.",
                content_model_kind="choice",
                child_groups=[{"members": ["Value", "Expression"], "cardinality": "1..1"}],
                contextual_variants=[
                    {
                        "parent_context": "ParameterAction",
                        "type_ref": "ParameterSetAction",
                        "deprecated": True,
                    },
                    {
                        "parent_context": "VariableAction",
                        "type_ref": "VariableSetAction",
                        "deprecated": False,
                    },
                ],
                parent_contexts=["ParameterAction", "VariableAction"],
                required_attributes=[
                    {
                        "name": "variableRef",
                        "type": "String",
                        "reference_kind": "variable",
                    }
                ],
                optional_attributes=[],
                allowed_children=[],
                child_order=[],
                multiplicity={},
                enum_constraints={},
                source_path="knowledge/raw/schema/OpenSCENARIO.xsd#L1744",
            ),
            "Storyboard": ElementRecord(
                element="Storyboard",
                description=(
                    "Scenario execution container. Init is required, Story entries are "
                    "optional and repeatable, and StopTrigger is optional with a strict "
                    "child order of Init, Story, then StopTrigger."
                ),
                parent_contexts=["OpenSCENARIO"],
                required_attributes=[],
                optional_attributes=[],
                allowed_children=[
                    {"name": "Init", "cardinality": "1..1"},
                    {"name": "Story", "cardinality": "0..*"},
                    {"name": "StopTrigger", "cardinality": "0..1"},
                ],
                child_order=["Init", "Story", "StopTrigger"],
                multiplicity={
                    "Init": "1..1",
                    "Story": "0..*",
                    "StopTrigger": "0..1",
                },
                enum_constraints={},
                source_path="knowledge/raw/schema/OpenSCENARIO.xsd#L2206",
            ),
            "VariableAction": ElementRecord(
                element="VariableAction",
                description="Variable action wrapper.",
                parent_contexts=["GlobalAction"],
                content_model_kind="choice",
                child_groups=[{"members": ["SetAction", "ModifyAction"], "cardinality": "1..1"}],
                required_attributes=[
                    {
                        "name": "variableRef",
                        "type": "String",
                        "reference_kind": "variable",
                    }
                ],
                optional_attributes=[],
                allowed_children=[],
                child_order=[],
                multiplicity={},
                enum_constraints={},
                source_path="knowledge/raw/schema/OpenSCENARIO.xsd#L2558",
            ),
        }
    )


def _build_diagnostic_patterns() -> list[dict[str, str]]:
    return [
        {
            "category": "missing_required_child",
            "regex": "^Element '(?P<element>[^']+)': Missing child element",
            "fix_advice_template": "Add {required_child_description} under {element}.",
        },
        {
            "category": "missing_required_attribute",
            "regex": "^Element '(?P<element>[^']+)': The attribute '(?P<attribute>[^']+)' is required but missing\\.$",
            "fix_advice_template": "Add the required attribute '{attribute}' to {element}.",
        },
    ]


def test_build_xml_guidance_composes_retrieval_and_schema_strategy() -> None:
    tool = build_xml_guidance_tool(_build_knowledge_base(), _build_diagnostic_patterns())

    result = tool(
        query="set action",
        element="SetAction",
        parent_context="VariableAction",
        top_k=1,
    )

    assert result["query"] == "set action"
    assert result["element"] == "SetAction"
    assert result["parent_context"] == "VariableAction"
    assert len(result["retrieval_hits"]) == 1
    assert result["retrieval_hits"][0]["strategy_summary"] == [
        "Use variant for VariableAction: VariableSetAction.",
        "Select exactly one branch from: Value, Expression.",
        "Wire required variable reference: variableRef.",
    ]
    assert result["element_schema"]["strategy"]["variant_resolution"]["resolved_variant"] == {
        "parent_context": "VariableAction",
        "type_ref": "VariableSetAction",
        "deprecated": False,
    }
    assert result["draft_checklist"] == [
        "Use variant for VariableAction: VariableSetAction.",
        "Select exactly one branch from: Value, Expression.",
        "Wire required variable reference: variableRef.",
    ]
    assert result["repair_diagnostics"] == []
    assert result["repair_actions"] == []


def test_build_xml_guidance_composes_repair_guidance_from_errors() -> None:
    tool = build_xml_guidance_tool(_build_knowledge_base(), _build_diagnostic_patterns())

    result = tool(
        query="variable action",
        element="VariableAction",
        errors=[
            {
                "message": (
                    "Element 'VariableAction': The attribute 'variableRef' is required but "
                    "missing."
                )
            }
        ],
    )

    assert result["repair_diagnostics"][0]["category"] == "missing_required_attribute"
    assert result["repair_diagnostics"][0]["repair_strategy"]["recommended_actions"] == [
        "add_required_references"
    ]
    assert result["repair_actions"] == ["add_required_references"]
    assert result["repair_batches"][0]["minimal_patch_scope"] == "VariableAction"
    assert result["repair_batches"][0]["recommended_actions"] == [
        "add_required_references"
    ]


def test_build_xml_guidance_loads_default_patterns_when_none() -> None:
    loaded_patterns: list[Mapping[str, str]] = [
        {
            "category": "missing_required_child",
            "regex": "^Element '(?P<element>[^']+)': Missing child element",
            "fix_advice_template": "Add {required_child_description} under {element}.",
        }
    ]
    original_load_patterns = retrieve_spec_module.load_patterns
    retrieve_spec_module.load_patterns = lambda: loaded_patterns.copy()
    try:
        tool = build_xml_guidance_tool(_build_knowledge_base())
    finally:
        retrieve_spec_module.load_patterns = original_load_patterns

    result = tool(query="storyboard", element="Storyboard", top_k=1)
    assert result["retrieval_hits"][0]["title"] == "Storyboard"
