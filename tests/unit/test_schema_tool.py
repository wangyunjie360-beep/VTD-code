import pytest

from openscenario_mcp.models import ElementRecord, KnowledgeBase
from openscenario_mcp.tools.schema import build_get_element_schema_tool


def test_get_element_schema_returns_named_record() -> None:
    knowledge_base = KnowledgeBase(
        records_by_element={
            "FileHeader": ElementRecord(
                element="FileHeader",
                description="Provides the scenario metadata header for an OpenSCENARIO document.",
                parent_contexts=["OpenSCENARIO"],
                required_attributes=[{"name": "revMajor", "type": "UnsignedShort"}],
                optional_attributes=[],
                allowed_children=[{"name": "Properties", "cardinality": "0..1"}],
                child_order=["License", "Properties"],
                multiplicity={"Properties": "0..1"},
                enum_constraints={},
                source_path="knowledge/raw/schema/OpenSCENARIO.xsd#L1300",
            )
        }
    )

    tool = build_get_element_schema_tool(knowledge_base)
    result = tool("FileHeader")

    assert result["element"] == "FileHeader"
    assert result["required_attributes"][0]["name"] == "revMajor"
    assert result["source_path"].startswith("knowledge/raw/schema/OpenSCENARIO.xsd#L")
    assert result["strategy"]["structure_mode"] == "sequence"
    assert result["strategy"]["ordering"] == {
        "mode": "sequence",
        "child_order": ["License", "Properties"],
    }
    assert result["strategy"]["reference_requirements"] == []


def test_get_element_schema_round_trips_variable_closure_metadata() -> None:
    knowledge_base = KnowledgeBase(
        records_by_element={
            "VariableAction": ElementRecord(
                element="VariableAction",
                description="Applies a variable action.",
                content_model_kind="choice",
                child_groups=[
                    {
                        "members": ["SetAction", "ModifyAction"],
                        "cardinality": "1..1",
                    }
                ],
                semantic_constraints=[
                    "variableRef must point at a declared parameter or variable."
                ],
                contextual_variants=[
                    {
                        "parent_context": "ParameterAction",
                        "type_ref": "ParameterActionType",
                        "deprecated": False,
                    }
                ],
                parent_contexts=["PrivateAction"],
                required_attributes=[{"name": "variableRef", "type": "String"}],
                optional_attributes=[],
                allowed_children=[],
                child_order=[],
                multiplicity={},
                enum_constraints={},
                source_path="knowledge/structured/elements/VariableAction.json",
            )
        }
    )

    tool = build_get_element_schema_tool(knowledge_base)
    result = tool("VariableAction")

    assert result["content_model_kind"] == "choice"
    assert result["child_groups"] == [
        {"members": ["SetAction", "ModifyAction"], "cardinality": "1..1"}
    ]
    assert result["semantic_constraints"] == [
        "variableRef must point at a declared parameter or variable."
    ]
    assert result["contextual_variants"] == [
        {
            "parent_context": "ParameterAction",
            "type_ref": "ParameterActionType",
            "deprecated": False,
        }
    ]
    assert result["strategy"]["branch_selection"] == {
        "mode": "single",
        "groups": [
            {"members": ["SetAction", "ModifyAction"], "min_branches": 1, "max_branches": 1}
        ],
    }
    assert result["strategy"]["variant_resolution"] == {
        "selection_required": True,
        "parent_context": None,
        "resolved_variant": None,
        "preferred_variants": [
            {
                "parent_context": "ParameterAction",
                "type_ref": "ParameterActionType",
                "deprecated": False,
            }
        ],
        "deprecated_variants": [],
    }


def test_get_element_schema_resolves_strategy_for_parent_context() -> None:
    knowledge_base = KnowledgeBase(
        records_by_element={
            "SetAction": ElementRecord(
                element="SetAction",
                description="Set action leaf.",
                content_model_kind="choice",
                child_groups=[
                    {
                        "members": ["Value", "Expression"],
                        "cardinality": "1..1",
                    }
                ],
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
                source_path="knowledge/structured/elements/SetAction.json",
            )
        }
    )

    tool = build_get_element_schema_tool(knowledge_base)
    result = tool("SetAction", parent_context="VariableAction")

    assert result["strategy"]["variant_resolution"]["resolved_variant"] == {
        "parent_context": "VariableAction",
        "type_ref": "VariableSetAction",
        "deprecated": False,
    }
    assert result["strategy"]["repair_priority"] == [
        "resolve_contextual_variant",
        "satisfy_choice_cardinality",
        "add_required_references",
    ]


def test_get_element_schema_raises_value_error_for_unknown_element() -> None:
    tool = build_get_element_schema_tool(KnowledgeBase(records_by_element={}))

    with pytest.raises(ValueError, match="^Unknown element: MissingElement$"):
        tool("MissingElement")
