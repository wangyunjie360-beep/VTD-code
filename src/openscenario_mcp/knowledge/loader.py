from __future__ import annotations

import json
from pathlib import Path

from openscenario_mcp.models import ElementRecord


def load_element_record(path: str | Path) -> ElementRecord:
    record_path = Path(path)
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    return ElementRecord(**payload)
