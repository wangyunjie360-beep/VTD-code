from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from lxml import etree

from openscenario_mcp.config import get_default_schema_path, get_project_root

_XSD_NS = {"xsd": "http://www.w3.org/2001/XMLSchema"}
_XSD = "{http://www.w3.org/2001/XMLSchema}"
_BUILTIN_TYPES = {
    "xsd:boolean",
    "xsd:dateTime",
    "xsd:double",
    "xsd:int",
    "xsd:string",
    "xsd:unsignedInt",
    "xsd:unsignedShort",
}


@dataclass(frozen=True, slots=True)
class _ContainerModel:
    content_model_kind: str
    allowed_children: tuple[dict[str, Any], ...]
    child_order: tuple[str, ...]
    child_groups: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class _TypeModel:
    required_attributes: tuple[dict[str, Any], ...]
    optional_attributes: tuple[dict[str, Any], ...]
    allowed_children: tuple[dict[str, Any], ...]
    child_order: tuple[str, ...]
    multiplicity: dict[str, str]
    enum_constraints: dict[str, list[str]]
    content_model_kind: str
    child_groups: tuple[dict[str, Any], ...]
    deprecated: bool
    source_lines: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class _SchemaIndex:
    root: etree._Element
    schema_path: Path
    complex_types: dict[str, etree._Element]
    simple_types: dict[str, etree._Element]
    groups: dict[str, etree._Element]
    type_to_element_names: dict[str, tuple[str, ...]]


def parse_element_definition(element_name: str) -> dict[str, Any]:
    index = _load_schema_index()
    occurrences = _find_element_occurrences(index.root, element_name)
    if not occurrences:
        raise ValueError(f"Unknown XSD element: {element_name}")

    type_names = tuple(
        dict.fromkeys(
            type_name
            for occurrence in occurrences
            if (type_name := _resolve_occurrence_type_name(occurrence))
        )
    )
    primary_type = _choose_primary_type(element_name, type_names, index)

    type_models = tuple(
        _parse_type_model(type_name, index)
        for type_name in type_names
        if type_name not in _BUILTIN_TYPES
    )
    primary_model = _parse_type_model(primary_type, index) if primary_type else None

    parent_contexts = sorted(
        {
            context
            for occurrence in occurrences
            for context in _infer_parent_contexts(occurrence, index)
            if context and context != element_name
        }
    )
    source_lines = sorted(
        {
            line
            for occurrence in occurrences
            if (line := occurrence.sourceline) is not None
        }
    )
    if primary_model is not None:
        source_lines.extend(primary_model.source_lines)
    unique_source_lines = tuple(sorted(set(source_lines)))

    required_attributes, optional_attributes = _merge_attributes(type_models)
    allowed_children = _merge_named_dicts(model.allowed_children for model in type_models)
    multiplicity = {
        child["name"]: child["cardinality"]
        for child in allowed_children
        if child.get("name") and child.get("cardinality")
    }
    enum_constraints = _merge_enum_constraints(type_models)
    content_model_kind = (
        primary_model.content_model_kind if primary_model is not None else ""
    )
    child_groups = (
        list(primary_model.child_groups)
        if primary_model is not None
        else _merge_named_group_lists(type_models)
    )
    child_order = (
        list(primary_model.child_order)
        if primary_model is not None
        else _merge_child_order(type_models)
    )

    contextual_variants = _build_contextual_variants(occurrences, index)
    semantic_constraints = _build_semantic_constraints(
        content_model_kind=content_model_kind,
        child_groups=child_groups,
        contextual_variants=contextual_variants,
    )

    description = _build_description(
        element_name=element_name,
        required_attributes=required_attributes,
        allowed_children=allowed_children,
        content_model_kind=content_model_kind,
        child_groups=child_groups,
        contextual_variants=contextual_variants,
    )

    return {
        "element": element_name,
        "description": description,
        "content_model_kind": content_model_kind,
        "child_groups": child_groups,
        "semantic_constraints": semantic_constraints,
        "contextual_variants": contextual_variants,
        "parent_contexts": parent_contexts,
        "required_attributes": required_attributes,
        "optional_attributes": optional_attributes,
        "allowed_children": allowed_children,
        "child_order": child_order,
        "multiplicity": multiplicity,
        "enum_constraints": enum_constraints,
        "source_path": _format_source_path(index.schema_path, unique_source_lines),
    }


