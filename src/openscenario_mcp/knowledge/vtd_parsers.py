from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

_DAT_COLUMN_SPLIT_RE = re.compile(r"\t+| {2,}")
_DAT_SCHEMAS = {
    "signal": {
        "tag": "SIGDEF",
        "required_columns": 16,
        "known_columns": 17,
        "filename_index": 2,
        "group_path_index": 11,
    },
    "external": {
        "tag": "EXTDEF",
        "required_columns": 11,
        "known_columns": 11,
        "filename_index": 3,
        "group_path_index": 8,
    },
}


def parse_resource_dirs(path: str | Path) -> list[dict[str, Any]]:
    resource_path = Path(path)
    source_path = _normalize_source_path(resource_path)
    entries: list[dict[str, Any]] = []

    for line_number, raw_line in enumerate(
        resource_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = _strip_comment_line(raw_line)
        if not line:
            continue

        for raw_entry in line.split(":"):
            resource_dir = _normalize_relative_path(raw_entry)
            if not resource_dir:
                continue
            entries.append(
                {
                    "resource_dir": resource_dir,
                    "source_path": f"{source_path}#L{line_number}",
                }
            )

    return entries


def parse_dat_definitions(
    path: str | Path,
    *,
    definition_kind: str,
) -> list[dict[str, Any]]:
    definition_path = Path(path)
    source_path = _normalize_source_path(definition_path)
    schema = _DAT_SCHEMAS.get(definition_kind)
    if schema is None:
        raise ValueError(f"Unsupported DAT definition kind: {definition_kind}")

    entries: list[dict[str, Any]] = []

    for line_number, raw_line in enumerate(
        definition_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = _strip_comment_line(raw_line)
        if not line:
            continue
        if not line.startswith(f'{schema["tag"]} '):
            continue

        tag, logical_columns = _split_dat_columns(line)
        if tag != schema["tag"] or len(logical_columns) < schema["required_columns"]:
            raise ValueError(
                f"Malformed DAT definition at {source_path}#L{line_number}: "
                f"expected at least {schema['required_columns']} columns for "
                f"{schema['tag']}."
            )

        model_name = logical_columns[0]
        filename = logical_columns[schema["filename_index"]]
        aliases: list[str] = [model_name] if model_name else []
        for extra_column in logical_columns[schema["known_columns"] :]:
            aliases.extend(_split_aliases(extra_column))

        entries.append(
            {
                "definition_kind": definition_kind,
                "tag": tag,
                "filename": filename,
                "canonical_name": _filename_stem(filename),
                "aliases": aliases,
                "group_path": logical_columns[schema["group_path_index"]],
                "source_path": f"{source_path}#L{line_number}",
            }
        )

    return entries


def parse_pbr_objects(path: str | Path) -> list[dict[str, Any]]:
    xml_path = Path(path)
    source_path = _normalize_source_path(xml_path)
    root = ElementTree.parse(xml_path).getroot()
    root_element = _local_name(root.tag)
    entries: list[dict[str, Any]] = []

    for node in root:
        if _local_name(node.tag) != "PBRObject":
            continue
        entries.append(
            {
                "hcs": node.get("hcs", ""),
                "pbr": node.get("pbr", ""),
                "cc": node.get("cc", ""),
                "root_element": root_element,
                "config_kind": "pbr_objects",
                "source_path": source_path,
            }
        )

    return entries


def parse_decal_scatter(path: str | Path) -> list[dict[str, Any]]:
    xml_path = Path(path)
    source_path = _normalize_source_path(xml_path)
    root = ElementTree.parse(xml_path).getroot()
    root_element = _local_name(root.tag)
    entries: list[dict[str, Any]] = []

    for scatterjob in root.findall("./scatterjobs/scatterjob"):
        targettexture = scatterjob.get("targettexture", "")
        for decal in scatterjob.findall("./decals/decal"):
            name = (decal.text or "").strip()
            if not name:
                continue
            entries.append(
                {
                    "name": name,
                    "quantity": decal.get("quantity", ""),
                    "alignment": decal.get("alignment", ""),
                    "targettexture": targettexture,
                    "root_element": root_element,
                    "config_kind": "decal_scatter",
                    "source_path": source_path,
                }
            )

    return entries


def parse_addon_xml_descriptor(path: str | Path) -> dict[str, Any]:
    xml_path = Path(path)
    source_path = _normalize_source_path(xml_path)
    payload = _wrap_xml_fragment(xml_path.read_text(encoding="utf-8"))
    root = ElementTree.fromstring(payload)
    top_level_descriptors: list[dict[str, Any]] = []

    for child in root:
        if not isinstance(child.tag, str):
            continue
        top_level_descriptors.append(
            {
                "element": _local_name(child.tag),
                "attributes": {key: child.attrib[key] for key in sorted(child.attrib)},
            }
        )

    return {
        "top_level_elements": [
            descriptor["element"] for descriptor in top_level_descriptors
        ],
        "top_level_descriptors": top_level_descriptors,
        "source_path": source_path,
        "config_kind": "addon_xml_descriptor",
    }


def _split_dat_columns(line: str) -> tuple[str, list[str]]:
    columns = [
        column.strip()
        for column in _DAT_COLUMN_SPLIT_RE.split(line.strip())
        if column.strip()
    ]
    if not columns:
        return "", []

    leader = columns[0]
    tag, separator, model_name = leader.partition(" ")
    if not separator or not model_name.strip():
        return tag, []
    return tag, [model_name.strip(), *columns[1:]]


def _wrap_xml_fragment(payload: str) -> str:
    text = payload.lstrip("\ufeff").strip()
    if text.startswith("<?xml"):
        _, _, text = text.partition("?>")
        text = text.strip()
    return f"<SyntheticRoot>{text}</SyntheticRoot>"


def _normalize_source_path(path: Path) -> str:
    return path.as_posix()


def _strip_comment_line(raw_line: str) -> str:
    line = raw_line.strip()
    if not line or line.startswith("#") or line.startswith(";"):
        return ""
    return line


def _normalize_relative_path(value: str) -> str:
    normalized = value.strip().replace("\\", "/")
    return normalized.rstrip("/")


def _split_aliases(value: str) -> list[str]:
    aliases: list[str] = []
    for raw_alias in value.split(","):
        alias = raw_alias.strip()
        if alias:
            aliases.append(alias)
    return aliases


def _filename_stem(filename: str) -> str:
    normalized = filename.strip().replace("\\", "/")
    return Path(normalized).stem


def _local_name(tag: str) -> str:
    if "}" not in tag:
        return tag
    return tag.rsplit("}", maxsplit=1)[-1]


__all__ = [
    "parse_addon_xml_descriptor",
    "parse_dat_definitions",
    "parse_decal_scatter",
    "parse_pbr_objects",
    "parse_resource_dirs",
]
