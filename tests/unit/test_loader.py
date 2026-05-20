import json
from pathlib import Path

from openscenario_mcp.knowledge.loader import load_element_record


def test_load_element_record_returns_children_and_attributes() -> None:
    record = load_element_record(Path("tests/fixtures/knowledge/file_header.json"))

    assert record.element == "FileHeader"
    assert record.required_attributes[3]["name"] == "revMajor"
    assert record.allowed_children[1]["name"] == "Properties"
    assert record.source_path.startswith("knowledge/raw/schema/OpenSCENARIO.xsd#L")


def test_structured_element_corpus_loads_with_matching_filenames() -> None:
    element_paths = sorted(Path("knowledge/structured/elements").glob("*.json"))

    assert element_paths

    for path in element_paths:
        record = load_element_record(path)

        assert record.element == path.stem
        assert record.source_path.startswith("knowledge/raw/schema/OpenSCENARIO.xsd#L")


def test_schema_scope_elements_match_structured_element_files() -> None:
    scope_path = Path("knowledge/structured/schema_scope.json")
    scope_payload = json.loads(scope_path.read_text(encoding="utf-8"))
    file_elements = {
        load_element_record(path).element
        for path in Path("knowledge/structured/elements").glob("*.json")
    }

    assert file_elements == set(scope_payload["elements"])
