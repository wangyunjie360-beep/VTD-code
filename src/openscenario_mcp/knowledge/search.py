from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from openscenario_mcp.generation.strategy import build_element_strategy
from openscenario_mcp.models import ElementRecord, KnowledgeBase

SUPPORTED_RETRIEVE_SPEC_KINDS = frozenset({"element", "attribute", "error", "concept"})
_DEFAULT_PATTERN_SOURCE_PATH = "knowledge/diagnostics/patterns.json"
_CAMEL_CASE_BOUNDARY_PATTERN = re.compile(
    r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])"
)
_NON_ALNUM_PATTERN = re.compile(r"[^A-Za-z0-9]+")
_PLACEHOLDER_PATTERN = re.compile(r"{([^{}]+)}")
_GENERIC_FIX_VALUES = {
    "attribute": "the attribute",
    "element": "the element",
    "expected_text": "the expected element",
    "invalid_value": "the invalid value",
    "required_child_description": "the required child element",
    "type_name": "the declared type",
}


@dataclass(frozen=True, slots=True)
class _SearchCandidate:
    title: str
    kind: str
    source_path: str
    source_paths: tuple[str, ...]
    summary: str
    constraints: tuple[str, ...]
    keywords: tuple[str, ...]
    text: str
    parent_contexts: tuple[str, ...] = ()
    strategy_summary: tuple[str, ...] = ()


def search_spec_records(
    query: str,
    knowledge_base: KnowledgeBase,
    diagnostic_patterns: Sequence[Mapping[str, Any]] | None = None,
    *,
    kind: str | None = None,
    top_k: int = 5,
    parent_context: str | None = None,
) -> list[dict[str, Any]]:
    normalized_kind = _normalize_kind(kind)
    if top_k <= 0:
        return []

    normalized_query = _normalize_text(query)
    if not normalized_query:
        return []

    candidates = tuple(
        _iter_candidates(
            knowledge_base,
            diagnostic_patterns or (),
            kind=normalized_kind,
            parent_context=parent_context,
        )
    )

    scored = [
        (score, candidate)
        for candidate in candidates
        if (score := _score_candidate(normalized_query, candidate)) > 0
    ]
    scored.sort(key=lambda item: (-item[0], item[1].kind, item[1].title.lower()))

    return [
        {
            "title": candidate.title,
            "kind": candidate.kind,
            "source_path": candidate.source_path,
            "source_paths": list(candidate.source_paths),
            "summary": candidate.summary,
            "constraints": list(candidate.constraints),
            **(
                {"parent_contexts": list(candidate.parent_contexts)}
                if candidate.parent_contexts
                else {}
            ),
            **(
                {"strategy_summary": list(candidate.strategy_summary)}
                if candidate.strategy_summary
                else {}
            ),
        }
        for _, candidate in scored[:top_k]
    ]


def _iter_candidates(
    knowledge_base: KnowledgeBase,
    diagnostic_patterns: Sequence[Mapping[str, Any]],
    *,
    kind: str | None,
    parent_context: str | None,
) -> Iterable[_SearchCandidate]:
    requested_kinds = (
        ("element", "attribute", "error")
        if kind is None
        else (kind,)
    )

    if "element" in requested_kinds:
        yield from _iter_element_candidates(knowledge_base, parent_context=parent_context)
    if "attribute" in requested_kinds:
        yield from _iter_attribute_candidates(knowledge_base)
    if "error" in requested_kinds:
        yield from _iter_error_candidates(diagnostic_patterns)
    if "concept" in requested_kinds:
        yield from _iter_concept_candidates(knowledge_base, parent_context=parent_context)


def _iter_element_candidates(
    knowledge_base: KnowledgeBase,
    *,
    parent_context: str | None,
) -> Iterable[_SearchCandidate]:
    for record in knowledge_base.records_by_element.values():
        yield _SearchCandidate(
            title=record.element,
            kind="element",
            source_path=_record_source_path(record),
            source_paths=_record_source_paths(record),
            summary=record.description or f"{record.element} element.",
            constraints=_element_constraints(record),
            keywords=_record_keywords(record),
            text=_record_search_text(record),
            parent_contexts=tuple(record.parent_contexts),
            strategy_summary=_strategy_summary(
                build_element_strategy(record, parent_context=parent_context)
            ),
        )


