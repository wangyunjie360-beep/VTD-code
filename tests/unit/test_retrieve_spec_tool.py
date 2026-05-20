from __future__ import annotations

from collections.abc import Mapping

import openscenario_mcp.tools.retrieve_spec as retrieve_spec_module
from openscenario_mcp.models import ElementRecord, KnowledgeBase
from openscenario_mcp.tools.retrieve_spec import build_retrieve_spec_tool


def _build_knowledge_base() -> KnowledgeBase:
    return KnowledgeBase(
        records_by_element={
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
            "FileHeader": ElementRecord(
                element="FileHeader",
                description=(
                    "Scenario metadata header. It carries authorship, revision, and "
                    "description fields before any scenario definition content."
                ),
                parent_contexts=["OpenSCENARIO"],
                required_attributes=[
                    {"name": "author", "type": "String"},
                    {"name": "date", "type": "DateTime"},
                    {"name": "description", "type": "String"},
                    {"name": "revMajor", "type": "UnsignedShort"},
                    {"name": "revMinor", "type": "UnsignedShort"},
                ],
                optional_attributes=[],
                allowed_children=[
                    {"name": "License", "cardinality": "0..1"},
                    {"name": "Properties", "cardinality": "0..1"},
                ],
                child_order=["License", "Properties"],
                multiplicity={
                    "License": "0..1",
                    "Properties": "0..1",
                },
                enum_constraints={},
                source_path=(
                    "knowledge/raw/schema/OpenSCENARIO.xsd#L1300;"
                    "knowledge/structured/elements/FileHeader.json"
                ),
            ),
            "ParameterDeclarations": ElementRecord(
                element="ParameterDeclarations",
                description=(
                    "Declares reusable parameters before the rest of the scenario "
                    "content is evaluated."
                ),
                parent_contexts=["OpenSCENARIO"],
                required_attributes=[],
                optional_attributes=[],
                allowed_children=[
                    {"name": "ParameterDeclaration", "cardinality": "0..*"},
                ],
                child_order=["ParameterDeclaration"],
                multiplicity={"ParameterDeclaration": "0..*"},
                enum_constraints={},
                source_path="knowledge/raw/schema/OpenSCENARIO.xsd#L1340",
            ),
            "RoadNetwork": ElementRecord(
                element="RoadNetwork",
                description=(
                    "Defines the road network references used by the scenario map "
                    "context."
                ),
                parent_contexts=["OpenSCENARIO"],
                required_attributes=[],
                optional_attributes=[],
                allowed_children=[
                    {"name": "LogicFile", "cardinality": "0..1"},
                    {"name": "SceneGraphFile", "cardinality": "0..1"},
                ],
                child_order=["LogicFile", "SceneGraphFile"],
                multiplicity={
                    "LogicFile": "0..1",
                    "SceneGraphFile": "0..1",
                },
                enum_constraints={},
                source_path="knowledge/raw/schema/OpenSCENARIO.xsd#L1500",
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


def test_retrieve_spec_returns_source_linked_element_result() -> None:
    tool = build_retrieve_spec_tool(_build_knowledge_base(), _build_diagnostic_patterns())

    result = tool(query="Storyboard", kind="element", top_k=1)

    assert len(result["hits"]) == 1
    hit = result["hits"][0]
    assert hit["title"] == "Storyboard"
    assert hit["kind"] == "element"
    assert hit["source_path"] == "knowledge/raw/schema/OpenSCENARIO.xsd#L2206"
    assert "Scenario execution container" in hit["summary"]
    assert "Required children: Init" in hit["constraints"]
    assert "Child order: Init -> Story -> StopTrigger" in hit["constraints"]
    assert hit["strategy_summary"] == [
        "Preserve child order: Init -> Story -> StopTrigger.",
        "Keep required children present: Init.",
    ]


def test_retrieve_spec_returns_attribute_result_with_host_element_context() -> None:
    tool = build_retrieve_spec_tool(_build_knowledge_base(), _build_diagnostic_patterns())

    result = tool(query="rev major", kind="attribute", top_k=1)

    assert len(result["hits"]) == 1
    hit = result["hits"][0]
    assert hit["title"] == "FileHeader.revMajor"
    assert hit["kind"] == "attribute"
    assert (
        hit["source_path"]
        == "knowledge/raw/schema/OpenSCENARIO.xsd#L1300;"
        "knowledge/structured/elements/FileHeader.json"
    )
    assert hit["source_paths"] == [
        "knowledge/raw/schema/OpenSCENARIO.xsd#L1300",
        "knowledge/structured/elements/FileHeader.json",
    ]
    assert hit["parent_contexts"] == ["OpenSCENARIO", "FileHeader"]
    assert "Required attribute 'revMajor' on FileHeader" in hit["summary"]
    assert "Required on FileHeader" in hit["constraints"]
    assert "Type: UnsignedShort" in hit["constraints"]


def test_retrieve_spec_returns_error_pattern_result() -> None:
    tool = build_retrieve_spec_tool(_build_knowledge_base(), _build_diagnostic_patterns())

    result = tool(query="missing_required_child", kind="error", top_k=1)

    assert len(result["hits"]) == 1
    hit = result["hits"][0]
    assert hit["title"] == "missing_required_child"
    assert hit["kind"] == "error"
    assert hit["source_path"] == "knowledge/diagnostics/patterns.json#missing_required_child"
    assert "missing required child" in hit["summary"].lower()
    assert "Add the required child element" in hit["summary"]
    assert hit["strategy_summary"] == [
        "Add the expected child element before rewriting unrelated XML.",
        "If the parent is a choice wrapper, satisfy its branch cardinality.",
    ]


def test_retrieve_spec_supports_description_driven_concept_queries() -> None:
    tool = build_retrieve_spec_tool(_build_knowledge_base(), _build_diagnostic_patterns())

    result = tool(
        query="revision and description fields",
        kind="concept",
        top_k=1,
    )

    assert len(result["hits"]) == 1
    hit = result["hits"][0]
    assert hit["title"] == "FileHeader"
    assert hit["kind"] == "concept"
    assert (
        hit["source_path"]
        == "knowledge/raw/schema/OpenSCENARIO.xsd#L1300;"
        "knowledge/structured/elements/FileHeader.json"
    )
    assert hit["parent_contexts"] == ["OpenSCENARIO"]
    assert "revision, and description fields" in hit["summary"]
    assert hit["strategy_summary"] == [
        "Preserve child order: License -> Properties.",
    ]


def test_retrieve_spec_matches_natural_language_to_camel_case_element() -> None:
    tool = build_retrieve_spec_tool(_build_knowledge_base(), _build_diagnostic_patterns())

    result = tool(query="road network", kind="element", top_k=1)

    assert len(result["hits"]) == 1
    hit = result["hits"][0]
    assert hit["title"] == "RoadNetwork"
    assert hit["kind"] == "element"
    assert hit["parent_contexts"] == ["OpenSCENARIO"]


def test_retrieve_spec_loads_default_diagnostic_patterns_when_none() -> None:
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
        tool = build_retrieve_spec_tool(_build_knowledge_base())
        result = tool(query="missing required child", kind="error", top_k=1)
    finally:
        retrieve_spec_module.load_patterns = original_load_patterns

    assert len(result["hits"]) == 1
    hit = result["hits"][0]
    assert hit["title"] == "missing_required_child"
    assert hit["kind"] == "error"


def test_retrieve_spec_surfaces_contextual_variant_and_choice_metadata() -> None:
    knowledge_base = KnowledgeBase(
        records_by_element={
            "SetAction": ElementRecord(
                element="SetAction",
                description="Set-action leaf shared by parameter and variable action paths.",
                content_model_kind="choice",
                child_groups=[{"members": ["Value", "Expression"], "cardinality": "1..1"}],
                semantic_constraints=["Select exactly one of: Value, Expression."],
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
                required_attributes=[{"name": "value", "type": "String"}],
                optional_attributes=[],
                allowed_children=[],
                child_order=[],
                multiplicity={},
                enum_constraints={},
                source_path="knowledge/raw/schema/OpenSCENARIO.xsd#L1744",
            )
        }
    )

    tool = build_retrieve_spec_tool(knowledge_base, _build_diagnostic_patterns())

    result = tool(query="set action", kind="element", top_k=1)

    assert len(result["hits"]) == 1
    hit = result["hits"][0]
    assert "Content model: choice" in hit["constraints"]
    assert "Choice groups: Value | Expression" in hit["constraints"]
    assert "Deprecated variants present" in hit["constraints"]
    assert (
        "Contextual variants: ParameterAction -> ParameterSetAction (deprecated); "
        "VariableAction -> VariableSetAction"
    ) in hit["constraints"]
    assert hit["strategy_summary"] == [
        "Resolve contextual variant before emitting this shared element name.",
        "Select exactly one branch from: Value, Expression.",
    ]


def test_retrieve_spec_resolves_strategy_summary_for_parent_context() -> None:
    knowledge_base = KnowledgeBase(
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
            )
        }
    )

    tool = build_retrieve_spec_tool(knowledge_base, _build_diagnostic_patterns())
    result = tool(
        query="set action",
        kind="concept",
        top_k=1,
        parent_context="VariableAction",
    )

    assert len(result["hits"]) == 1
    hit = result["hits"][0]
    assert hit["strategy_summary"] == [
        "Use variant for VariableAction: VariableSetAction.",
        "Select exactly one branch from: Value, Expression.",
        "Wire required variable reference: variableRef.",
    ]


def test_retrieve_spec_surfaces_attribute_reference_kinds() -> None:
    knowledge_base = KnowledgeBase(
        records_by_element={
            "VariableAction": ElementRecord(
                element="VariableAction",
                description="Variable action wrapper.",
                parent_contexts=["GlobalAction"],
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
            )
        }
    )

    tool = build_retrieve_spec_tool(knowledge_base, _build_diagnostic_patterns())

    result = tool(query="variable ref", kind="attribute", top_k=1)

    assert len(result["hits"]) == 1
    hit = result["hits"][0]
    assert hit["title"] == "VariableAction.variableRef"
    assert "Reference kind: variable" in hit["constraints"]
