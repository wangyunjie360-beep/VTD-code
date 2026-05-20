from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from openscenario_mcp.knowledge.vtd_loader import build_vtd_knowledge_snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the repository-local phase-1 VTD knowledge snapshot."
    )
    parser.add_argument(
        "--runtime-root",
        type=Path,
        required=True,
        help="Path to the VTD.2020 Runtime directory.",
    )
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=REPO_ROOT / "knowledge" / "structured" / "vtd",
        help="Repository-local output directory for structured VTD snapshot files.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_vtd_knowledge_snapshot(
        runtime_root=args.runtime_root,
        snapshot_root=args.snapshot_root,
    )
    print(f"Wrote VTD snapshot to {args.snapshot_root}")
    print(f"Asset counts: {summary['asset_counts']}")
    print(f"Rule counts: {summary['rule_counts']}")
    print(f"Semantic counts: {summary['semantic_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
