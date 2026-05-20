from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

from openscenario_mcp.config import get_project_root

_XSD_NS = {"xsd": "http://www.w3.org/2001/XMLSchema"}


@dataclass(frozen=True, slots=True)
class XsdInventory:
    element_names: tuple[str, ...]
    simple_type_names: tuple[str, ...]
    complex_type_names: tuple[str, ...]
    group_names: tuple[str, ...]


def load_xsd_inventory(path: str | Path) -> XsdInventory:
    schema_path = _resolve_path(path)
    root = ET.parse(schema_path).getroot()

    element_names = tuple(
        sorted(
            {
                element.get("name")
                for element in root.findall(".//xsd:element", _XSD_NS)
                if element.get("name")
            }
        )
    )
    simple_type_names = tuple(
        sorted(
            {
                element.get("name")
                for element in root.findall("xsd:simpleType", _XSD_NS)
                if element.get("name")
            }
        )
    )
    complex_type_names = tuple(
        sorted(
            {
                element.get("name")
                for element in root.findall("xsd:complexType", _XSD_NS)
                if element.get("name")
            }
        )
    )
    group_names = tuple(
        sorted(
            {
                element.get("name")
                for element in root.findall("xsd:group", _XSD_NS)
                if element.get("name")
            }
        )
    )

    return XsdInventory(
        element_names=element_names,
        simple_type_names=simple_type_names,
        complex_type_names=complex_type_names,
        group_names=group_names,
    )


def _resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return get_project_root() / candidate


__all__ = ["XsdInventory", "load_xsd_inventory"]
