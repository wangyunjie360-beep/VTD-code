from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.build_benchmark_guidance import load_benchmark_guidance_inputs


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_load_benchmark_guidance_inputs_reads_known_benchmarks() -> None:
    manifest = load_benchmark_guidance_inputs(
        REPO_ROOT / "benchmarks" / "guidance-inputs.json"
    )

    assert set(manifest) == {
        "minimal-single-vehicle",
        "two-vehicle-follow",
        "triggered-deceleration",
        "triggered-lane-change",
    }
    assert manifest["minimal-single-vehicle"]["element"] == "Storyboard"
    assert manifest["triggered-lane-change"]["element"] == "LaneChangeAction"


def test_build_benchmark_guidance_script_writes_default_result_path(
    tmp_path: Path,
) -> None:
    results_dir = tmp_path / "results"
    results_dir.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_benchmark_guidance.py",
            "--benchmark",
            "minimal-single-vehicle",
            "--results-dir",
            str(results_dir),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    output_path = results_dir / "minimal-single-vehicle.guidance.json"
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["prompt_path"].endswith("benchmarks/prompts/minimal-single-vehicle.md")
    assert payload["guidance"]["element"] == "Storyboard"
    assert payload["guidance"]["draft_checklist"]


def test_benchmark_guidance_manifest_keeps_triggered_lane_change_context() -> None:
    manifest = load_benchmark_guidance_inputs(
        REPO_ROOT / "benchmarks" / "guidance-inputs.json"
    )

    assert manifest["triggered-lane-change"]["parent_context"] == "LateralAction"
