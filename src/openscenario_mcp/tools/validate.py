from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from openscenario_mcp.config import DEFAULT_SCHEMA_VERSION
from openscenario_mcp.validator.adapter import ValidatorAdapter


def build_validate_xml_tool(adapter: ValidatorAdapter | None = None):
    validator = adapter or ValidatorAdapter()

    def validate_xml(
        xml: str,
        schema_version: str = DEFAULT_SCHEMA_VERSION,
    ) -> dict[str, Any]:
        try:
            raw_errors = validator.validate(xml=xml, schema_version=schema_version)
        except Exception as exc:
            errors = [_normalize_error(exc)]
        else:
            errors = [_normalize_error(error) for error in raw_errors]

        return {"ok": not errors, "errors": errors}

    return validate_xml


def _normalize_error(error: Any) -> dict[str, Any]:
    if isinstance(error, Mapping):
        payload: Mapping[str, Any] = error
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
        "line": _coerce_optional_int(raw_line),
        "column": _coerce_optional_int(raw_column),
        "message": str(raw_message) if raw_message else str(error),
        "rule_hint": str(raw_rule_hint) if raw_rule_hint not in (None, "") else None,
    }


def _coerce_optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