def _iter_concept_candidates(
    knowledge_base: KnowledgeBase,
    *,
    parent_context: str | None,
) -> Iterable[_SearchCandidate]:
    for record in knowledge_base.records_by_element.values():
        yield _SearchCandidate(
            title=record.element,
            kind="concept",
            source_path=_record_source_path(record),
            source_paths=_record_source_paths(record),
            summary=record.description or f"{record.element} concept.",
            constraints=_element_constraints(record),
            keywords=(record.element, *record.parent_contexts),
            text=" ".join(
                part
                for part in (
                    record.description,
                    " ".join(record.parent_contexts),
                    " ".join(_attribute_names(record)),
                    " ".join(_child_names(record)),
                )
                if part
            ),
            parent_contexts=tuple(record.parent_contexts),
            strategy_summary=_strategy_summary(
                build_element_strategy(record, parent_context=parent_context)
            ),
        )


def _iter_attribute_candidates(knowledge_base: KnowledgeBase) -> Iterable[_SearchCandidate]:
    for record in knowledge_base.records_by_element.values():
        required_names = {
            str(attribute.get("name", "")).strip()
            for attribute in record.required_attributes
            if str(attribute.get("name", "")).strip()
        }
        for attribute in (*record.required_attributes, *record.optional_attributes):
            name = str(attribute.get("name", "")).strip()
            if not name:
                continue

            type_name = str(attribute.get("type", "")).strip()
            reference_kind = str(attribute.get("reference_kind", "")).strip()
            required = name in required_names
            requirement_label = "Required" if required else "Optional"
            summary_parts = [f"{requirement_label} attribute '{name}' on {record.element}."]
            if type_name:
                summary_parts.append(f"Type: {type_name}.")
            if reference_kind:
                summary_parts.append(f"Reference kind: {reference_kind}.")
            if record.description:
                summary_parts.append(record.description)

            constraints = [f"{requirement_label} on {record.element}"]
            if type_name:
                constraints.append(f"Type: {type_name}")
            if reference_kind:
                constraints.append(f"Reference kind: {reference_kind}")
            enum_values = record.enum_constraints.get(name, [])
            if enum_values:
                constraints.append(f"Allowed values: {', '.join(enum_values)}")

            yield _SearchCandidate(
                title=f"{record.element}.{name}",
                kind="attribute",
                source_path=_record_source_path(record),
                source_paths=_record_source_paths(record),
                summary=" ".join(summary_parts),
                constraints=tuple(constraints),
                keywords=(
                    name,
                    f"{record.element}.{name}",
                    record.element,
                    type_name,
                    reference_kind,
                ),
                text=" ".join(
                    part
                    for part in (
                        record.description,
                        requirement_label,
                        type_name,
                        reference_kind,
                        " ".join(record.parent_contexts),
                    )
                    if part
                ),
                parent_contexts=tuple((*record.parent_contexts, record.element)),
            )


def _iter_error_candidates(
    diagnostic_patterns: Sequence[Mapping[str, Any]],
) -> Iterable[_SearchCandidate]:
    for pattern in diagnostic_patterns:
        category = str(pattern.get("category", "")).strip()
        if not category:
            continue

        humanized = _humanize(category)
        regex = str(pattern.get("regex", "")).strip()
        fix_advice_template = str(pattern.get("fix_advice_template", "")).strip()
        summary = f"Validator error topic for {humanized}."
        if fix_advice_template:
            summary = (
                f"{summary} Typical fix: {_generalize_fix_advice(fix_advice_template)}"
            )

        yield _SearchCandidate(
            title=category,
            kind="error",
            source_path=f"{_DEFAULT_PATTERN_SOURCE_PATH}#{category}",
            source_paths=(f"{_DEFAULT_PATTERN_SOURCE_PATH}#{category}",),
            summary=summary,
            constraints=(f"Diagnostic category: {category}",),
            keywords=(category, humanized),
            text=" ".join(part for part in (humanized, regex, fix_advice_template) if part),
            strategy_summary=_error_strategy_summary(category),
        )


def _element_constraints(record: ElementRecord) -> tuple[str, ...]:
    constraints: list[str] = []

    required_attributes = _attribute_names(record.required_attributes)
    if required_attributes:
        constraints.append(f"Required attributes: {', '.join(required_attributes)}")

    required_children = _required_child_names(record)
    if required_children:
        constraints.append(f"Required children: {', '.join(required_children)}")

    if record.content_model_kind:
        constraints.append(f"Content model: {record.content_model_kind}")

    if record.child_groups:
        constraints.extend(
            f"Choice groups: {' | '.join(group.get('members', []))}"
            for group in record.child_groups
            if group.get("members")
        )

    if record.child_order:
        constraints.append(f"Child order: {' -> '.join(record.child_order)}")

    if record.semantic_constraints:
        constraints.extend(record.semantic_constraints)

    if record.contextual_variants:
        if any(variant.get("deprecated") for variant in record.contextual_variants):
            constraints.append("Deprecated variants present")
        constraints.append(
            "Contextual variants: " + _format_contextual_variants(record.contextual_variants)
        )

    return tuple(constraints)