@lru_cache(maxsize=1)
def _load_schema_index() -> _SchemaIndex:
    schema_path = get_default_schema_path()
    parser = etree.XMLParser(remove_blank_text=False)
    root = etree.parse(str(schema_path), parser).getroot()

    complex_types = {
        node.get("name"): node
        for node in root.findall("xsd:complexType", _XSD_NS)
        if node.get("name")
    }
    simple_types = {
        node.get("name"): node
        for node in root.findall("xsd:simpleType", _XSD_NS)
        if node.get("name")
    }
    groups = {
        node.get("name"): node
        for node in root.findall("xsd:group", _XSD_NS)
        if node.get("name")
    }

    type_to_element_names: dict[str, list[str]] = {}
    for element in root.findall(".//xsd:element", _XSD_NS):
        type_name = element.get("type")
        element_name = element.get("name")
        if type_name and element_name:
            type_to_element_names.setdefault(type_name, []).append(element_name)

    return _SchemaIndex(
        root=root,
        schema_path=schema_path,
        complex_types=complex_types,
        simple_types=simple_types,
        groups=groups,
        type_to_element_names={
            key: tuple(dict.fromkeys(values))
            for key, values in type_to_element_names.items()
        },
    )


def _find_element_occurrences(root: etree._Element, element_name: str) -> list[etree._Element]:
    return list(root.xpath(f".//xsd:element[@name='{element_name}']", namespaces=_XSD_NS))


def _resolve_occurrence_type_name(occurrence: etree._Element) -> str | None:
    type_name = occurrence.get("type")
    if type_name:
        return type_name

    complex_type = occurrence.find("xsd:complexType", _XSD_NS)
    if complex_type is not None:
        return occurrence.get("name")

    return None


def _choose_primary_type(
    element_name: str,
    type_names: tuple[str, ...],
    index: _SchemaIndex,
) -> str | None:
    if element_name in index.complex_types:
        return element_name
    if element_name in type_names:
        return element_name
    if type_names:
        return type_names[0]
    return None


def _parse_type_model(type_name: str, index: _SchemaIndex) -> _TypeModel:
    node = index.complex_types.get(type_name)
    if node is None:
        return _TypeModel(
            required_attributes=(),
            optional_attributes=(),
            allowed_children=(),
            child_order=(),
            multiplicity={},
            enum_constraints={},
            content_model_kind="",
            child_groups=(),
            deprecated=False,
            source_lines=(),
        )

    required_attributes: list[dict[str, Any]] = []
    optional_attributes: list[dict[str, Any]] = []
    enum_constraints: dict[str, list[str]] = {}
    source_lines: set[int] = set()

    if node.sourceline is not None:
        source_lines.add(node.sourceline)

    content_model = _extract_content_model(node, index)

    for attribute in _iter_attribute_nodes(node):
        payload = _build_attribute_payload(attribute)
        if attribute.get("use") == "required":
            required_attributes.append(payload)
        else:
            optional_attributes.append(payload)

        type_ref = attribute.get("type", "")
        enum_values = _extract_enum_values(type_ref, index)
        if enum_values:
            enum_constraints[payload["name"]] = enum_values
            source_lines.update(_simple_type_source_lines(type_ref, index))

    return _TypeModel(
        required_attributes=tuple(required_attributes),
        optional_attributes=tuple(optional_attributes),
        allowed_children=content_model.allowed_children,
        child_order=content_model.child_order,
        multiplicity={
            child["name"]: child["cardinality"]
            for child in content_model.allowed_children
            if child.get("name") and child.get("cardinality")
        },
        enum_constraints=enum_constraints,
        content_model_kind=content_model.content_model_kind,
        child_groups=content_model.child_groups,
        deprecated=_is_deprecated(node),
        source_lines=tuple(sorted(source_lines)),
    )


def _extract_content_model(
    node: etree._Element,
    index: _SchemaIndex,
) -> _ContainerModel:
    direct_content_model = _extract_direct_content_model(node, index)
    if direct_content_model.content_model_kind:
        return direct_content_model

    extension = _find_extension_node(node)
    if extension is not None:
        return _extract_direct_content_model(extension, index)

    return _ContainerModel("", (), (), ())


