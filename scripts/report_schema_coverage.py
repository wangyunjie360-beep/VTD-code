from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_PATH = _PROJECT_ROOT / "src"
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from openscenario_mcp.config import get_project_root
from openscenario_mcp.knowledge.xsd_inventory import load_xsd_inventory
from openscenario_mcp.models import ElementRecord


def build_schema_coverage_report(project_root: str | Path | None = None) -> dict[str, Any]:
    project_root = Path(project_root) if project_root is not None else get_project_root()
    inventory = load_xsd_inventory(project_root / "knowledge/raw/schema/OpenSCENARIO.xsd")
    elements_dir = project_root / "knowledge/structured/elements"
    structured_paths = sorted(elements_dir.glob("*.json"))
    structured_elements = sorted(path.stem for path in structured_paths)
    structured_set = set(structured_elements)
    structured_by_lower = {name.lower(): name for name in structured_elements}
    xsd_by_lower = {name.lower(): name for name in inventory.element_names}

    missing_elements = [
        name
        for name in inventory.element_names
        if name not in structured_set and name.lower() not in structured_by_lower
    ]
    extra_structured_elements = [
        name
        for name in structured_elements
        if name not in set(inventory.element_names) and name.lower() not in xsd_by_lower
    ]

    dangling_child_references: list[dict[str, str]] = []
    records_missing_required_metadata: list[dict[str, str]] = []

    for path in structured_paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            records_missing_required_metadata.append(
                {"element": path.stem, "issue": "invalid_json"}
            )
            continue

        element_name = str(payload.get("element", "")).strip()
        source_path = str(payload.get("source_path", "")).strip()

        if not element_name:
            records_missing_required_metadata.append(
                {"element": path.stem, "issue": "missing_element"}
            )
            continue

        if not source_path:
            records_missing_required_metadata.append(
                {"element": element_name, "issue": "missing_source_path"}
            )

        try:
            record = ElementRecord(**payload)
        except TypeError:
            records_missing_required_metadata.append(
                {"element": element_name or path.stem, "issue": "invalid_record"}
            )
            continue

        for child in record.allowed_children:
            child_name = str(child.get("name", "")).strip()
            if child_name and child_name not in structured_set:
                dangling_child_references.append(
                    {"element": record.element, "child": child_name}
                )

    return {
        "xsd_element_count": len(inventory.element_names),
        "structured_element_count": len(structured_elements),
        "structured_elements": structured_elements,
        "missing_elements": missing_elements,
        "extra_structured_elements": extra_structured_elements,
        "dangling_child_references": dangling_child_references,
        "records_missing_required_metadata": records_missing_required_metadata,
    }


if __name__ == "__main__":
    print(json.dumps(build_schema_coverage_report(), indent=2))
