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
from openscenario_mcp.knowledge.xsd_parser import parse_element_definition
from scripts.report_schema_coverage import build_schema_coverage_report


def main() -> None:
    project_root = get_project_root()
    schema_path = project_root / "knowledge/raw/schema/OpenSCENARIO.xsd"
    elements_dir = project_root / "knowledge/structured/elements"
    elements_dir.mkdir(parents=True, exist_ok=True)

    inventory = load_xsd_inventory(schema_path)
    existing = {path.stem for path in elements_dir.glob("*.json")}
    existing_by_lower = {name.lower(): name for name in existing}

    for element_name in inventory.element_names:
        if element_name in existing or element_name.lower() in existing_by_lower:
            continue
        payload = parse_element_definition(element_name)
        target = elements_dir / f"{element_name}.json"
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    _write_schema_scope(project_root, inventory)
    _write_coverage_report(project_root)


def _write_schema_scope(project_root: Path, inventory: Any) -> None:
    elements = sorted(
        path.stem
        for path in (project_root / "knowledge/structured/elements").glob("*.json")
    )
    canonical_by_lower = {name.lower(): name for name in elements}
    alias_collisions = {
        name: canonical_by_lower[name.lower()]
        for name in inventory.element_names
        if name not in elements and name.lower() in canonical_by_lower
    }
    payload = {
        "mode": "full",
        "schema_version": "1.4.0",
        "schema_label": "ASAM OpenSCENARIO XML V1.4.0",
        "xsd_element_count": len(inventory.element_names),
        "elements": elements,
        "represented_xsd_elements": list(inventory.element_names),
        "alias_collisions": alias_collisions,
        "source_path": "knowledge/raw/schema/OpenSCENARIO.xsd#L1",
    }
    target = project_root / "knowledge/structured/schema_scope.json"
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_coverage_report(project_root: Path) -> None:
    payload = build_schema_coverage_report()
    target = project_root / "knowledge/structured/coverage_report.json"
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
