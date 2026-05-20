from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from openscenario_mcp.knowledge.graph_export import export_visual_knowledge_graph


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a visualization-friendly OpenSCENARIO + VTD graph bundle."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=REPO_ROOT,
        help="Project root containing knowledge/structured and knowledge/diagnostics.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPO_ROOT / "knowledge" / "graph_visual",
        help="Output directory for the visual graph bundle.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = export_visual_knowledge_graph(
        project_root=args.project_root,
        output_root=args.output_root,
    )
    print(f"Wrote visual knowledge graph bundle to {args.output_root}")
    print(f"Node counts: {manifest['node_counts']}")
    print(f"Edge counts: {manifest['edge_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
