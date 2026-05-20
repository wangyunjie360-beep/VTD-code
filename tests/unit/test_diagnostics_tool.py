from __future__ import annotations

import pytest

from openscenario_mcp.tools.diagnostics import build_explain_validation_errors_tool
from openscenario_mcp.validator.classifier import load_patterns


def test_explain_validation_errors_classifies_missing_child() -> None:
    errors = [
        {
            "line": 12,
            "column": 8,
            "message": "Element 'ManeuverGroup': Missing child element(s). Expected is ( Actors ).",
        }
    ]

    explain_validation_errors = build_explain_validation_errors_tool(load_patterns())
    result = explain_validation_errors(errors)

    assert result["diagnostics"][0]["category"] == "missing_required_child"
    assert result["diagnostics"][0]["missing"] == ["Actors"]
    assert result["diagnostics"][0]["repair_strategy"]["focus_element"] == "ManeuverGroup"
    assert result["diagnostics"][0]["repair_strategy"]["recommended_actions"] == [
        "add_required_children",
        "enforce_sequence_order",
    ]


def test_explain_validation_errors_keeps_wrong_parent_as_unexpected_element() -> None:
    errors = [
        {
            "message": (
                "Element 'Entities': This element is not expected. "
                "Expected is ( Init )."
            )
        }
    ]

    explain_validation_errors = build_explain_validation_errors_tool(load_patterns())
    result = explain_validation_errors(errors)

    diagnostic = result["diagnostics"][0]
    assert diagnostic["category"] == "unexpected_element"
    assert diagnostic["element"] == "Entities"
    assert diagnostic["expected"] == ["Init"]


def test_explain_validation_errors_describes_choice_group_missing_child() -> None:
    errors = [
        {
            "message": (
                "Element 'PrivateAction': Missing child element(s). Expected is one "
                "of ( LongitudinalAction, LateralAction, VisibilityAction, "
                "SynchronizeAction, ActivateControllerAction, ControllerAction, "
                "TeleportAction, RoutingAction, AppearanceAction, TrailerAction )."
            )
        }
    ]

    explain_validation_errors = build_explain_validation_errors_tool(load_patterns())
    result = explain_validation_errors(errors)

    diagnostic = result["diagnostics"][0]
    assert diagnostic["category"] == "missing_required_child"
    assert "missing" not in diagnostic
    assert diagnostic["required_one_of"] == [
        "LongitudinalAction",
        "LateralAction",
        "VisibilityAction",
        "SynchronizeAction",
        "ActivateControllerAction",
        "ControllerAction",
        "TeleportAction",
        "RoutingAction",
        "AppearanceAction",
        "TrailerAction",
    ]
    assert "one of the listed elements is required" in diagnostic["fix_advice"]
    assert "LongitudinalAction" in diagnostic["fix_advice"]
    assert diagnostic["repair_strategy"]["recommended_actions"] == [
        "satisfy_choice_cardinality"
    ]
    assert diagnostic["repair_strategy"]["focus_strategy"]["branch_selection"]["mode"] == "single"


def test_explain_validation_errors_adds_reference_aware_repair_strategy() -> None:
    errors = [
        {
            "message": (
                "Element 'VariableAction': The attribute 'variableRef' is required but "
                "missing."
            )
        }
    ]

    explain_validation_errors = build_explain_validation_errors_tool(load_patterns())
    result = explain_validation_errors(errors)

    diagnostic = result["diagnostics"][0]
    assert diagnostic["category"] == "missing_required_attribute"
    assert diagnostic["repair_strategy"]["focus_element"] == "VariableAction"
    assert diagnostic["repair_strategy"]["recommended_actions"] == [
        "add_required_references"
    ]
    assert diagnostic["repair_strategy"]["focus_strategy"]["reference_requirements"] == [
        {"name": "variableRef", "reference_kind": "variable", "required": True}
    ]


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            {
                "message": (
                    "Element 'FileHeader': The attribute 'author' is required but "
                    "missing."
                )
            },
            {
                "category": "missing_required_attribute",
                "element": "FileHeader",
                "attribute": "author",
            },
        ),
        (
            {
                "message": (
                    "Element 'Broken': This element is not expected. "
                    "Expected is ( Actions )."
                )
            },
            {
                "category": "unexpected_element",
                "element": "Broken",
                "expected": ["Actions"],
            },
        ),
        (
            {
                "message": (
                    "Element 'FileHeader', attribute 'extra': The attribute 'extra' "
                    "is not allowed."
                )
            },
            {
                "category": "invalid_attribute",
                "element": "FileHeader",
                "attribute": "extra",
            },
        ),
        (
            {
                "message": (
                    "Element 'Story': This element is not expected. "
                    "Expected is ( Init )."
                )
            },
            {
                "category": "wrong_child_order",
                "element": "Story",
                "expected": ["Init"],
            },
        ),
        (
            {
                "message": (
                    "Element 'SpeedActionDynamics', attribute 'dynamicsShape': "
                    "'invalid' is not a valid value of the union type "
                    "'DynamicsShape'."
                )
            },
            {
                "category": "invalid_enum_value",
                "element": "SpeedActionDynamics",
                "attribute": "dynamicsShape",
                "invalid_value": "invalid",
                "type_name": "DynamicsShape",
            },
        ),
        (
            {
                "message": (
                    "Element '{urn:test}OpenScenario': No matching global "
                    "declaration available for the validation root."
                )
            },
            {
                "category": "namespace_or_root_issue",
                "element": "{urn:test}OpenScenario",
            },
        ),
    ],
)
def test_explain_validation_errors_covers_mvp_categories(
    error: dict[str, str],
    expected: dict[str, object],
) -> None:
    explain_validation_errors = build_explain_validation_errors_tool(load_patterns())

    result = explain_validation_errors([error])

    diagnostic = result["diagnostics"][0]
    for key, value in expected.items():
        assert diagnostic[key] == value
    assert diagnostic["fix_advice"]
