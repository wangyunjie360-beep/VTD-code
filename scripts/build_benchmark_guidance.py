from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence


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


def load_benchmark_guidance_inputs(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("benchmark guidance inputs must be a JSON object")
    return {
        str(name): dict(config)
        for name, config in payload.items()
        if isinstance(name, str) and isinstance(config, dict)
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build guidance packets for benchmark prompts."
    )
    parser.add_argument("--benchmark", required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=REPO_ROOT / "benchmarks" / "guidance-inputs.json",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=REPO_ROOT / "benchmarks" / "results",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = load_benchmark_guidance_inputs(args.manifest)
    try:
        config = manifest[args.benchmark]
    except KeyError as exc:
        raise SystemExit(f"Unknown benchmark guidance entry: {args.benchmark}") from exc

    runtime = build_runtime_from_config()
    guidance_tool = build_xml_guidance_tool(runtime.knowledge_base, runtime.patterns)
    prompt_path = REPO_ROOT / str(config["prompt_file"])
    packet = build_prompt_guidance_packet(
        prompt_path=prompt_path,
        guidance_tool=guidance_tool,
        query=str(config["query"]),
        element=str(config["element"]),
        parent_context=(
            str(config["parent_context"])
            if config.get("parent_context") is not None
            else None
        ),
    )

    args.results_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.results_dir / f"{args.benchmark}.guidance.json"
    write_guidance_packet(output_path, packet)
    print(f"Wrote benchmark guidance packet to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
