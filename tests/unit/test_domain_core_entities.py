import json
from pathlib import Path

from openscenario_mcp.knowledge.loader import load_element_record
from openscenario_mcp.knowledge.xsd_parser import parse_element_definition


MANIFEST_PATH = Path("knowledge/structured/manifests/domain-core-entities.txt")
ELEMENTS_DIR = Path("knowledge/structured/elements")
CORE_DOMAIN_ELEMENTS = MANIFEST_PATH.read_text(encoding="utf-8").splitlines()


def _load_record(element_name: str):
    return load_element_record(ELEMENTS_DIR / f"{element_name}.json")


def _load_payload(element_name: str) -> dict[str, object]:
    return json.loads((ELEMENTS_DIR / f"{element_name}.json").read_text(encoding="utf-8"))


def test_core_domain_records_match_parser_structural_metadata() -> None:
    for element_name in CORE_DOMAIN_ELEMENTS:
        record = _load_record(element_name)
        expected = parse_element_definition(element_name)

        assert record.content_model_kind == expected["content_model_kind"]
        assert record.child_groups == expected["child_groups"]
        assert record.contextual_variants == expected["contextual_variants"]
        assert record.parent_contexts == expected["parent_contexts"]
        assert record.required_attributes == expected["required_attributes"]
        assert record.optional_attributes == expected["optional_attributes"]
        assert record.allowed_children == expected["allowed_children"]
        assert record.child_order == expected["child_order"]
        assert record.multiplicity == expected["multiplicity"]
        assert record.enum_constraints == expected["enum_constraints"]


def test_core_domain_representative_contextual_variants_and_deprecation() -> None:
    catalog_reference = _load_record("CatalogReference")
    pedestrian = _load_record("Pedestrian")
    open_scenario = _load_record("OpenSCENARIO")

    assert catalog_reference.contextual_variants == [
        {
            "parent_context": "AssignControllerAction",
            "type_ref": "CatalogReference",
            "deprecated": False,
        },
        {
            "parent_context": "AssignRouteAction",
            "type_ref": "CatalogReference",
            "deprecated": False,
        },
        {
            "parent_context": "ControllerDistributionEntry",
            "type_ref": "CatalogReference",
            "deprecated": False,
        },
        {
            "parent_context": "EntityObject",
            "type_ref": "CatalogReference",
            "deprecated": False,
        },
        {
            "parent_context": "EnvironmentAction",
            "type_ref": "CatalogReference",
            "deprecated": False,
        },
        {
            "parent_context": "FollowTrajectoryAction",
            "type_ref": "CatalogReference",
            "deprecated": False,
        },
        {
            "parent_context": "ManeuverGroup",
            "type_ref": "CatalogReference",
            "deprecated": False,
        },
        {
            "parent_context": "ObjectController",
            "type_ref": "CatalogReference",
            "deprecated": False,
        },
        {
            "parent_context": "RouteRef",
            "type_ref": "CatalogReference",
            "deprecated": False,
        },
        {
            "parent_context": "TrajectoryRef",
            "type_ref": "CatalogReference",
            "deprecated": False,
        },
    ]
    assert pedestrian.contextual_variants == [
        {
            "parent_context": "Catalog",
            "type_ref": "Pedestrian",
            "deprecated": True,
        },
        {
            "parent_context": "EntityObject",
            "type_ref": "Pedestrian",
            "deprecated": True,
        },
    ]
    assert pedestrian.semantic_constraints == [
        "Some contextual variants of this element are deprecated in the local XSD."
    ]
    assert open_scenario.contextual_variants == [
        {
            "parent_context": "",
            "type_ref": "OpenScenario",
            "deprecated": False,
        }
    ]


def test_core_domain_reference_attributes_are_typed() -> None:
    entity_ref = _load_record("EntityRef")
    private = _load_record("Private")
    parameter_assignment = _load_record("ParameterAssignment")

    assert entity_ref.required_attributes == [
        {
            "name": "entityRef",
            "type": "String",
            "reference_kind": "entity",
        }
    ]
    assert private.required_attributes == [
        {
            "name": "entityRef",
            "type": "String",
            "reference_kind": "entity",
        }
    ]
    assert parameter_assignment.required_attributes[0]["reference_kind"] == "parameter"


def test_core_domain_raw_records_keep_child_references_closed() -> None:
    for element_name in CORE_DOMAIN_ELEMENTS:
        payload = _load_payload(element_name)
        for child in payload.get("allowed_children", []):
            child_name = child["name"]
            assert (ELEMENTS_DIR / f"{child_name}.json").exists(), (
                f"{element_name} references missing child record {child_name}"
            )
