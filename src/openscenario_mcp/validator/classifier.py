from __future__ import annotations

import json
import re
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

from openscenario_mcp.config import get_project_root
from openscenario_mcp.generation.strategy import build_element_strategy
from openscenario_mcp.models import ElementRecord

_PATTERNS_RELATIVE_PATH = Path("knowledge") / "diagnostics" / "patterns.json"
_KNOWN_ELEMENTS_RELATIVE_PATH = Path("knowledge") / "structured" / "elements"


@lru_cache(maxsize=1)
def load_patterns() -> list[dict[str, Any]]:
    pattern_path = get_project_root() / _PATTERNS_RELATIVE_PATH
    return json.loads(pattern_path.read_text(encoding="utf-8"))


def classify_error(
    error: Mapping[str, Any] | object,
    patterns: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    payload = _extract_payload(error)
    message = payload["message"]
    rule_hint = payload["rule_hint"]
    diagnostic: dict[str, Any] = {
        "category": "unknown_validation_issue",
        "line": payload["line"],
        "column": payload["column"],
        "message": message,
        "rule_hint": rule_hint,
        "fix_advice": (
            "Review the validator message and compare the XML against the schema "
            "for the failing element."
        ),
    }

    active_patterns = patterns if patterns is not None else load_patterns()

    for pattern in active_patterns:
        match = _compile_regex(str(pattern["regex"])).search(message)
        if match is None:
            continue

        extracted = _normalize_groups(match.groupdict())
        if not _pattern_applies(pattern, extracted):
            continue

        category = str(pattern["category"])
        diagnostic.update(_category_fields(category, extracted, rule_hint=rule_hint))
        diagnostic["category"] = category
        diagnostic["fix_advice"] = _render_fix_advice(
            str(pattern["fix_advice_template"]),
            diagnostic,
        )
        repair_strategy = _build_repair_strategy(diagnostic)
        if repair_strategy is not None:
            diagnostic["repair_strategy"] = repair_strategy
        return diagnostic

    if rule_hint and "expected" not in diagnostic:
        diagnostic["expected"] = [rule_hint]

    repair_strategy = _build_repair_strategy(diagnostic)
    if repair_strategy is not None:
        diagnostic["repair_strategy"] = repair_strategy

    return diagnostic


def _extract_payload(error: Mapping[str, Any] | object) -> dict[str, Any]:
    if isinstance(error, Mapping):
        payload = error
        raw_message = payload.get("message")
        raw_line = payload.get("line")
        raw_column = payload.get("column")
        raw_rule_hint = payload.get("rule_hint")
    else:
        raw_message = getattr(error, "message", None)
        raw_line = getattr(error, "line", None)
        raw_column = getattr(error, "column", None)
        raw_rule_hint = getattr(error, "rule_hint", None)

    return {
        "message": str(raw_message) if raw_message else str(error),
        "line": _coerce_optional_int(raw_line),
        "column": _coerce_optional_int(raw_column),
        "rule_hint": str(raw_rule_hint) if raw_rule_hint not in (None, "") else None,
    }


def _normalize_groups(
    groups: dict[str, str | None],
) -> dict[str, Any]:
    extracted = {
        key: value.strip()
        for key, value in groups.items()
        if isinstance(value, str) and value.strip()
    }

    expected_text = extracted.get("expected_text")
    if expected_text:
        extracted["expected"] = _split_expected(expected_text)

    if "one_of" in extracted:
        extracted["expects_one_of"] = True
        extracted.pop("one_of", None)

    if "expected" in extracted:
        extracted["expected_text"] = ", ".join(extracted["expected"])

    return extracted


def _category_fields(
    category: str,
    extracted: dict[str, Any],
    *,
    rule_hint: str | None,
) -> dict[str, Any]:
    fields = dict(extracted)
    expects_one_of = bool(fields.pop("expects_one_of", False))

    if category in {
        "missing_required_child",
        "unexpected_element",
        "wrong_child_order",
    } and "expected" not in fields and rule_hint:
        fields["expected"] = _split_expected(rule_hint)
        fields["expected_text"] = ", ".join(fields["expected"])

    if category == "missing_required_child":
        expected = list(fields.get("expected", []))
        choice_group = _find_choice_group(fields.get("element"), expected)

        if choice_group or expects_one_of:
            fields["requirement_kind"] = "one_of"
            fields["required_one_of"] = choice_group or expected
            fields["required_child_description"] = (
                "one of the listed elements is required: "
                f"{', '.join(fields['required_one_of'])}"
            )
        else:
            fields["requirement_kind"] = "all_of"
            fields["missing"] = expected
            fields["required_child_description"] = (
                "the required child element(s): "
                f"{', '.join(fields['missing'])}"
            )

    return fields


def _pattern_applies(pattern: Mapping[str, Any], extracted: Mapping[str, Any]) -> bool:
    known_elements = _load_known_elements()

    if pattern.get("requires_known_element"):
        element = extracted.get("element")
        if element not in known_elements:
            return False

    if pattern.get("requires_expected_known"):
        expected = extracted.get("expected", [])
        if not expected or any(item not in known_elements for item in expected):
            return False

    excluded_expected = {
        str(item) for item in pattern.get("exclude_expected", []) if str(item)
    }
    if excluded_expected and any(
        expected in excluded_expected for expected in extracted.get("expected", [])
    ):
        return False

    if pattern.get("requires_structural_order_match") and not _has_ordered_sibling_context(
        extracted.get("element"),
        extracted.get("expected", []),
    ):
        return False

    return True


@lru_cache(maxsize=None)
def _compile_regex(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern)


@lru_cache(maxsize=1)
def _load_known_elements() -> frozenset[str]:
    return frozenset(_load_element_definitions())


@lru_cache(maxsize=1)
def _load_element_definitions() -> dict[str, dict[str, Any]]:
    elements_dir = get_project_root() / _KNOWN_ELEMENTS_RELATIVE_PATH
    if not elements_dir.is_dir():
        return {}
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in elements_dir.glob("*.json")
    }


