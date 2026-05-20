from pathlib import Path

from openscenario_mcp.knowledge.loader import load_element_record


def load_domain_record(name: str):
    return load_element_record(Path(f"knowledge/structured/elements/{name}.json"))


def test_global_action_and_variable_branches_capture_contextual_variants() -> None:
    global_action = load_domain_record("GlobalAction")
    parameter_action = load_domain_record("ParameterAction")
    variable_action = load_domain_record("VariableAction")

    assert global_action.contextual_variants == [
        {
            "parent_context": "Action",
            "type_ref": "GlobalAction",
            "deprecated": False,
        },
        {
            "parent_context": "Actions",
            "type_ref": "GlobalAction",
            "deprecated": False,
        },
    ]
    assert parameter_action.contextual_variants == [
        {
            "parent_context": "GlobalAction",
            "type_ref": "ParameterAction",
            "deprecated": True,
        }
    ]
    assert variable_action.contextual_variants == [
        {
            "parent_context": "GlobalAction",
            "type_ref": "VariableAction",
            "deprecated": False,
        }
    ]


def test_shared_parameter_and_variable_action_leaves_keep_contextual_variants() -> None:
    set_action = load_domain_record("SetAction")
    modify_action = load_domain_record("ModifyAction")
    add_value = load_domain_record("AddValue")
    multiply_by_value = load_domain_record("MultiplyByValue")

    assert set_action.contextual_variants == [
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
    assert modify_action.contextual_variants == [
        {
            "parent_context": "ParameterAction",
            "type_ref": "ParameterModifyAction",
            "deprecated": True,
        },
        {
            "parent_context": "VariableAction",
            "type_ref": "VariableModifyAction",
            "deprecated": False,
        },
    ]
    assert add_value.contextual_variants == [
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


def test_private_controller_and_appearance_actions_keep_choice_metadata() -> None:
    private_action = load_domain_record("PrivateAction")
    controller_action = load_domain_record("ControllerAction")
    appearance_action = load_domain_record("AppearanceAction")
    assign_controller_action = load_domain_record("AssignControllerAction")
    activate_controller_action = load_domain_record("ActivateControllerAction")

    assert private_action.content_model_kind == "choice"
    assert private_action.child_groups == [
        {
            "members": [
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
            ],
            "cardinality": "1..1",
        }
    ]
    assert controller_action.child_groups == [
        {
            "members": [
                "AssignControllerAction",
                "OverrideControllerValueAction",
                "ActivateControllerAction",
            ],
            "cardinality": "1..1",
        }
    ]
    assert appearance_action.child_groups == [
        {
            "members": ["LightStateAction", "AnimationAction"],
            "cardinality": "1..1",
        }
    ]
    assert assign_controller_action.contextual_variants == [
        {
            "parent_context": "ControllerAction",
            "type_ref": "AssignControllerAction",
            "deprecated": False,
        }
    ]
    assert activate_controller_action.contextual_variants == [
        {
            "parent_context": "ControllerAction",
            "type_ref": "ActivateControllerAction",
            "deprecated": False,
        },
        {
            "parent_context": "PrivateAction",
            "type_ref": "ActivateControllerAction",
            "deprecated": True,
        },
    ]
    assert activate_controller_action.optional_attributes == [
        {"name": "animation", "type": "Boolean"},
        {
            "name": "controllerRef",
            "type": "String",
            "reference_kind": "controller",
        },
        {"name": "lateral", "type": "Boolean"},
        {"name": "lighting", "type": "Boolean"},
        {"name": "longitudinal", "type": "Boolean"},
        {
            "name": "objectControllerRef",
            "type": "String",
            "reference_kind": "controller",
        },
    ]


def test_override_controller_value_inputs_capture_non_deprecated_variants() -> None:
    brake = load_domain_record("Brake")
    gear = load_domain_record("Gear")
    parking_brake = load_domain_record("ParkingBrake")

    assert brake.contextual_variants == [
        {
            "parent_context": "OverrideControllerValueAction",
            "type_ref": "OverrideBrakeAction",
            "deprecated": False,
        }
    ]
    assert gear.contextual_variants == [
        {
            "parent_context": "OverrideControllerValueAction",
            "type_ref": "OverrideGearAction",
            "deprecated": False,
        }
    ]
    assert parking_brake.contextual_variants == [
        {
            "parent_context": "OverrideControllerValueAction",
            "type_ref": "OverrideParkingBrakeAction",
            "deprecated": False,
        }
    ]


def test_trailer_and_coupling_records_capture_context_and_reference_kinds() -> None:
    trailer = load_domain_record("Trailer")
    trailer_action = load_domain_record("TrailerAction")
    connect_trailer_action = load_domain_record("ConnectTrailerAction")
    trailer_ref = load_domain_record("TrailerRef")
    trailer_hitch = load_domain_record("TrailerHitch")
    trailer_coupler = load_domain_record("TrailerCoupler")

    assert trailer_action.child_groups == [
        {
            "members": ["ConnectTrailerAction", "DisconnectTrailerAction"],
            "cardinality": "1..1",
        }
    ]
    assert trailer.contextual_variants == [
        {
            "parent_context": "Trailer",
            "type_ref": "ScenarioObject",
            "deprecated": False,
        },
        {
            "parent_context": "Vehicle",
            "type_ref": "Trailer",
            "deprecated": False,
        },
    ]
    assert trailer.parent_contexts == ["Trailer", "Vehicle"]
    assert connect_trailer_action.required_attributes == [
        {
            "name": "trailerRef",
            "type": "String",
            "reference_kind": "trailer",
        }
    ]
    assert trailer_ref.required_attributes == [
        {
            "name": "entityRef",
            "type": "String",
            "reference_kind": "entity",
        }
    ]
    assert trailer_hitch.contextual_variants == [
        {
            "parent_context": "Vehicle",
            "type_ref": "TrailerHitch",
            "deprecated": False,
        }
    ]
    assert trailer_coupler.contextual_variants == [
        {
            "parent_context": "Vehicle",
            "type_ref": "TrailerCoupler",
            "deprecated": False,
        }
    ]


def test_custom_command_action_keeps_simple_content_extension_attributes() -> None:
    custom_command_action = load_domain_record("CustomCommandAction")

    assert custom_command_action.required_attributes == [
        {"name": "type", "type": "String"}
    ]
