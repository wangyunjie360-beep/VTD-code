from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openscenario_mcp.models import OscVtdBindingRule, OscVtdBridgeKnowledgeBase, SourceEntry

_FIELD_BINDINGS_FILE = "field-bindings.jsonl"
_GENERATION_POLICIES_FILE = "generation-policies.jsonl"
_GUIDANCE_RECIPES_FILE = "guidance-recipes.jsonl"
_BRIDGE_SOURCE_ROOT = "knowledge/structured/bridges/osc_vtd"


def load_osc_vtd_bridge(bridge_root: str | Path) -> OscVtdBridgeKnowledgeBase:
    bridge_path = Path(bridge_root)
    rules = _load_binding_rules(bridge_path / _FIELD_BINDINGS_FILE)
    generation_policies = _load_jsonl_objects(
        bridge_path / _GENERATION_POLICIES_FILE,
        _GENERATION_POLICIES_FILE,
    )
    guidance_recipes = _load_jsonl_objects(
        bridge_path / _GUIDANCE_RECIPES_FILE,
        _GUIDANCE_RECIPES_FILE,
    )

    rules_by_id: dict[str, OscVtdBindingRule] = {}
    bindings_by_field: dict[tuple[str, str], list[OscVtdBindingRule]] = {}
    for rule in rules:
        if rule.binding_id in rules_by_id:
            raise ValueError(f"Duplicate OSC-VTD bridge binding id: {rule.binding_id}")
        rules_by_id[rule.binding_id] = rule
        bindings_by_field.setdefault((rule.element, rule.attribute), []).append(rule)

    return OscVtdBridgeKnowledgeBase(
        rules_by_id=rules_by_id,
        bindings_by_field=bindings_by_field,
        sources=[
            SourceEntry(
                id="osc-vtd-field-bindings",
                kind="bridge",
                path=f"{_BRIDGE_SOURCE_ROOT}/{_FIELD_BINDINGS_FILE}",
            ),
            SourceEntry(
                id="osc-vtd-generation-policies",
                kind="bridge",
                path=f"{_BRIDGE_SOURCE_ROOT}/{_GENERATION_POLICIES_FILE}",
            ),
            SourceEntry(
                id="osc-vtd-guidance-recipes",
                kind="bridge",
                path=f"{_BRIDGE_SOURCE_ROOT}/{_GUIDANCE_RECIPES_FILE}",
            ),
        ],
        metadata={
            "root": bridge_path.as_posix(),
            "exists": True,
            "status": "loaded",
            "generation_policies": generation_policies,
            "guidance_recipes": guidance_recipes,
        },
    )


def _load_binding_rules(path: Path) -> list[OscVtdBindingRule]:
    payloads = _load_jsonl_objects(path, _FIELD_BINDINGS_FILE)
    return [
        OscVtdBindingRule(
            binding_id=str(payload.get("binding_id", "")).strip(),
            element=str(payload.get("element", "")).strip(),
            attribute=str(payload.get("attribute", "")).strip(),
            parent_context=str(payload.get("parent_context", "")).strip(),
            binding_kind=str(payload.get("binding_kind", "")).strip(),
            namespace=str(payload.get("namespace", "")).strip(),
            asset_kind=str(payload.get("asset_kind", "")).strip(),
            family_selector=dict(payload.get("family_selector", {})),
            constraint_mode=str(payload.get("constraint_mode", "")).strip(),
            selection_recipe=dict(payload.get("selection_recipe", {})),
            fallback_policy=dict(payload.get("fallback_policy", {})),
        )
        for payload in payloads
    ]


def _load_jsonl_objects(path: Path, bucket_name: str) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f"Missing OSC-VTD bridge bucket '{bucket_name}': {path.as_posix()}")

    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(
                f"OSC-VTD bridge bucket '{bucket_name}' line {line_number} must be a JSON object."
            )
        records.append(payload)
    return records


__all__ = ["load_osc_vtd_bridge"]
