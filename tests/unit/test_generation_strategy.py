from openscenario_mcp.generation.strategy import build_element_strategy
from openscenario_mcp.models import ElementRecord


def test_build_element_strategy_resolves_contextual_variant_and_single_choice() -> None:
    record = ElementRecord(
        element="SetAction",
        description="Shared set-action leaf.",
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
        required_attributes=[
            {"name": "variableRef", "type": "String", "reference_kind": "variable"}
        ],
    )

    strategy = build_element_strategy(record, parent_context="VariableAction")

    assert strategy["structure_mode"] == "choice"
    assert strategy["branch_selection"] == {
        "mode": "single",
        "groups": [
            {
                "members": ["Value", "Expression"],
                "min_branches": 1,
                "max_branches": 1,
            }
        ],
    }
    assert strategy["variant_resolution"] == {
        "selection_required": True,
        "parent_context": "VariableAction",
        "resolved_variant": {
            "parent_context": "VariableAction",
            "type_ref": "VariableSetAction",
            "deprecated": False,
        },
        "preferred_variants": [
            {
                "parent_context": "VariableAction",
                "type_ref": "VariableSetAction",
                "deprecated": False,
            }
        ],
        "deprecated_variants": [
            {
                "parent_context": "ParameterAction",
                "type_ref": "ParameterSetAction",
                "deprecated": True,
            }
        ],
    }
    assert strategy["reference_requirements"] == [
        {"name": "variableRef", "reference_kind": "variable", "required": True}
    ]
    assert strategy["repair_priority"] == [
        "resolve_contextual_variant",
        "satisfy_choice_cardinality",
        "add_required_references",
    ]


def test_build_element_strategy_preserves_bounded_choice_cardinality() -> None:
    record = ElementRecord(
        element="TrafficDistribution",
        description="Traffic distribution wrapper.",
        content_model_kind="choice",
        child_groups=[
            {
                "members": ["TrafficDistributionEntry", "CatalogReferences"],
                "cardinality": "1..2",
            }
        ],
        allowed_children=[
            {"name": "TrafficDistributionEntry", "cardinality": "1..unbounded"},
            {"name": "CatalogReferences", "cardinality": "1..unbounded"},
        ],
    )

    strategy = build_element_strategy(record)

    assert strategy["branch_selection"] == {
        "mode": "bounded",
        "groups": [
            {
                "members": ["TrafficDistributionEntry", "CatalogReferences"],
                "min_branches": 1,
                "max_branches": 2,
            }
        ],
    }
    assert strategy["repair_priority"] == [
        "satisfy_choice_cardinality",
        "add_required_children",
    ]


def test_build_element_strategy_prioritizes_references_and_sequence_order() -> None:
    record = ElementRecord(
        element="Private",
        description="Private action wrapper.",
        content_model_kind="sequence",
        required_attributes=[
            {"name": "entityRef", "type": "String", "reference_kind": "entity"}
        ],
        allowed_children=[
            {"name": "PrivateAction", "cardinality": "1..1"},
            {"name": "ControllerAction", "cardinality": "0..1"},
        ],
        child_order=["PrivateAction", "ControllerAction"],
        multiplicity={"PrivateAction": "1..1", "ControllerAction": "0..1"},
    )

    strategy = build_element_strategy(record)

    assert strategy["ordering"] == {
        "mode": "sequence",
        "child_order": ["PrivateAction", "ControllerAction"],
    }
    assert strategy["required_children"] == ["PrivateAction"]
    assert strategy["reference_requirements"] == [
        {"name": "entityRef", "reference_kind": "entity", "required": True}
    ]
    assert strategy["repair_priority"] == [
        "add_required_references",
        "add_required_children",
        "enforce_sequence_order",
    ]


def test_build_element_strategy_falls_back_to_deprecated_variant_when_needed() -> None:
    record = ElementRecord(
        element="ParameterAction",
        description="Deprecated parameter action wrapper.",
        contextual_variants=[
            {
                "parent_context": "GlobalAction",
                "type_ref": "ParameterAction",
                "deprecated": True,
            }
        ],
    )

    strategy = build_element_strategy(record, parent_context="GlobalAction")

    assert strategy["variant_resolution"] == {
        "selection_required": True,
        "parent_context": "GlobalAction",
        "resolved_variant": {
            "parent_context": "GlobalAction",
            "type_ref": "ParameterAction",
            "deprecated": True,
        },
        "preferred_variants": [
            {
                "parent_context": "GlobalAction",
                "type_ref": "ParameterAction",
                "deprecated": True,
            }
        ],
        "deprecated_variants": [
            {
                "parent_context": "GlobalAction",
                "type_ref": "ParameterAction",
                "deprecated": True,
            }
        ],
    }
