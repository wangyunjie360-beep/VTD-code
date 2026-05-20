from __future__ import annotations

from pathlib import Path

from openscenario_mcp.reporting.ppt_mermaid import (
    asset_path_for_placement,
    extract_mermaid_blocks,
    report_diagram_placements,
)


def test_extract_mermaid_blocks_preserves_order_and_content() -> None:
    markdown = """
# Demo

```mermaid
flowchart LR
A --> B
```

text

```mermaid
sequenceDiagram
participant U
U->>S: ping
```
"""

    blocks = extract_mermaid_blocks(markdown)

    assert blocks == [
        "flowchart LR\nA --> B",
        "sequenceDiagram\nparticipant U\nU->>S: ping",
    ]


def test_extract_mermaid_blocks_ignores_other_fenced_blocks() -> None:
    markdown = """
```python
print("hi")
```

```dot
digraph G { A -> B }
```

```mermaid
flowchart TD
A --> C
```
"""

    blocks = extract_mermaid_blocks(markdown)

    assert blocks == ["flowchart TD\nA --> C"]


def test_report_diagram_placements_cover_expected_slides_and_blocks() -> None:
    placements = report_diagram_placements()

    assert len(placements) == 10
    assert [item.markdown_index for item in placements] == list(range(10))
    assert [item.slide_number for item in placements] == [4, 7, 12, 14, 15, 16, 17, 18, 19, 20]


def test_report_diagram_placements_have_positive_geometry_and_unique_keys() -> None:
    placements = report_diagram_placements()

    assert len({item.key for item in placements}) == len(placements)
    for item in placements:
        assert item.expected_fragment
        assert item.left > 0
        assert item.top > 0
        assert item.width > 0
        assert item.height > 0


def test_asset_path_for_placement_uses_stable_numbered_filenames() -> None:
    placement = report_diagram_placements()[0]

    path = asset_path_for_placement(Path("assets"), placement)

    assert path == Path("assets") / "01-system-architecture.png"