def _required_child_names(record: ElementRecord) -> list[str]:
    required: list[str] = []
    for child in record.allowed_children:
        name = str(child.get("name", "")).strip()
        if not name:
            continue

        cardinality = str(
            child.get("cardinality") or record.multiplicity.get(name, "")
        ).strip()
        if cardinality.startswith("1..") or cardinality == "1":
            required.append(name)
    return required


def _record_keywords(record: ElementRecord) -> tuple[str, ...]:
    return (
        record.element,
        *record.parent_contexts,
        record.content_model_kind,
        *(constraint for constraint in record.semantic_constraints),
        *_attribute_names(record),
        *_child_names(record),
    )


def _record_search_text(record: ElementRecord) -> str:
    return " ".join(
        part
        for part in (
            record.description,
            " ".join(record.parent_contexts),
            record.content_model_kind,
            " ".join(record.semantic_constraints),
            _format_contextual_variants(record.contextual_variants),
            " ".join(_attribute_names(record)),
            " ".join(_child_names(record)),
        )
        if part
    )


def _record_source_path(record: ElementRecord) -> str:
    return record.source_path or f"knowledge/structured/elements/{record.element}.json"


def _record_source_paths(record: ElementRecord) -> tuple[str, ...]:
    return _split_source_paths(_record_source_path(record))


def _split_source_paths(source_path: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in source_path.split(";") if part.strip())


def _attribute_names(
    record_or_attributes: ElementRecord | Sequence[Mapping[str, Any]],
) -> list[str]:
    if isinstance(record_or_attributes, ElementRecord):
        attributes = (
            *record_or_attributes.required_attributes,
            *record_or_attributes.optional_attributes,
        )
    else:
        attributes = record_or_attributes

    return [
        str(attribute.get("name", "")).strip()
        for attribute in attributes
        if str(attribute.get("name", "")).strip()
    ]


def _child_names(record: ElementRecord) -> list[str]:
    return [
        str(child.get("name", "")).strip()
        for child in record.allowed_children
        if str(child.get("name", "")).strip()
    ]


def _score_candidate(query: str, candidate: _SearchCandidate) -> int:
    normalized_title = _normalize_text(candidate.title)
    normalized_keywords = tuple(
        normalized_keyword
        for keyword in candidate.keywords
        if (normalized_keyword := _normalize_text(keyword))
    )
    normalized_text = _normalize_text(f"{candidate.title} {candidate.text}")

    score = 0

    if query == normalized_title:
        score += 160
    if any(query == keyword for keyword in normalized_keywords):
        score += 140
    if query in normalized_title:
        score += 70
    if any(query in keyword for keyword in normalized_keywords):
        score += 55
    if query in normalized_text:
        score += 30

    query_tokens = set(_tokenize(query))
    title_tokens = set(_tokenize(normalized_title))
    keyword_tokens = {
        token for keyword in normalized_keywords for token in _tokenize(keyword)
    }
    text_tokens = set(_tokenize(normalized_text))

    score += 18 * len(query_tokens & title_tokens)
    score += 12 * len(query_tokens & keyword_tokens)
    score += 6 * len(query_tokens & text_tokens)

    if query_tokens and query_tokens <= title_tokens:
        score += 45
    if query_tokens and query_tokens <= keyword_tokens:
        score += 35
    if query_tokens and query_tokens <= text_tokens:
        score += 25

    return score


def _normalize_kind(kind: str | None) -> str | None:
    if kind is None:
        return None
    normalized_kind = kind.strip().lower()
    if normalized_kind not in SUPPORTED_RETRIEVE_SPEC_KINDS:
        raise ValueError(
            "Unsupported retrieve_spec kind: "
            f"{kind}. Expected one of {sorted(SUPPORTED_RETRIEVE_SPEC_KINDS)}."
        )
    return normalized_kind


def _normalize_text(value: str) -> str:
    return " ".join(_tokenize(value))


def _tokenize(value: str) -> list[str]:
    normalized = _CAMEL_CASE_BOUNDARY_PATTERN.sub(" ", value)
    normalized = _NON_ALNUM_PATTERN.sub(" ", normalized)
    return [token.lower() for token in normalized.split() if token]


def _humanize(value: str) -> str:
    return value.replace("_", " ").strip()


def _generalize_fix_advice(template: str) -> str:
    return _PLACEHOLDER_PATTERN.sub(_replace_placeholder, template)


def _replace_placeholder(match: re.Match[str]) -> str:
    return _GENERIC_FIX_VALUES.get(match.group(1), "the relevant value")


