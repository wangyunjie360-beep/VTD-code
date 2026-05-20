from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from openscenario_mcp.generation.runner import (
    build_prompt_guidance_packet,
    write_guidance_packet,
)
from openscenario_mcp.runtime import build_runtime_from_config
from openscenario_mcp.tools.guidance import build_xml_guidance_tool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a guidance packet for an OpenSCENARIO prompt."
    )
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--element", required=True)
    parser.add_argument("--parent-context", default=None)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument(
        "--errors-json",
        type=Path,
        default=None,
        help="Optional JSON file containing normalized validation errors.",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def load_errors(path: Path | None) -> list[dict[str, object]] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("errors-json must contain a JSON array")
    return [item for item in payload if isinstance(item, dict)]


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runtime = build_runtime_from_config()
    guidance_tool = build_xml_guidance_tool(runtime.knowledge_base, runtime.patterns)
    packet = build_prompt_guidance_packet(
        prompt_path=args.prompt_file,
        guidance_tool=guidance_tool,
        query=args.query,
        element=args.element,
        parent_context=args.parent_context,
        top_k=args.top_k,
        errors=load_errors(args.errors_json),
    )
    output_path = write_guidance_packet(args.output, packet)
    print(f"Wrote guidance packet to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
