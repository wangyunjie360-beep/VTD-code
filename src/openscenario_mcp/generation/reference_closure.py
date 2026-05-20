from __future__ import annotations

from typing import Any


def build_reference_closure(intent: dict[str, Any]) -> dict[str, list[str]]:
    entities = [
        str(entity.get("name", "")).strip()
        for entity in intent.get("entities", [])
        if isinstance(entity, dict) and str(entity.get("name", "")).strip()
    ]
    parameters = [
        str(parameter.get("name", "")).strip()
        for parameter in intent.get("parameters", [])
        if isinstance(parameter, dict) and str(parameter.get("name", "")).strip()
    ]
    return {
        "entity_names": _dedupe(entities),
        "parameter_names": _dedupe(parameters),
        "variable_names": [],
        "controller_names": [],
    }


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


__all__ = ["build_reference_closure"]
