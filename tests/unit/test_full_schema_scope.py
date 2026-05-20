import json
from pathlib import Path

from openscenario_mcp.knowledge.xsd_parser import parse_element_definition


def test_parse_variable_action_extracts_choice_and_attribute_metadata() -> None:
    record = parse_element_definition("VariableAction")

    assert record["element"] == "VariableAction"
    assert record["content_model_kind"] == "choice"
    assert record["required_attributes"][0]["name"] == "variableRef"


def test_parse_license_extracts_simple_content_extension_attributes() -> None:
    record = parse_element_definition("License")

    assert record["required_attributes"] == [{"name": "name", "type": "String"}]
    assert record["optional_attributes"] == [
        {"name": "resource", "type": "String"},
        {"name": "spdxId", "type": "String"},
    ]


def test_parse_traffic_distribution_preserves_choice_occurrence_bounds() -> None:
    record = parse_element_definition("TrafficDistribution")

    assert record["child_groups"] == [
        {
            "members": ["TrafficDistributionEntry", "CatalogReferences"],
            "cardinality": "1..2",
        }
    ]
    assert record["semantic_constraints"] == [
        "Select 1 to 2 branches from: TrafficDistributionEntry, CatalogReferences."
    ]


def test_schema_scope_tracks_full_element_population() -> None:
    payload = json.loads(
        Path("knowledge/structured/schema_scope.json").read_text(encoding="utf-8")
    )

    assert payload["mode"] == "full"
    assert payload["xsd_element_count"] == 302
    assert len(payload["represented_xsd_elements"]) == 302
    assert len(payload["elements"]) == 301
    assert payload["alias_collisions"]["OpenScenario"] == "OpenSCENARIO"


def test_domain_manifests_partition_every_structured_element_once() -> None:
    manifests = sorted(Path("knowledge/structured/manifests").glob("domain-*.txt"))

    assert len(manifests) == 5

    assigned: list[str] = []
    for manifest in manifests:
        entries = [
            line.strip()
            for line in manifest.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert entries == sorted(entries)
        assert len(entries) == len(set(entries))
        assigned.extend(entries)

    structured_elements = sorted(
        path.stem for path in Path("knowledge/structured/elements").glob("*.json")
    )

    assert sorted(assigned) == structured_elements
