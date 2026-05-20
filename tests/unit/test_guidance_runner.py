from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from openscenario_mcp.generation.runner import (
    build_prompt_guidance_packet,
    build_request_generation_packet,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_build_prompt_guidance_packet_reads_prompt_and_embeds_guidance(
    tmp_path: Path,
) -> None:
    prompt_path = tmp_path / "sample.md"
    prompt_path.write_text(
        "# Sample Prompt\n\nCreate a minimal SetAction example.\n",
        encoding="utf-8",
    )

    def guidance_tool(**kwargs):
        return {
            "query": kwargs["query"],
            "element": kwargs["element"],
            "parent_context": kwargs["parent_context"],
            "retrieval_hits": [{"title": "SetAction"}],
            "element_schema": {"element": "SetAction"},
            "draft_checklist": ["Select exactly one branch from: Value, Expression."],
            "repair_diagnostics": [],
            "repair_actions": [],
        }

    packet = build_prompt_guidance_packet(
        prompt_path=prompt_path,
        guidance_tool=guidance_tool,
        query="set action",
        element="SetAction",
        parent_context="VariableAction",
    )

    assert packet["prompt_path"] == prompt_path.as_posix()
    assert packet["prompt_text"].startswith("# Sample Prompt")
    assert packet["guidance"]["query"] == "set action"
    assert packet["guidance"]["element"] == "SetAction"
    assert packet["guidance"]["parent_context"] == "VariableAction"
    assert packet["guidance"]["draft_checklist"] == [
        "Select exactly one branch from: Value, Expression."
    ]


def test_build_guidance_packet_script_writes_output(tmp_path: Path) -> None:
    output_path = tmp_path / "guidance.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_guidance_packet.py",
            "--prompt-file",
            "benchmarks/prompts/minimal-single-vehicle.md",
            "--query",
            "storyboard",
            "--element",
            "Storyboard",
            "--output",
            str(output_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["prompt_path"].endswith("benchmarks/prompts/minimal-single-vehicle.md")
    assert payload["guidance"]["element"] == "Storyboard"
    assert payload["guidance"]["draft_checklist"]


def test_build_request_generation_packet_embeds_generation_packet() -> None:
    def packet_tool(**kwargs):
        return {
            "intent": {"entities": [{"name": "ego"}]},
            "schema_plan": {"primary_elements": ["Storyboard"]},
            "vtd_plan": {"country_code": kwargs["country_code"]},
            "naming_plan": {},
            "validation_plan": {"stage": kwargs["stage"]},
            "open_questions": [],
        }

    packet = build_request_generation_packet(
        request="生成一个最小 ego 场景",
        packet_tool=packet_tool,
        country_code="CN",
        stage="draft",
    )

    assert packet["request"] == "生成一个最小 ego 场景"
    assert packet["generation_packet"]["intent"]["entities"][0]["name"] == "ego"
    assert packet["generation_packet"]["validation_plan"]["stage"] == "draft"
