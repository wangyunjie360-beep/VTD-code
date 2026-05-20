import json
from pathlib import Path

from openscenario_mcp.knowledge.loader import load_element_record
from openscenario_mcp.models import KnowledgeBase
from openscenario_mcp.tools.schema import build_get_element_schema_tool


VARIABLE_DOMAIN_ELEMENTS = {
    "AddValue",
    "ConstraintGroup",
    "ModifyAction",
    "MultiplyByValue",
    "ParameterAction",
    "ParameterCondition",
    "ParameterDeclaration",
    "ParameterDeclarations",
    "Rule",
    "SetAction",
    "ValueConstraint",
    "VariableAction",
    "VariableCondition",
    "VariableDeclaration",
    "VariableDeclarations",
}


def test_variable_domain_elements_are_in_mvp_scope() -> None:
    scope_path = Path("knowledge/structured/mvp_scope.json")
    scope_payload = json.loads(scope_path.read_text(encoding="utf-8"))

    assert VARIABLE_DOMAIN_ELEMENTS <= set(scope_payload["elements"])


def test_variable_action_record_captures_choice_and_reference_semantics() -> None:
    record = load_element_record(Path("knowledge/structured/elements/VariableAction.json"))

    assert record.element == "VariableAction"
    assert record.content_model_kind == "choice"
    assert record.child_groups == [
        {"members": ["SetAction", "ModifyAction"], "cardinality": "1..1"}
    ]
    assert record.required_attributes == [
        {
            "name": "variableRef",
            "type": "String",
            "reference_kind": "variable",
        }
    ]


def test_set_action_record_captures_contextual_variants() -> None:
    record = load_element_record(Path("knowledge/structured/elements/SetAction.json"))

    assert record.element == "SetAction"
    assert record.contextual_variants == [
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
    ]


def test_modify_rule_leaf_records_capture_contextual_variants() -> None:
    add_value = load_element_record(Path("knowledge/structured/elements/AddValue.json"))
    multiply_by_value = load_element_record(
        Path("knowledge/structured/elements/MultiplyByValue.json")
    )

    expected_variants = [
        {
            "parent_context": "Rule",
            "type_ref": "ParameterAddValueRule",
            "deprecated": True,
        },
        {
            "parent_context": "Rule",
            "type_ref": "VariableAddValueRule",
            "deprecated": False,
        },
    ]
    assert add_value.contextual_variants == expected_variants
    assert multiply_by_value.contextual_variants == [
        {
            "parent_context": "Rule",
            "type_ref": "ParameterMultiplyByValueRule",
            "deprecated": True,
        },
        {
            "parent_context": "Rule",
            "type_ref": "VariableMultiplyByValueRule",
            "deprecated": False,
        },
    ]


def test_parameter_declaration_record_keeps_constraint_child_and_semantics() -> None:
    record = load_element_record(Path("knowledge/structured/elements/ParameterDeclaration.json"))

    assert record.content_model_kind == "sequence"
    assert record.allowed_children == [
        {"name": "ConstraintGroup", "cardinality": "0..unbounded"}
    ]
    assert record.semantic_constraints == []


def test_parameter_and_variable_reference_attributes_are_typed() -> None:
    parameter_action = load_element_record(
        Path("knowledge/structured/elements/ParameterAction.json")
    )
    parameter_condition = load_element_record(
        Path("knowledge/structured/elements/ParameterCondition.json")
    )
    variable_condition = load_element_record(
        Path("knowledge/structured/elements/VariableCondition.json")
    )

    assert parameter_action.required_attributes[0]["reference_kind"] == "parameter"
    assert parameter_condition.required_attributes[0]["reference_kind"] == "parameter"
    assert variable_condition.required_attributes[0]["reference_kind"] == "variable"


def test_variable_domain_records_have_closed_child_coverage() -> None:
    records = {
        name: load_element_record(Path(f"knowledge/structured/elements/{name}.json"))
        for name in VARIABLE_DOMAIN_ELEMENTS
    }

    for record in records.values():
        for child in record.allowed_children:
            child_name = child["name"]
            assert child_name in records, f"{record.element} references missing child record {child_name}"


def test_get_element_schema_returns_contextual_variable_metadata() -> None:
    record = load_element_record(Path("knowledge/structured/elements/SetAction.json"))
    tool = build_get_element_schema_tool(
        KnowledgeBase(records_by_element={"SetAction": record})
    )

    result = tool("SetAction")

    assert result["contextual_variants"][0]["parent_context"] == "ParameterAction"
    assert result["contextual_variants"][1]["type_ref"] == "VariableSetAction"