def _build_repair_strategy(diagnostic: Mapping[str, Any]) -> dict[str, Any] | None:
    element = diagnostic.get("element")
    if not isinstance(element, str):
        return None

    definition = _load_element_definitions().get(element)
    if definition is None:
        return None

    record = ElementRecord(**definition)
    focus_strategy = build_element_strategy(record)
    recommended_actions = _recommended_actions_for_diagnostic(
        diagnostic,
        focus_strategy=focus_strategy,
    )

    strategy: dict[str, Any] = {
        "focus_element": element,
        "focus_strategy": focus_strategy,
        "expected_elements": _expected_elements_for_diagnostic(diagnostic),
        "recommended_actions": recommended_actions,
    }
    return strategy


def _expected_elements_for_diagnostic(diagnostic: Mapping[str, Any]) -> list[str]:
    for key in ("required_one_of", "missing", "expected"):
        value = diagnostic.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, str)]
    return []


def _recommended_actions_for_diagnostic(
    diagnostic: Mapping[str, Any],
    *,
    focus_strategy: Mapping[str, Any],
) -> list[str]:
    category = str(diagnostic.get("category", ""))
    reference_requirements = focus_strategy.get("reference_requirements", [])
    attribute = str(diagnostic.get("attribute", "")).strip()

    if category == "missing_required_child":
        if diagnostic.get("requirement_kind") == "one_of":
            return ["satisfy_choice_cardinality"]
        actions: list[str] = ["add_required_children"]
        ordering = focus_strategy.get("ordering", {})
        if isinstance(ordering, Mapping) and ordering.get("mode") == "sequence":
            actions.append("enforce_sequence_order")
        return actions

    if category == "missing_required_attribute":
        if any(
            isinstance(requirement, Mapping)
            and requirement.get("name") == attribute
            and requirement.get("reference_kind")
            for requirement in reference_requirements
        ):
            return ["add_required_references"]
        return ["add_required_attributes"]

    if category == "wrong_child_order":
        return ["enforce_sequence_order"]
    if category == "invalid_attribute":
        return ["remove_invalid_attributes"]
    if category == "invalid_enum_value":
        return ["replace_invalid_enum_value"]
    if category == "unexpected_element":
        return ["review_expected_elements"]
    if category == "namespace_or_root_issue":
        return ["align_root_element_and_namespace"]

    return list(focus_strategy.get("repair_priority", []))


def _has_ordered_sibling_context(
    element: object,
    expected: object,
) -> bool:
    if not isinstance(element, str) or not isinstance(expected, list):
        return False

    expected_names = [item for item in expected if isinstance(item, str)]
    if not expected_names:
        return False

    for definition in _load_element_definitions().values():
        child_slots = _child_order_slots(definition)
        element_index = _find_child_slot_index(element, child_slots)
        if element_index is None:
            continue

        for expected_name in expected_names:
            expected_index = _find_child_slot_index(expected_name, child_slots)
            if expected_index is not None and expected_index < element_index:
                return True

    return False


def _find_choice_group(
    element: object,
    expected: list[str],
) -> list[str] | None:
    if not isinstance(element, str) or not expected:
        return None

    definition = _load_element_definitions().get(element)
    if definition is None:
        return None

    expected_set = set(expected)
    for slot in _child_order_slots(definition):
        if len(slot) <= 1:
            continue
        if expected_set == set(slot) and len(expected_set) == len(slot):
            return expected

    return None


def _child_order_slots(definition: Mapping[str, Any]) -> list[tuple[str, ...]]:
    raw_child_order = definition.get("child_order", [])
    if not isinstance(raw_child_order, list):
        return []

    return [
        tuple(item.strip() for item in str(slot).split("|") if item.strip())
        for slot in raw_child_order
    ]


def _find_child_slot_index(
    child_name: str,
    child_slots: list[tuple[str, ...]],
) -> int | None:
    for index, slot in enumerate(child_slots):
        if child_name in slot:
            return index
    return None


def _split_expected(raw_value: str) -> list[str]:
    return [
        item.strip()
        for item in re.split(r"\s*\|\s*|\s*,\s*", raw_value)
        if item.strip()
    ]


def _render_fix_advice(template: str, diagnostic: Mapping[str, Any]) -> str:
    return template.format_map(_FormatMap(diagnostic))


def _coerce_optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class _FormatMap(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "unknown"
