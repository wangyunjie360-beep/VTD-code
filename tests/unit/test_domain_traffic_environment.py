from pathlib import Path

from openscenario_mcp.knowledge.loader import load_element_record


DOMAIN_ELEMENTS = [
    line.strip()
    for line in Path(
        "knowledge/structured/manifests/domain-traffic-environment.txt"
    ).read_text(encoding="utf-8").splitlines()
    if line.strip()
]


def load_record(name: str):
    return load_element_record(Path(f"knowledge/structured/elements/{name}.json"))


def test_traffic_environment_records_replace_schema_derived_placeholders() -> None:
    records = {name: load_record(name) for name in DOMAIN_ELEMENTS}

    for record in records.values():
        assert record.description
        assert not record.description.startswith("Schema-derived "), (
            f"{record.element} still uses the schema-derived placeholder description"
        )


def test_environment_records_capture_branch_and_deprecation_metadata() -> None:
    environment = load_record("Environment")
    environment_action = load_record("EnvironmentAction")
    weather = load_record("Weather")
    precipitation = load_record("Precipitation")

    assert environment.content_model_kind == "all"
    assert "xsd:all" in environment.description
    assert "ParameterDeclarations" in environment.description
    assert "RoadCondition" in environment.description

    assert environment_action.content_model_kind == "choice"
    assert "Exactly one" in environment_action.description
    assert "CatalogReference" in environment_action.description

    assert "xsd:all" in weather.description
    assert "cloudState" in weather.description
    assert "fractionalCloudCover" in weather.description
    assert "deprecated" in weather.description

    assert "precipitationType" in precipitation.description
    assert "precipitationIntensity" in precipitation.description
    assert "intensity" in precipitation.description


def test_traffic_generation_records_capture_source_sink_swarm_branches() -> None:
    traffic_action = load_record("TrafficAction")
    traffic_source = load_record("TrafficSourceAction")
    traffic_sink = load_record("TrafficSinkAction")
    traffic_swarm = load_record("TrafficSwarmAction")
    traffic_distribution = load_record("TrafficDistribution")

    assert traffic_action.content_model_kind == "choice"
    assert "Exactly one" in traffic_action.description
    assert "TrafficSourceAction" in traffic_action.description
    assert "TrafficSinkAction" in traffic_action.description
    assert "TrafficSwarmAction" in traffic_action.description

    assert "Position" in traffic_source.description
    assert "TrafficDistribution" in traffic_source.description
    assert "deprecated" in traffic_source.description

    assert "Position" in traffic_sink.description
    assert "TrafficDefinition" in traffic_sink.description
    assert "deprecated" in traffic_sink.description

    assert "CentralObject" in traffic_swarm.description
    assert "InitialSpeedRange" in traffic_swarm.description
    assert "DirectionOfTravelDistribution" in traffic_swarm.description
    assert "deprecated" in traffic_swarm.description

    assert "TrafficDistributionEntry" in traffic_distribution.description
    assert "CatalogReferences" in traffic_distribution.description
    assert "one or more" in traffic_distribution.description


def test_distribution_wrappers_capture_nested_and_repeated_children() -> None:
    parameter_value_distribution = load_record("ParameterValueDistribution")
    deterministic = load_record("Deterministic")
    deterministic_multi = load_record("DeterministicMultiParameterDistribution")
    deterministic_single = load_record("DeterministicSingleParameterDistribution")
    stochastic = load_record("Stochastic")
    stochastic_distribution = load_record("StochasticDistribution")
    distribution_set = load_record("DistributionSet")
    value_set_distribution = load_record("ValueSetDistribution")
    parameter_value_set = load_record("ParameterValueSet")
    probability_distribution_set = load_record("ProbabilityDistributionSet")
    histogram = load_record("Histogram")

    assert "ScenarioFile" in parameter_value_distribution.description
    assert "Deterministic" in parameter_value_distribution.description
    assert "Stochastic" in parameter_value_distribution.description

    assert "one or more" in deterministic.description
    assert "DeterministicMultiParameterDistribution" in deterministic.description
    assert "DeterministicSingleParameterDistribution" in deterministic.description

    assert "ValueSetDistribution" in deterministic_multi.description

    assert "parameterName" in deterministic_single.description
    assert "DistributionSet" in deterministic_single.description
    assert "DistributionRange" in deterministic_single.description
    assert "UserDefinedDistribution" in deterministic_single.description

    assert "numberOfTestRuns" in stochastic.description
    assert "one or more" in stochastic.description
    assert "StochasticDistribution" in stochastic.description

    assert "parameterName" in stochastic_distribution.description
    assert "ProbabilityDistributionSet" in stochastic_distribution.description
    assert "Histogram" in stochastic_distribution.description
    assert "UserDefinedDistribution" in stochastic_distribution.description

    assert "one or more" in distribution_set.description
    assert "Element" in distribution_set.description

    assert "one or more" in value_set_distribution.description
    assert "ParameterValueSet" in value_set_distribution.description

    assert "one or more" in parameter_value_set.description
    assert "ParameterAssignment" in parameter_value_set.description

    assert "one or more" in probability_distribution_set.description
    assert "Element" in probability_distribution_set.description

    assert "one or more" in histogram.description
    assert "Bin" in histogram.description


def test_distribution_structural_metadata_keeps_choice_and_extension_details() -> None:
    traffic_distribution = load_record("TrafficDistribution")
    user_defined_distribution = load_record("UserDefinedDistribution")

    assert traffic_distribution.child_groups == [
        {
            "members": ["TrafficDistributionEntry", "CatalogReferences"],
            "cardinality": "1..2",
        }
    ]
    assert traffic_distribution.semantic_constraints == [
        "Select 1 to 2 branches from: TrafficDistributionEntry, CatalogReferences."
    ]
    assert user_defined_distribution.required_attributes == [
        {"name": "type", "type": "String"}
    ]


def test_distribution_enum_metadata_highlights_appinfo_deprecations() -> None:
    vehicle_category_entry = load_record("VehicleCategoryDistributionEntry")
    vehicle_role_entry = load_record("VehicleRoleDistributionEntry")

    assert "motorbike" in vehicle_category_entry.description
    assert "truck" in vehicle_category_entry.description
    assert "deprecated" in vehicle_category_entry.description

    assert "fire" in vehicle_role_entry.description
    assert "roadAssistance" in vehicle_role_entry.description
    assert "deprecated" in vehicle_role_entry.description