def _extract_direct_content_model(
    node: etree._Element,
    index: _SchemaIndex,
) -> _ContainerModel:
    for child in node:
        if not isinstance(child.tag, str):
            continue

        if child.tag == f"{_XSD}sequence":
            return _parse_container(child, "sequence", index)
        if child.tag == f"{_XSD}choice":
            return _parse_container(child, "choice", index)
        if child.tag == f"{_XSD}all":
            return _parse_container(child, "all", index)
        if child.tag == f"{_XSD}group" and child.get("ref"):
            return _parse_group_ref(child, index)

    return _ContainerModel("", (), (), ())


def _find_extension_node(node: etree._Element) -> etree._Element | None:
    for wrapper_tag in ("simpleContent", "complexContent"):
        wrapper = node.find(f"xsd:{wrapper_tag}", _XSD_NS)
        if wrapper is None:
            continue
        extension = wrapper.find("xsd:extension", _XSD_NS)
        if extension is not None:
            return extension
    return None


def _iter_attribute_nodes(node: etree._Element) -> tuple[etree._Element, ...]:
    attributes = list(node.findall("xsd:attribute", _XSD_NS))

    extension = _find_extension_node(node)
    if extension is not None:
        attributes.extend(extension.findall("xsd:attribute", _XSD_NS))

    return tuple(attributes)


def _parse_container(
    container: etree._Element,
    kind: str,
    index: _SchemaIndex,
) -> _ContainerModel:
    allowed_children: list[dict[str, Any]] = []
    child_order: list[str] = []
    child_groups: list[dict[str, Any]] = []

    for child in container:
        if not isinstance(child.tag, str):
            continue

        if child.tag == f"{_XSD}element" and child.get("name"):
            payload = {
                "name": child.get("name"),
                "cardinality": _cardinality(child),
            }
            allowed_children.append(payload)
            if kind == "sequence":
                child_order.append(str(child.get("name")))
        elif child.tag == f"{_XSD}choice":
            nested = _parse_container(child, "choice", index)
            allowed_children.extend(nested.allowed_children)
            child_groups.extend(nested.child_groups)
            if kind == "sequence" and nested.child_groups:
                members = nested.child_groups[0]["members"]
                child_order.append("|".join(members))
        elif child.tag == f"{_XSD}group" and child.get("ref"):
            nested = _parse_group_ref(child, index)
            allowed_children.extend(nested.allowed_children)
            child_groups.extend(nested.child_groups)
            if kind == "sequence" and nested.child_order:
                child_order.extend(nested.child_order)
        elif child.tag == f"{_XSD}sequence":
            nested = _parse_container(child, "sequence", index)
            allowed_children.extend(nested.allowed_children)
            child_groups.extend(nested.child_groups)
            if kind == "sequence":
                child_order.extend(nested.child_order)
        elif child.tag == f"{_XSD}all":
            nested = _parse_container(child, "all", index)
            allowed_children.extend(nested.allowed_children)
            child_groups.extend(nested.child_groups)

    if kind == "choice":
        members = [
            payload["name"]
            for payload in allowed_children
            if payload.get("name")
        ]
        if members:
            child_groups.append(
                {"members": members, "cardinality": _cardinality(container)}
            )
        child_order = ["|".join(members)] if members else []

    if kind == "all":
        child_order = []

    return _ContainerModel(
        content_model_kind=kind,
        allowed_children=tuple(_dedupe_named_dicts(allowed_children)),
        child_order=tuple(child_order),
        child_groups=tuple(child_groups),
    )


def _parse_group_ref(group_ref: etree._Element, index: _SchemaIndex) -> _ContainerModel:
    group_name = group_ref.get("ref", "")
    group = index.groups.get(group_name)
    if group is None:
        return _ContainerModel("", (), (), ())

    for child in group:
        if not isinstance(child.tag, str):
            continue
        if child.tag == f"{_XSD}sequence":
            return _parse_container(child, "sequence", index)
        if child.tag == f"{_XSD}choice":
            return _parse_container(child, "choice", index)
        if child.tag == f"{_XSD}all":
            return _parse_container(child, "all", index)

    return _ContainerModel("", (), (), ())


