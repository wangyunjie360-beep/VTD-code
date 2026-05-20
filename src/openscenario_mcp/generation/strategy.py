from __future__ import annotations

from typing import Any

from openscenario_mcp.models import ElementRecord


def build_element_strategy(
    record: ElementRecord,
    parent_context: str | None = None,
) -> dict[str, Any]:
    structure_mode = _infer_structure_mode(record)
    branch_selection = _build_branch_selection(record, structure_mode)
    ordering = _build_ordering(record, structure_mode)
    variant_resolution = _build_variant_resolution(record, parent_context)
    reference_requirements = _build_reference_requirements(record)
    required_children = _build_required_children(record)

    return {
        "structure_mode": structure_mode,
        "branch_selection": branch_selection,
        "ordering": ordering,
        "required_children": required_children,
        "variant_resolution": variant_resolution,
        "reference_requirements": reference_requirements,
        "repair_priority": _build_repair_priority(
            has_variants=variant_resolution["selection_required"],
            has_choice=branch_selection["mode"] != "none",
            has_references=bool(reference_requirements),
            has_required_children=bool(required_children),
            enforce_sequence=ordering["mode"] == "sequence",
        ),
    }


def _infer_structure_mode(record: ElementRecord) -> str:
    if record.content_model_kind:
        return record.content_model_kind
    if record.child_order:
        return "sequence"
    if record.allowed_children:
        return "children"
    return "leaf"


def _build_branch_selection(
    record: ElementRecord,
    structure_mode: str,
) -> dict[str, Any]:
    if structure_mode != "choice" or not record.child_groups:
        return {"mode": "none", "groups": []}

    groups = [
        {
            "members": list(group.get("members", [])),
            "min_branches": minimum,
            "max_branches": maximum,
        }
        for group in record.child_groups
        for minimum, maximum in [_parse_cardinality(str(group.get("cardinality", "1..1")))]
    ]

    if all(
        group["min_branches"] == 1 and group["max_branches"] == 1 for group in groups
    ):
        mode = "single"
    elif all(
        group["min_branches"] == 0 and group["max_branches"] == 1 for group in groups
    ):
        mode = "optional_single"
    elif any(group["max_branches"] is None for group in groups):
        mode = "multiple"
    else:
        mode = "bounded"

    return {"mode": mode, "groups": groups}


def _build_ordering(
    record: ElementRecord,
    structure_mode: str,
) -> dict[str, Any]:
    if structure_mode == "sequence" or record.child_order:
        return {"mode": "sequence", "child_order": list(record.child_order)}
    if structure_mode == "all":
        return {"mode": "all", "child_order": []}
    return {"mode": "none", "child_order": []}


def _build_variant_resolution(
    record: ElementRecord,
    parent_context: str | None,
) -> dict[str, Any]:
    variants = [dict(variant) for variant in record.contextual_variants]
    non_deprecated = [variant for variant in variants if not variant.get("deprecated")]
    deprecated = [variant for variant in variants if variant.get("deprecated")]

    resolved_variant: dict[str, Any] | None = None
    preferred_variants = non_deprecated or deprecated
    if parent_context is not None:
        matching_non_deprecated = [
            variant
            for variant in non_deprecated
            if variant.get("parent_context") == parent_context
        ]
        matching_deprecated = [
            variant
            for variant in deprecated
            if variant.get("parent_context") == parent_context
        ]
        if matching_non_deprecated:
            preferred_variants = matching_non_deprecated
            resolved_variant = matching_non_deprecated[0]
        elif matching_deprecated:
            preferred_variants = matching_deprecated
            resolved_variant = matching_deprecated[0]
        else:
            preferred_variants = [
                variant for variant in non_deprecated if variant.get("parent_context")
            ] or non_deprecated or matching_deprecated or deprecated

    return {
        "selection_required": bool(variants),
        "parent_context": parent_context,
        "resolved_variant": resolved_variant,
        "preferred_variants": preferred_variants,
        "deprecated_variants": deprecated,
    }


def _build_reference_requirements(record: ElementRecord) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    required_names = {
        str(attribute.get("name", "")).strip()
        for attribute in record.required_attributes
        if str(attribute.get("name", "")).strip()
    }

    for attribute in (*record.required_attributes, *record.optional_attributes):
        name = str(attribute.get("name", "")).strip()
        reference_kind = str(attribute.get("reference_kind", "")).strip()
        if not name or not reference_kind:
            continue
        requirements.append(
            {
                "name": name,
                "reference_kind": reference_kind,
                "required": name in required_names,
            }
        )

    return requirements


def _build_required_children(record: ElementRecord) -> list[str]:
    required_children: list[str] = []
    for child in record.allowed_children:
        child_name = str(child.get("name", "")).strip()
        if not child_name:
            continue

        cardinality = str(
            child.get("cardinality") or record.multiplicity.get(child_name, "")
        ).strip()
        minimum, _ = _parse_cardinality(cardinality)
        if minimum >= 1:
            required_children.append(child_name)

    return required_children


def _build_repair_priority(
    *,
    has_variants: bool,
    has_choice: bool,
    has_references: bool,
    has_required_children: bool,
    enforce_sequence: bool,
) -> list[str]:
    priorities: list[str] = []

    if has_variants:
        priorities.append("resolve_contextual_variant")
    if has_choice:
        priorities.append("satisfy_choice_cardinality")
    if has_references:
        priorities.append("add_required_references")
    if has_required_children:
        priorities.append("add_required_children")
    if enforce_sequence:
        priorities.append("enforce_sequence_order")

    return priorities


def _parse_cardinality(cardinality: str) -> tuple[int, int | None]:
    minimum_text, _, maximum_text = cardinality.partition("..")
    minimum = int(minimum_text or "0")
    if maximum_text in {"*", "unbounded"}:
        return minimum, None
    if not maximum_text:
        return minimum, minimum
    return minimum, int(maximum_text)


__all__ = ["build_element_strategy"]
