from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from lxml import etree

from openscenario_mcp.config import DEFAULT_SCHEMA_VERSION, get_default_schema_path

_SUPPORTED_SCHEMA_VERSIONS = {
    "1.4.0": DEFAULT_SCHEMA_VERSION,
    "1.4": DEFAULT_SCHEMA_VERSION,
    "1.x": DEFAULT_SCHEMA_VERSION,
    "v1.4.0": DEFAULT_SCHEMA_VERSION,
    "v1.4": DEFAULT_SCHEMA_VERSION,
}
_EXPECTED_RULE_HINT_PATTERN = re.compile(r"Expected is(?: one of)? \( ([^)]+) \)")
_RULE_HINT_PATTERNS = (
    r"attribute '([^']+)'",
    r"Element '([^']+)'",
)


def validate(xml: str, schema_version: str) -> list[dict[str, Any]]:
    normalized_version = _normalize_schema_version(schema_version)
    schema = _load_schema(normalized_version)

    try:
        document = etree.fromstring(xml.encode("utf-8"))
    except etree.XMLSyntaxError as exc:
        return [_normalize_xml_syntax_error(exc)]

    if schema.validate(document):
        return []

    return [_normalize_log_entry(entry) for entry in schema.error_log]


def _normalize_schema_version(schema_version: str) -> str:
    requested_version = schema_version.strip().lower()
    try:
        return _SUPPORTED_SCHEMA_VERSIONS[requested_version]
    except KeyError as exc:
        supported = ", ".join(sorted(_SUPPORTED_SCHEMA_VERSIONS))
        raise ValueError(
            f"Unsupported schema_version: {schema_version}. Supported values: {supported}."
        ) from exc


@lru_cache(maxsize=None)
def _load_schema(schema_version: str) -> etree.XMLSchema:
    if schema_version != DEFAULT_SCHEMA_VERSION:
        raise ValueError(f"No schema registered for version {schema_version}.")

    schema_document = etree.parse(str(get_default_schema_path()))
    return etree.XMLSchema(schema_document)


def _normalize_log_entry(entry: etree._LogEntry) -> dict[str, Any]:
    message = entry.message.strip()
    return {
        "line": _coerce_optional_int(entry.line),
        "column": _coerce_optional_int(getattr(entry, "column", None)),
        "message": message,
        "rule_hint": _extract_rule_hint(message),
    }


def _normalize_xml_syntax_error(exc: etree.XMLSyntaxError) -> dict[str, Any]:
    message = exc.msg.strip() if exc.msg else str(exc)
    return {
        "line": _coerce_optional_int(exc.lineno),
        "column": _coerce_optional_int(exc.offset),
        "message": message,
        "rule_hint": _extract_rule_hint(message),
    }


def _extract_rule_hint(message: str) -> str | None:
    expected_match = _EXPECTED_RULE_HINT_PATTERN.search(message)
    if expected_match:
        return expected_match.group(1).strip()

    for pattern in _RULE_HINT_PATTERNS:
        match = re.search(pattern, message)
        if match:
            return match.group(1)
    return None


def _coerce_optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
