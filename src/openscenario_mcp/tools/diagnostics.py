from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from openscenario_mcp.validator.classifier import classify_error, load_patterns


def build_explain_validation_errors_tool(
    patterns: list[Mapping[str, Any]] | None = None,
):
    loaded_patterns = list(patterns) if patterns is not None else load_patterns()

    def explain_validation_errors(errors: list[Mapping[str, Any] | object]) -> dict[str, Any]:
        diagnostics = [classify_error(error, loaded_patterns) for error in errors]
        return {"diagnostics": diagnostics}

    return explain_validation_errors
