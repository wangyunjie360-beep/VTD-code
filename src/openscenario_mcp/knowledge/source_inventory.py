from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openscenario_mcp.models import SourceEntry


def load_source_inventory(manifest_path: str | Path) -> list[SourceEntry]:
    manifest = Path(manifest_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError("Source inventory manifest must be a JSON object.")

    raw_sources = payload.get("sources")
    if not isinstance(raw_sources, list):
        raise ValueError("Source inventory manifest must contain a 'sources' list.")

    return [
        SourceEntry(
            id=_require_string(entry, "id", index),
            kind=_require_string(entry, "kind", index),
            path=_require_string(entry, "path", index),
        )
        for index, entry in enumerate(raw_sources)
    ]


def _require_string(entry: Any, key: str, index: int) -> str:
    if not isinstance(entry, dict):
        raise ValueError(f"Source entry at index {index} must be an object.")

    value = entry.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"Source entry at index {index} must define a non-empty string '{key}'."
        )

    return value