def _format_contextual_variants(
    contextual_variants: Sequence[Mapping[str, Any]],
) -> str:
    parts: list[str] = []
    for variant in contextual_variants:
        parent_context = str(variant.get("parent_context", "")).strip()
        type_ref = str(variant.get("type_ref", "")).strip()
        deprecated = bool(variant.get("deprecated"))
        label = " -> ".join(part for part in (parent_context, type_ref) if part)
        if deprecated:
            label = f"{label} (deprecated)"
        if label:
            parts.append(label)
    return "; ".join(parts)


def _strategy_summary(strategy: Mapping[str, Any]) -> tuple[str, ...]:
    summary: list[str] = []

    variant_resolution = strategy.get("variant_resolution", {})
    if isinstance(variant_resolution, Mapping) and variant_resolution.get(
        "selection_required"
    ):
        resolved_variant = variant_resolution.get("resolved_variant")
        if isinstance(resolved_variant, Mapping):
            parent_context = str(resolved_variant.get("parent_context", "")).strip()
            type_ref = str(resolved_variant.get("type_ref", "")).strip()
            deprecated_suffix = " (deprecated)." if resolved_variant.get("deprecated") else "."
            if parent_context and type_ref:
                summary.append(
                    f"Use variant for {parent_context}: {type_ref}{deprecated_suffix}"
                )
        else:
            summary.append(
                "Resolve contextual variant before emitting this shared element name."
            )

    branch_selection = strategy.get("branch_selection", {})
    if isinstance(branch_selection, Mapping):
        for group in branch_selection.get("groups", []):
            if not isinstance(group, Mapping):
                continue
            members = [
                str(member).strip()
                for member in group.get("members", [])
                if str(member).strip()
            ]
            if not members:
                continue
            member_list = ", ".join(members)
            minimum = group.get("min_branches")
            maximum = group.get("max_branches")
            if minimum == 1 and maximum == 1:
                summary.append(f"Select exactly one branch from: {member_list}.")
            elif minimum == 0 and maximum == 1:
                summary.append(f"Select at most one branch from: {member_list}.")
            elif minimum == 0 and maximum is None:
                summary.append(f"Select zero or more branches from: {member_list}.")
            elif minimum == 1 and maximum is None:
                summary.append(f"Select one or more branches from: {member_list}.")
            else:
                summary.append(
                    f"Select {minimum} to {maximum} branches from: {member_list}."
                )

    ordering = strategy.get("ordering", {})
    if isinstance(ordering, Mapping) and ordering.get("mode") == "sequence":
        child_order = [
            str(child).strip()
            for child in ordering.get("child_order", [])
            if str(child).strip()
        ]
        if child_order:
            summary.append(f"Preserve child order: {' -> '.join(child_order)}.")

    required_children = [
        str(child).strip()
        for child in strategy.get("required_children", [])
        if str(child).strip()
    ]
    if required_children:
        summary.append(
            f"Keep required children present: {', '.join(required_children)}."
        )

    reference_requirements = [
        requirement
        for requirement in strategy.get("reference_requirements", [])
        if isinstance(requirement, Mapping) and requirement.get("required")
    ]
    if reference_requirements:
        if len(reference_requirements) == 1:
            requirement = reference_requirements[0]
            summary.append(
                "Wire required "
                f"{requirement.get('reference_kind')} reference: {requirement.get('name')}."
            )
        else:
            formatted = ", ".join(
                f"{requirement.get('reference_kind')}:{requirement.get('name')}"
                for requirement in reference_requirements
            )
            summary.append(f"Wire required references first: {formatted}.")

    return tuple(summary)


def _error_strategy_summary(category: str) -> tuple[str, ...]:
    summaries = {
        "missing_required_child": (
            "Add the expected child element before rewriting unrelated XML.",
            "If the parent is a choice wrapper, satisfy its branch cardinality.",
        ),
        "missing_required_attribute": (
            "Add the missing required attribute before changing sibling structure.",
            "If the attribute is a reference, wire the correct referenced identifier.",
        ),
        "wrong_child_order": ("Reorder children to match the schema sequence.",),
        "invalid_attribute": ("Remove unsupported attributes before retrying validation.",),
        "invalid_enum_value": ("Replace the value with a schema-supported enum literal.",),
        "unexpected_element": (
            "Replace, move, or remove the unexpected element after checking expected siblings.",
        ),
        "namespace_or_root_issue": (
            "Align the root element name and namespace with the schema before further repairs.",
        ),
    }
    return summaries.get(category, ())


__all__ = ["SUPPORTED_RETRIEVE_SPEC_KINDS", "search_spec_records"]
