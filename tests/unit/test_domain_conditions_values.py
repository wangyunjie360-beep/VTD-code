from pathlib import Path

from openscenario_mcp.knowledge.loader import load_element_record


RULE_ENUM = [
    "equalTo",
    "greaterThan",
    "lessThan",
    "greaterOrEqual",
    "lessOrEqual",
    "notEqualTo",
]


def test_by_entity_and_value_condition_records_capture_wrapper_branches() -> None:
    by_entity = load_element_record(Path("knowledge/structured/elements/ByEntityCondition.json"))
    by_value = load_element_record(Path("knowledge/structured/elements/ByValueCondition.json"))

    assert by_entity.content_model_kind == "all"
    assert by_entity.allowed_children == [
        {"name": "TriggeringEntities", "cardinality": "1..1"},
        {"name": "EntityCondition", "cardinality": "1..1"},
    ]

    assert by_value.content_model_kind == "choice"
    assert by_value.child_groups == [
        {
            "members": [
                "ParameterCondition",
                "TimeOfDayCondition",
                "SimulationTimeCondition",
                "StoryboardElementStateCondition",
                "UserDefinedValueCondition",
                "TrafficSignalCondition",
                "TrafficSignalControllerCondition",
                "VariableCondition",
            ],
            "cardinality": "1..1",
        }
    ]


def test_trigger_wrapper_records_capture_trigger_sequences() -> None:
    start_trigger = load_element_record(Path("knowledge/structured/elements/StartTrigger.json"))
    stop_trigger = load_element_record(Path("knowledge/structured/elements/StopTrigger.json"))
    condition_group = load_element_record(Path("knowledge/structured/elements/ConditionGroup.json"))
    triggering_entities = load_element_record(
        Path("knowledge/structured/elements/TriggeringEntities.json")
    )

    assert start_trigger.content_model_kind == "sequence"
    assert start_trigger.allowed_children == [
        {"name": "ConditionGroup", "cardinality": "0..*"}
    ]

    assert stop_trigger.content_model_kind == "sequence"
    assert stop_trigger.allowed_children == [
        {"name": "ConditionGroup", "cardinality": "0..*"}
    ]

    assert condition_group.content_model_kind == "sequence"
    assert condition_group.allowed_children == [{"name": "Condition", "cardinality": "1..*"}]

    assert triggering_entities.content_model_kind == "sequence"
    assert triggering_entities.allowed_children == [
        {"name": "EntityRef", "cardinality": "1..*"}
    ]
    assert triggering_entities.enum_constraints["triggeringEntitiesRule"] == ["all", "any"]


def test_condition_records_capture_exact_one_of_branches() -> None:
    condition = load_element_record(Path("knowledge/structured/elements/Condition.json"))
    entity_condition = load_element_record(Path("knowledge/structured/elements/EntityCondition.json"))
    collision_condition = load_element_record(
        Path("knowledge/structured/elements/CollisionCondition.json")
    )
    reach_position = load_element_record(
        Path("knowledge/structured/elements/ReachPositionCondition.json")
    )

    assert condition.content_model_kind == "choice"
    assert condition.child_groups == [
        {
            "members": ["ByEntityCondition", "ByValueCondition"],
            "cardinality": "1..1",
        }
    ]

    assert entity_condition.content_model_kind == "choice"
    assert entity_condition.child_groups == [
        {
            "members": [
                "EndOfRoadCondition",
                "CollisionCondition",
                "OffroadCondition",
                "TimeHeadwayCondition",
                "TimeToCollisionCondition",
                "AccelerationCondition",
                "StandStillCondition",
                "SpeedCondition",
                "RelativeSpeedCondition",
                "TraveledDistanceCondition",
                "ReachPositionCondition",
                "DistanceCondition",
                "RelativeDistanceCondition",
                "RelativeClearanceCondition",
                "AngleCondition",
                "RelativeAngleCondition",
            ],
            "cardinality": "1..1",
        }
    ]

    assert collision_condition.content_model_kind == "choice"
    assert collision_condition.child_groups == [
        {"members": ["EntityRef", "ByType"], "cardinality": "1..1"}
    ]

    assert reach_position.content_model_kind == "all"
    assert reach_position.allowed_children == [{"name": "Position", "cardinality": "1..1"}]


def test_value_constraints_and_condition_rules_keep_rule_enums_and_typed_refs() -> None:
    parameter_condition = load_element_record(
        Path("knowledge/structured/elements/ParameterCondition.json")
    )
    simulation_time = load_element_record(
        Path("knowledge/structured/elements/SimulationTimeCondition.json")
    )
    value_constraint = load_element_record(
        Path("knowledge/structured/elements/ValueConstraint.json")
    )
    variable_condition = load_element_record(
        Path("knowledge/structured/elements/VariableCondition.json")
    )
    relative_distance = load_element_record(
        Path("knowledge/structured/elements/RelativeDistanceCondition.json")
    )
    storyboard_condition = load_element_record(
        Path("knowledge/structured/elements/StoryboardElementStateCondition.json")
    )
    traffic_signal_controller = load_element_record(
        Path("knowledge/structured/elements/TrafficSignalControllerCondition.json")
    )

    assert parameter_condition.enum_constraints["rule"] == RULE_ENUM
    assert simulation_time.enum_constraints["rule"] == RULE_ENUM
    assert value_constraint.enum_constraints["rule"] == RULE_ENUM
    assert variable_condition.enum_constraints["rule"] == RULE_ENUM
    assert relative_distance.enum_constraints["rule"] == RULE_ENUM

    assert parameter_condition.required_attributes[0]["reference_kind"] == "parameter"
    assert variable_condition.required_attributes[0]["reference_kind"] == "variable"
    assert relative_distance.required_attributes[0]["reference_kind"] == "entity"
    assert storyboard_condition.required_attributes[1]["reference_kind"] == "storyboard_element"
    assert traffic_signal_controller.required_attributes[1]["reference_kind"] == (
        "traffic_signal_controller"
    )


def test_domain_condition_value_records_reference_existing_children() -> None:
    record_names = [
        "ByEntityCondition",
        "ByValueCondition",
        "CollisionCondition",
        "Condition",
        "ConditionGroup",
        "ConstraintGroup",
        "DistanceCondition",
        "EntityCondition",
        "ReachPositionCondition",
        "RelativeClearanceCondition",
        "RoadCondition",
        "Rule",
        "StartTrigger",
        "StopTrigger",
        "TimeToCollisionCondition",
        "TimeToCollisionConditionTarget",
        "TriggeringEntities",
    ]

    for name in record_names:
        record = load_element_record(Path(f"knowledge/structured/elements/{name}.json"))
        for child in record.allowed_children:
            child_path = Path(f"knowledge/structured/elements/{child['name']}.json")
            assert child_path.exists(), f"{name} references missing child record {child['name']}"
