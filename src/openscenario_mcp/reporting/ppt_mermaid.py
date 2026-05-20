from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


_MERMAID_BLOCK_PATTERN = re.compile(
    r"```mermaid\s*\n(?P<body>.*?)(?:\n```)",
    re.DOTALL,
)


@dataclass(frozen=True, slots=True)
class DiagramPlacement:
    key: str
    markdown_index: int
    slide_number: int
    expected_fragment: str
    left: float
    top: float
    width: float
    height: float


def extract_mermaid_blocks(markdown_text: str) -> list[str]:
    return [
        match.group("body").strip()
        for match in _MERMAID_BLOCK_PATTERN.finditer(markdown_text)
        if match.group("body").strip()
    ]


def report_diagram_placements() -> list[DiagramPlacement]:
    return [
        DiagramPlacement("system-architecture", 0, 4, "ASAM OpenSCENARIO XML V1.4.0 XSD", 0.72, 1.24, 11.55, 1.45),
        DiagramPlacement("knowledge-pipeline", 1, 7, "本地 OpenSCENARIO.xsd", 0.72, 1.18, 11.40, 4.85),
        DiagramPlacement("knowledge-drives-llm", 2, 12, "用户场景需求", 0.82, 1.35, 11.20, 1.45),
        DiagramPlacement("retrieve-spec", 3, 14, "自然语言 query", 0.80, 1.35, 6.95, 4.15),
        DiagramPlacement("element-schema", 4, 15, "element + parent_context", 0.80, 1.35, 6.95, 4.15),
        DiagramPlacement("validate-xml", 5, 16, "XML 字符串", 0.80, 1.35, 6.95, 4.15),
        DiagramPlacement("diagnostics", 6, 17, "validate_xml 返回 errors", 0.80, 1.35, 6.95, 4.15),
        DiagramPlacement("build-xml-guidance", 7, 18, "query + element + parent_context + errors?", 0.80, 1.35, 6.95, 4.15),
        DiagramPlacement("tool-loop", 8, 19, "participant U as 用户/Agent", 0.82, 1.28, 11.20, 4.55),
        DiagramPlacement("skill-workflow", 9, 20, "用户输入自然语言场景需求", 0.82, 1.18, 11.20, 4.95),
    ]


def asset_path_for_placement(assets_dir: Path, placement: DiagramPlacement) -> Path:
    filename = f"{placement.markdown_index + 1:02d}-{placement.key}.png"
    return assets_dir / filename


__all__ = [
    "DiagramPlacement",
    "asset_path_for_placement",
    "extract_mermaid_blocks",
    "report_diagram_placements",
]
