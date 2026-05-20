import importlib
import json
from pathlib import Path
from typing import get_args, get_origin, get_type_hints

import pytest

from openscenario_mcp.knowledge.source_inventory import load_source_inventory
from openscenario_mcp.models import (
    ElementRecord,
    KnowledgeBase,
    ScenarioIntent,
    ValidationError,
)


def test_load_source_inventory_reads_entries(tmp_path: Path) -> None:
    manifest = tmp_path / "source_inventory.json"
    manifest.write_text(
        '{"sources":[{"id":"spec-doc","kind":"doc","path":"knowledge/raw/docs/spec.md"}]}',
        encoding="utf-8",
    )

    inventory = load_source_inventory(manifest)

    assert inventory[0].id == "spec-doc"
    assert inventory[0].kind == "doc"


def test_repo_source_inventory_includes_vtd_runtime_entry() -> None:
    inventory = load_source_inventory(Path("knowledge/source_inventory.json"))
    entries_by_id = {entry.id: entry for entry in inventory}

    assert "vtd-runtime" in entries_by_id
    assert entries_by_id["vtd-runtime"].kind == "runtime"
    assert entries_by_id["vtd-runtime"].path == "knowledge/structured/vtd"


def test_model_contract_matches_task_two_shapes() -> None:
    element_hints = get_type_hints(ElementRecord)
    for field_name in ("required_attributes", "optional_attributes", "allowed_children"):
        field_hint = element_hints[field_name]
        assert get_origin(field_hint) is list
        (item_hint,) = get_args(field_hint)
        assert get_origin(item_hint) is dict

    knowledge_hints = get_type_hints(KnowledgeBase)
    _, record_hint = get_args(knowledge_hints["records_by_element"])
    assert record_hint is ElementRecord

    validation_hints = get_type_hints(ValidationError)
    assert type(None) in get_args(validation_hints["line"])
    assert type(None) in get_args(validation_hints["column"])

    intent_hints = get_type_hints(ScenarioIntent)
    assert get_origin(intent_hints["parameters"]) is list
    assert ScenarioIntent().parameters == []


def test_sample_knowledge_base_uses_canonical_metadata_record(
    sample_knowledge_base: KnowledgeBase,
) -> None:
    record = sample_knowledge_base.records_by_element["Storyboard"]

    assert isinstance(record, ElementRecord)
    assert record.required_attributes[0]["name"] == "name"
    assert record.optional_attributes[0]["name"] == "maximumExecutionCount"
    assert record.allowed_children[0]["name"] == "Init"


def test_write_sample_element_record_json_uses_metadata_shape(
    write_sample_element_record_json,
) -> None:
    record_path = write_sample_element_record_json()
    payload = json.loads(record_path.read_text(encoding="utf-8"))

    assert payload["required_attributes"][0]["name"] == "name"
    assert payload["optional_attributes"][0]["name"] == "maximumExecutionCount"
    assert payload["allowed_children"][0]["name"] == "Init"


def test_tmp_path_is_not_repo_local(tmp_path: Path) -> None:
    assert ".pytest_tmp" not in str(tmp_path)


_SEEN_VALIDATOR_MODULES: set[str] = set()


@pytest.mark.parametrize("case_id", [1, 2])
def test_fake_validator_module_uses_unique_import_path(
    case_id: int,
    fake_validator_module: str,
) -> None:
    assert fake_validator_module not in _SEEN_VALIDATOR_MODULES
    _SEEN_VALIDATOR_MODULES.add(fake_validator_module)

    module = importlib.import_module(fake_validator_module)

    assert module.__name__ == fake_validator_module
    assert module.validate("<OpenSCENARIO />", "1.2")[0]["severity"] == "error"
