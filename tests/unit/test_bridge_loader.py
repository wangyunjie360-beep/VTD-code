from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any, get_type_hints

import pytest

from openscenario_mcp.config import get_project_root
from openscenario_mcp.models import OscVtdBridgeKnowledgeBase
from openscenario_mcp.runtime import (
    Runtime,
    _BRIDGE_RELATIVE_PATH,
    _load_osc_vtd_bridge_knowledge_base,
    build_runtime_for_tests,
)

_FIRST_BATCH_BINDING_IDS = {
    "osc-vtd-binding:ScenarioObject:name",
    "osc-vtd-binding:Vehicle:model3d",
    "osc-vtd-binding:ExternalObjectReference:name",
    "osc-vtd-binding:TrafficSignalController:name",
    "osc-vtd-binding:TrafficSignalStateAction:name",
}
_FIRST_BATCH_FIELDS = {
    ("ScenarioObject", "name"),
    ("Vehicle", "model3d"),
    ("ExternalObjectReference", "name"),
    ("TrafficSignalController", "name"),
    ("TrafficSignalStateAction", "name"),
}


def _load_repo_bridge() -> Any:
    try:
        bridge_loader = import_module("openscenario_mcp.knowledge.bridge_loader")
    except ModuleNotFoundError as exc:
        pytest.fail(f"Missing bridge loader module: {exc}")

    return bridge_loader.load_osc_vtd_bridge(get_project_root() / _BRIDGE_RELATIVE_PATH)


def test_phase2_bridge_output_directory_is_reserved_under_project_root() -> None:
    project_root = get_project_root()

    assert _BRIDGE_RELATIVE_PATH.as_posix() == "knowledge/structured/bridges/osc_vtd"
    assert (project_root / _BRIDGE_RELATIVE_PATH).is_dir()


def test_bridge_loader_reads_first_batch_bindings_from_repo_snapshot() -> None:
    bridge = _load_repo_bridge()
    bridge_root = get_project_root() / _BRIDGE_RELATIVE_PATH

    assert isinstance(bridge, OscVtdBridgeKnowledgeBase)
    assert set(bridge.rules_by_id) == _FIRST_BATCH_BINDING_IDS
    assert set(bridge.bindings_by_field) == _FIRST_BATCH_FIELDS
    assert ("TrafficSignalAction", "name") not in bridge.bindings_by_field

    scenario_object_rule = bridge.rules_by_id["osc-vtd-binding:ScenarioObject:name"]
    assert scenario_object_rule.namespace == "scenario_object"
    assert scenario_object_rule.constraint_mode == "soft"

    vehicle_rule = bridge.rules_by_id["osc-vtd-binding:Vehicle:model3d"]
    assert vehicle_rule.binding_kind == "asset_reference"
    assert vehicle_rule.namespace == "runtime_asset"
    assert vehicle_rule.asset_kind == "model"

    external_object_rule = bridge.rules_by_id[
        "osc-vtd-binding:ExternalObjectReference:name"
    ]
    assert external_object_rule.namespace == "external_object"
    assert external_object_rule.constraint_mode == "soft"

    controller_rule = bridge.rules_by_id["osc-vtd-binding:TrafficSignalController:name"]
    assert controller_rule.binding_kind == "controller_reference"
    assert controller_rule.namespace == "traffic_signal_controller"

    signal_state_rule = bridge.rules_by_id[
        "osc-vtd-binding:TrafficSignalStateAction:name"
    ]
    assert signal_state_rule.namespace == "runtime_asset"
    assert signal_state_rule.asset_kind == "signal"

    assert [source.path for source in bridge.sources] == [
        "knowledge/structured/bridges/osc_vtd/field-bindings.jsonl",
        "knowledge/structured/bridges/osc_vtd/generation-policies.jsonl",
        "knowledge/structured/bridges/osc_vtd/guidance-recipes.jsonl",
    ]
    assert bridge.metadata["status"] == "loaded"
    assert bridge.metadata["exists"] is True
    assert Path(bridge.metadata["root"]) == bridge_root
    assert isinstance(bridge.metadata["generation_policies"], list)
    assert isinstance(bridge.metadata["guidance_recipes"], list)
    assert {policy["policy_id"] for policy in bridge.metadata["generation_policies"]} == {
        "osc-vtd-generation:entity-names",
        "osc-vtd-generation:runtime-assets",
        "osc-vtd-generation:traffic-signal-controller-closure",
    }
    assert {recipe["recipe_id"] for recipe in bridge.metadata["guidance_recipes"]} == {
        "osc-vtd-guidance:vehicle-model3d",
        "osc-vtd-guidance:scenario-object-name",
        "osc-vtd-guidance:traffic-signal-state-name",
    }


def test_runtime_loads_real_bridge_layer_when_bridge_files_exist() -> None:
    runtime_hints = get_type_hints(Runtime)
    runtime = build_runtime_for_tests()
    bridge_root = get_project_root() / _BRIDGE_RELATIVE_PATH

    assert runtime_hints["osc_vtd_bridge_knowledge_base"] is OscVtdBridgeKnowledgeBase
    assert isinstance(runtime.osc_vtd_bridge_knowledge_base, OscVtdBridgeKnowledgeBase)
    assert set(runtime.osc_vtd_bridge_knowledge_base.rules_by_id) == _FIRST_BATCH_BINDING_IDS
    assert set(runtime.osc_vtd_bridge_knowledge_base.bindings_by_field) == _FIRST_BATCH_FIELDS
    assert runtime.osc_vtd_bridge_knowledge_base.metadata["status"] == "loaded"
    assert runtime.osc_vtd_bridge_knowledge_base.metadata["exists"] is True
    assert Path(runtime.osc_vtd_bridge_knowledge_base.metadata["root"]) == bridge_root


def test_bridge_placeholder_loader_stays_stable_when_bridge_files_are_missing(
    tmp_path: Path,
) -> None:
    bridge_dir = tmp_path / _BRIDGE_RELATIVE_PATH
    bridge_dir.mkdir(parents=True, exist_ok=True)
    (bridge_dir / "field-bindings.jsonl").write_text("", encoding="utf-8")

    bridge_knowledge_base = _load_osc_vtd_bridge_knowledge_base(tmp_path)

    assert isinstance(bridge_knowledge_base, OscVtdBridgeKnowledgeBase)
    assert bridge_knowledge_base.rules_by_id == {}
    assert bridge_knowledge_base.bindings_by_field == {}
    assert bridge_knowledge_base.sources[0].id == "osc-vtd-bridge"
    assert bridge_knowledge_base.sources[0].kind == "bridge"
    assert bridge_knowledge_base.sources[0].path == "knowledge/structured/bridges/osc_vtd"
    assert bridge_knowledge_base.metadata["status"] == "placeholder"
    assert bridge_knowledge_base.metadata["exists"] is True
    assert Path(bridge_knowledge_base.metadata["root"]) == tmp_path / _BRIDGE_RELATIVE_PATH