def _merge_attributes(
    type_models: tuple[_TypeModel, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    required_by_name: dict[str, dict[str, Any]] = {}
    optional_by_name: dict[str, dict[str, Any]] = {}

    for model in type_models:
        for attribute in model.required_attributes:
            required_by_name[attribute["name"]] = dict(attribute)
            optional_by_name.pop(attribute["name"], None)
        for attribute in model.optional_attributes:
            if attribute["name"] not in required_by_name:
                optional_by_name.setdefault(attribute["name"], dict(attribute))

    return (
        sorted(required_by_name.values(), key=lambda item: item["name"]),
        sorted(optional_by_name.values(), key=lambda item: item["name"]),
    )


def _merge_enum_constraints(type_models: tuple[_TypeModel, ...]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for model in type_models:
        for name, values in model.enum_constraints.items():
            merged.setdefault(name, [])
            for value in values:
                if value not in merged[name]:
                    merged[name].append(value)
    return merged


def _merge_named_dicts(
    groups: Any,
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for group in groups:
        for payload in group:
            merged.append(dict(payload))
    return _dedupe_named_dicts(merged)


def _merge_named_group_lists(type_models: tuple[_TypeModel, ...]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[str, ...], str]] = set()
    for model in type_models:
        for group in model.child_groups:
            key = (
                model.content_model_kind,
                tuple(group.get("members", [])),
                str(group.get("cardinality", "")),
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(dict(group))
    return merged


def _merge_child_order(type_models: tuple[_TypeModel, ...]) -> list[str]:
    for model in type_models:
        if model.child_order:
            return list(model.child_order)
    return []


def _build_contextual_variants(
    occurrences: list[etree._Element],
    index: _SchemaIndex,
) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    seen: set[tuple[str, str, bool]] = set()

    for occurrence in occurrences:
        type_name = _resolve_occurrence_type_name(occurrence)
        if not type_name or type_name in _BUILTIN_TYPES:
            continue

        deprecated = _type_is_deprecated(type_name, index)
        parent_contexts = _infer_parent_contexts(occurrence, index) or [""]
        for parent_context in parent_contexts:
            key = (parent_context, type_name, deprecated)
            if key in seen:
                continue
            seen.add(key)
            variants.append(
                {
                    "parent_context": parent_context,
                    "type_ref": type_name,
                    "deprecated": deprecated,
                }
            )

    return variants


def _infer_parent_contexts(
    occurrence: etree._Element,
    index: _SchemaIndex,
) -> list[str]:
    parent = occurrence.getparent()
    while parent is not None:
        if parent.tag == f"{_XSD}complexType" and parent.get("name"):
            container_name = parent.get("name", "")
            element_names = index.type_to_element_names.get(container_name)
            return list(element_names) if element_names else [container_name]
        if parent.tag == f"{_XSD}group" and parent.get("name"):
            return [parent.get("name", "")]
        parent = parent.getparent()
    return []


def _build_attribute_payload(attribute: etree._Element) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": attribute.get("name"),
        "type": attribute.get("type", "String"),
    }
    reference_kind = _infer_reference_kind(attribute.get("name", ""))
    if reference_kind:
        payload["reference_kind"] = reference_kind
    return payload


def _infer_reference_kind(attribute_name: str) -> str | None:
    exact_matches = {
        "parameterRef": "parameter",
        "variableRef": "variable",
        "entityRef": "entity",
        "masterEntityRef": "entity",
        "catalogReference": "catalog",
        "catalogRef": "catalog",
        "controllerRef": "controller",
        "objectControllerRef": "controller",
        "monitorRef": "monitor",
        "storyboardElementRef": "storyboard_element",
        "trafficSignalControllerRef": "traffic_signal_controller",
        "trafficSignalId": "traffic_signal",
        "trajectoryRef": "trajectory",
        "routeRef": "route",
    }
    return exact_matches.get(attribute_name)


def _extract_enum_values(type_name: str, index: _SchemaIndex) -> list[str]:
    simple_type = index.simple_types.get(type_name)
    if simple_type is None:
        return []
    return [
        enum.get("value")
        for enum in simple_type.findall(".//xsd:enumeration", _XSD_NS)
        if enum.get("value")
    ]


def _simple_type_source_lines(type_name: str, index: _SchemaIndex) -> set[int]:
    simple_type = index.simple_types.get(type_name)
    if simple_type is None or simple_type.sourceline is None:
        return set()
    return {simple_type.sourceline}


def _type_is_deprecated(type_name: str, index: _SchemaIndex) -> bool:
    node = index.complex_types.get(type_name)
    if node is None:
        node = index.simple_types.get(type_name)
    return _is_deprecated(node) if node is not None else False


def _is_deprecated(node: etree._Element) -> bool:
    appinfo_nodes = node.xpath(".//xsd:appinfo", namespaces=_XSD_NS)
    return any((node.text or "").strip() == "deprecated" for node in appinfo_nodes)


def _cardinality(node: etree._Element) -> str:
    min_occurs = node.get("minOccurs", "1")
    max_occurs = node.get("maxOccurs", "1")
    return f"{min_occurs}..{max_occurs}"


def _dedupe_named_dicts(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for value in values:
        name = str(value.get("name", ""))
        cardinality = str(value.get("cardinality", ""))
        key = (name, cardinality)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(value)
    return deduped


def _build_semantic_constraints(
    *,
    content_model_kind: str,
    child_groups: list[dict[str, Any]],
    contextual_variants: list[dict[str, Any]],
) -> list[str]:
    constraints: list[str] = []
    if content_model_kind == "choice" and child_groups:
        members = child_groups[0].get("members", [])
        if members:
            constraints.append(
                _build_choice_constraint(
                    child_groups[0].get("cardinality", "1..1"),
                    [str(member) for member in members],
                )
            )

    deprecated_variants = [variant for variant in contextual_variants if variant["deprecated"]]
    if deprecated_variants:
        constraints.append(
            "Some contextual variants of this element are deprecated in the local XSD."
        )
    return constraints


def _build_description(
    *,
    element_name: str,
    required_attributes: list[dict[str, Any]],
    allowed_children: list[dict[str, Any]],
    content_model_kind: str,
    child_groups: list[dict[str, Any]],
    contextual_variants: list[dict[str, Any]],
) -> str:
    if contextual_variants:
        return (
            f"Schema-derived {element_name} element with context-dependent type variants "
            "captured from the local XSD."
        )
    if content_model_kind == "choice" and allowed_children:
        if child_groups:
            members = [str(member) for member in child_groups[0].get("members", [])]
            if members:
                return (
                    f"Schema-derived {element_name} element. "
                    f"{_build_choice_constraint(child_groups[0].get('cardinality', '1..1'), members)}"
                )
        return (
            f"Schema-derived {element_name} element. Exactly one of its allowed child "
            "branches should be selected."
        )
    if allowed_children:
        return (
            f"Schema-derived {element_name} element with child elements defined by the local XSD."
        )
    if required_attributes:
        return (
            f"Schema-derived {element_name} element with XML attributes defined by the local XSD."
        )
    return f"Schema-derived {element_name} element defined by the local XSD."


def _format_source_path(schema_path: Path, lines: tuple[int, ...]) -> str:
    relative_path = schema_path.as_posix()
    try:
        project_relative = schema_path.relative_to(get_project_root())
        relative_path = project_relative.as_posix()
    except ValueError:
        pass

    if not lines:
        return relative_path
    return "; ".join(f"{relative_path}#L{line}" for line in lines)


def _build_choice_constraint(cardinality: str, members: list[str]) -> str:
    member_list = ", ".join(members)
    minimum, _, maximum = cardinality.partition("..")

    if minimum == "1" and maximum == "1":
        return f"Select exactly one of: {member_list}."
    if minimum == "0" and maximum == "1":
        return f"Select at most one of: {member_list}."
    if minimum == "1" and maximum == "unbounded":
        return f"Select one or more branches from: {member_list}."
    if minimum == "0" and maximum == "unbounded":
        return f"Select zero or more branches from: {member_list}."
    return f"Select {minimum} to {maximum} branches from: {member_list}."


__all__ = ["parse_element_definition"]
