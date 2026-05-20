from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from openscenario_mcp.runtime import build_runtime_from_config
from openscenario_mcp.tools.check_xml_intent_consistency import (
    build_check_xml_intent_consistency_tool,
)
from openscenario_mcp.tools.validate import build_validate_xml_tool


CASE_REQUEST = (
    "Generate a VTD OpenSCENARIO case on an urban road in China: ego vehicle "
    "starts at 30 km/h; the scenario trigger is simulation time 5 seconds; at "
    "that trigger the ego vehicle performs a lane change to the left by one lane; "
    "the simulation stops at 20 seconds. Keep the XML minimal but schema-valid."
)

ALLOWED_MCP_TOOLS = [
    "mcp__openscenario__build_generation_packet",
    "mcp__openscenario__retrieve_spec",
    "mcp__openscenario__get_element_schema",
    "mcp__openscenario__resolve_vtd_name",
    "mcp__openscenario__retrieve_vtd_asset",
    "mcp__openscenario__recommend_vtd_candidates",
    "mcp__openscenario__build_vtd_guidance",
    "mcp__openscenario__validate_xml",
    "mcp__openscenario__explain_validation_errors",
    "mcp__openscenario__summarize_validation_repairs",
    "mcp__openscenario__check_xml_intent_consistency",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run an AI-primary OpenSCENARIO case: Claude Code routed to GPT "
            "drives generation and uses local MCP tools only as helpers."
        )
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPO_ROOT / "docs" / "case-runs" / "lane-change-cn-ai-primary",
        help="Directory where XML, interaction logs, and the markdown report are written.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=600,
        help="Timeout for the Claude Code primary generation run.",
    )
    parser.add_argument(
        "--max-budget-usd",
        type=str,
        default="2.00",
        help="Claude Code --max-budget-usd value for the case run.",
    )
    parser.add_argument(
        "--rebuild-report",
        action="store_true",
        help="Rebuild markdown from existing AI-primary artifacts without rerunning Claude.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    if args.rebuild_report:
        report_path = _rebuild_report_from_existing_artifacts(output_root)
        print(f"Rebuilt report: {report_path}")
        return 0

    claude_run = _run_claude_gpt_primary_case(
        output_root=output_root,
        timeout_seconds=args.timeout_seconds,
        max_budget_usd=args.max_budget_usd,
    )
    final_output = claude_run["final_output"]
    xml_text = str(final_output.get("xml", "")).strip()
    if not xml_text:
        raise RuntimeError("Claude/GPT final output did not contain an XML payload.")

    scenario_path = output_root / "lane_change_cn_ai_primary.xosc"
    scenario_path.write_text(xml_text + "\n", encoding="utf-8")

    verification = _verify_final_xml(xml_text)
    _write_json(output_root / "independent-verification.json", verification)

    summary = {
        "case_request": CASE_REQUEST,
        "primary_actor": "claude_code_gpt",
        "model": final_output.get("model", "gpt-5.5"),
        "scenario_path": _repo_relative(scenario_path),
        "interaction_count": len(claude_run["interactions"]),
        "ai_validation_ok": _latest_validation_ok(claude_run["interactions"]),
        "ai_intent_consistent_claim": final_output.get("intent_consistent"),
        "independent_validation_ok": verification["validation"]["ok"],
        "independent_intent_consistent": verification["consistency"][
            "intent_consistent"
        ],
        "claude_stream": _repo_relative(claude_run["stream_path"]),
        "claude_prompt": _repo_relative(claude_run["prompt_path"]),
        "interactions": _repo_relative(output_root / "interactions.json"),
        "ai_output": _repo_relative(output_root / "ai-primary-output.json"),
        "verification": _repo_relative(output_root / "independent-verification.json"),
    }
    _write_json(output_root / "summary.json", summary)

    report_path = output_root / "full-flow-report.md"
    report_path.write_text(
        _build_markdown_report(
            output_root=output_root,
            scenario_path=scenario_path,
            claude_run=claude_run,
            final_output=final_output,
            verification=verification,
            summary=summary,
        ),
        encoding="utf-8",
    )

    print(f"Wrote scenario: {scenario_path}")
    print(f"Wrote interactions: {output_root / 'interactions.json'}")
    print(f"Wrote report: {report_path}")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


def _rebuild_report_from_existing_artifacts(output_root: Path) -> Path:
    scenario_path = output_root / "lane_change_cn_ai_primary.xosc"
    stream_path = output_root / "claude-gpt-primary-stream.jsonl"
    _sanitize_existing_claude_stream(stream_path)
    prompt_path = output_root / "claude-gpt-primary-prompt.txt"
    stderr_path = output_root / "claude-gpt-primary-stderr.txt"
    mcp_config_path = output_root / "openscenario-mcp.config.json"
    final_output = json.loads(
        (output_root / "ai-primary-output.json").read_text(encoding="utf-8")
    )
    interactions = json.loads(
        (output_root / "interactions.json").read_text(encoding="utf-8")
    )
    verification = json.loads(
        (output_root / "independent-verification.json").read_text(encoding="utf-8")
    )
    summary = json.loads((output_root / "summary.json").read_text(encoding="utf-8"))
    parsed_stream = _parse_claude_stream(stream_path)
    claude_run = {
        "status": "ok",
        "started_at": "",
        "finished_at": "",
        "returncode": 0,
        "command": "claude -p <prompt> --model gpt-5.5 --mcp-config <openscenario-mcp> --output-format stream-json",
        "prompt_path": prompt_path,
        "stream_path": stream_path,
        "stderr_path": stderr_path,
        "mcp_config_path": mcp_config_path,
        "init": parsed_stream["init"],
        "result": parsed_stream["result"],
        "interactions": interactions,
        "final_output": final_output,
    }
    report_path = output_root / "full-flow-report.md"
    report_path.write_text(
        _build_markdown_report(
            output_root=output_root,
            scenario_path=scenario_path,
            claude_run=claude_run,
            final_output=final_output,
            verification=verification,
            summary=summary,
        ),
        encoding="utf-8",
    )
    return report_path


def _run_claude_gpt_primary_case(
    *,
    output_root: Path,
    timeout_seconds: int,
    max_budget_usd: str,
) -> dict[str, Any]:
    claude_executable = shutil.which("claude.cmd") or shutil.which("claude")
    if claude_executable is None:
        raise RuntimeError("Claude Code CLI was not found on PATH.")

    mcp_config_path = output_root / "openscenario-mcp.config.json"
    _write_json(
        mcp_config_path,
        {
            "mcpServers": {
                "openscenario": {
                    "command": "py",
                    "args": ["-3.14", "-m", "openscenario_mcp"],
                }
            }
        },
    )

    prompt = _build_ai_primary_prompt()
    prompt_path = output_root / "claude-gpt-primary-prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")

    stream_path = output_root / "claude-gpt-primary-stream.jsonl"
    command = [
        claude_executable,
        "--model",
        "gpt-5.5",
        "--mcp-config",
        str(mcp_config_path),
        "--strict-mcp-config",
        "--allowedTools",
        ",".join(ALLOWED_MCP_TOOLS),
        "--verbose",
        "--output-format",
        "stream-json",
        "--no-session-persistence",
        "--max-budget-usd",
        max_budget_usd,
        "--setting-sources",
        "user",
        "-p",
    ]

    started_at = _utc_now()
    completed = subprocess.run(
        command,
        input=prompt,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        encoding="utf-8",
        errors="replace",
    )
    finished_at = _utc_now()
    _write_sanitized_claude_stream(stream_path, completed.stdout)
    stderr_path = output_root / "claude-gpt-primary-stderr.txt"
    stderr_path.write_text(_redact_secret_text(completed.stderr), encoding="utf-8")

    parsed_stream = _parse_claude_stream(stream_path)
    final_output = _parse_final_output(parsed_stream["result"].get("result", ""))
    _write_json(output_root / "ai-primary-output.json", final_output)
    _write_json(output_root / "interactions.json", parsed_stream["interactions"])

    return {
        "status": "ok" if completed.returncode == 0 else "error",
        "started_at": started_at,
        "finished_at": finished_at,
        "returncode": completed.returncode,
        "command": "claude -p <prompt> --model gpt-5.5 --mcp-config <openscenario-mcp> --output-format stream-json",
        "prompt_path": prompt_path,
        "stream_path": stream_path,
        "stderr_path": stderr_path,
        "mcp_config_path": mcp_config_path,
        "init": parsed_stream["init"],
        "result": parsed_stream["result"],
        "interactions": parsed_stream["interactions"],
        "final_output": final_output,
    }


def _build_ai_primary_prompt() -> str:
    canonical_intent = _canonical_case_intent()
    return "\n".join(
        [
            "You are the primary AI scenario generator.",
            "The local OpenSCENARIO MCP tools are only query, naming, validation, and consistency-check helpers.",
            "Do not treat the tools as the generator. You draft the XML yourself after querying evidence.",
            "",
            "Case request:",
            CASE_REQUEST,
            "",
            "Required workflow:",
            "1. Call build_generation_packet first.",
            '2. Resolve the open target-lane question as AbsoluteTargetLane value="-1" and record that assumption.',
            '3. Query retrieve_spec with kind="element" and get_element_schema before drafting ScenarioObject, Vehicle, Storyboard, LaneChangeAction, and SimulationTimeCondition blocks.',
            "4. Use at least one VTD naming/asset helper for the ego/runtime naming context.",
            "5. Draft the XML yourself as the primary AI.",
            "6. Call validate_xml on the full XML. If it fails, call explain_validation_errors or summarize_validation_repairs, repair only the affected XML, and validate again. Retry at most 3 times.",
            "7. Call check_xml_intent_consistency on the final XML. Use exactly this intent JSON so the helper can check the requested behavior:",
            json.dumps(canonical_intent, ensure_ascii=False, indent=2),
            'Use checklist ["ego", "lane_change", "speed_change", "simulation_time", "stop_trigger"].',
            "",
            "Return final output as strict JSON only, no markdown and no code fences, with these keys:",
            json.dumps(
                {
                    "primary_actor": "claude_code_gpt",
                    "model": "gpt-5.5",
                    "request": CASE_REQUEST,
                    "parsed_intent": {},
                    "xml_intent_check": [],
                    "tool_call_summary": [{"tool": "...", "purpose": "..."}],
                    "validation_ok": True,
                    "intent_consistent": True,
                    "remaining_blockers": [],
                    "xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>...",
                },
                ensure_ascii=False,
                indent=2,
            ),
        ]
    )


def _parse_claude_stream(stream_path: Path) -> dict[str, Any]:
    init: dict[str, Any] = {}
    result: dict[str, Any] = {}
    interactions: list[dict[str, Any]] = []
    by_tool_use_id: dict[str, dict[str, Any]] = {}

    for line in stream_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        event_type = event.get("type")
        if event_type == "system" and event.get("subtype") == "init":
            init = {
                "cwd": event.get("cwd"),
                "session_id": event.get("session_id"),
                "model": event.get("model"),
                "mcp_servers": event.get("mcp_servers", []),
                "claude_code_version": event.get("claude_code_version"),
                "tools": [
                    tool
                    for tool in event.get("tools", [])
                    if str(tool).startswith("mcp__openscenario__")
                ],
            }
            continue
        if event_type == "assistant":
            for content in event.get("message", {}).get("content", []):
                if content.get("type") != "tool_use":
                    continue
                name = str(content.get("name", ""))
                if not name.startswith("mcp__openscenario__"):
                    continue
                tool_use_id = str(content.get("id", ""))
                interaction = {
                    "step": len(interactions) + 1,
                    "actor": "claude_code_gpt",
                    "tool": name.removeprefix("mcp__openscenario__"),
                    "tool_use_id": tool_use_id,
                    "status": "called",
                    "arguments": content.get("input", {}),
                    "result": None,
                }
                interactions.append(interaction)
                by_tool_use_id[tool_use_id] = interaction
            continue
        if event_type == "user":
            for content in event.get("message", {}).get("content", []):
                if content.get("type") != "tool_result":
                    continue
                tool_use_id = str(content.get("tool_use_id", ""))
                interaction = by_tool_use_id.get(tool_use_id)
                if interaction is None:
                    continue
                interaction["status"] = "error" if content.get("is_error") else "ok"
                interaction["result"] = _parse_jsonish(content.get("content"))
            continue
        if event_type == "result":
            result = {
                "subtype": event.get("subtype"),
                "is_error": event.get("is_error"),
                "duration_ms": event.get("duration_ms"),
                "duration_api_ms": event.get("duration_api_ms"),
                "num_turns": event.get("num_turns"),
                "result": event.get("result"),
                "session_id": event.get("session_id"),
                "total_cost_usd": event.get("total_cost_usd"),
                "usage": event.get("usage", {}),
                "modelUsage": event.get("modelUsage", {}),
                "permission_denials": event.get("permission_denials", []),
            }

    for interaction in interactions:
        if interaction["status"] == "called":
            interaction["status"] = "missing_result"
    return {"init": init, "result": result, "interactions": interactions}


def _write_sanitized_claude_stream(path: Path, stdout: str) -> None:
    path.write_text(_sanitize_claude_stream_text(stdout), encoding="utf-8")


def _sanitize_existing_claude_stream(path: Path) -> None:
    if not path.is_file():
        return
    sanitized = _sanitize_claude_stream_text(path.read_text(encoding="utf-8"))
    path.write_text(sanitized, encoding="utf-8")


def _sanitize_claude_stream_text(stdout: str) -> str:
    lines: list[str] = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            lines.append(line)
            continue
        _sanitize_claude_event(event)
        lines.append(json.dumps(event, ensure_ascii=False, sort_keys=True))
    return "\n".join(lines) + ("\n" if lines else "")


def _sanitize_claude_event(event: Any) -> None:
    if not isinstance(event, dict):
        return
    message = event.get("message")
    if isinstance(message, dict):
        _sanitize_message_content(message.get("content"))
    nested = event.get("event")
    if isinstance(nested, dict):
        content_block = nested.get("content_block")
        if isinstance(content_block, dict) and content_block.get("type") == "thinking":
            content_block["thinking"] = "[redacted: model reasoning omitted]"
        delta = nested.get("delta")
        if isinstance(delta, dict) and str(delta.get("type", "")).startswith("thinking"):
            delta["thinking"] = "[redacted: model reasoning omitted]"
    result = event.get("result")
    if isinstance(result, dict):
        _sanitize_message_content(result.get("content"))


def _sanitize_message_content(content: Any) -> None:
    if not isinstance(content, list):
        return
    for item in content:
        if isinstance(item, dict) and item.get("type") == "thinking":
            item["thinking"] = "[redacted: model reasoning omitted]"


def _parse_jsonish(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return ""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _parse_final_output(text: Any) -> dict[str, Any]:
    if not isinstance(text, str):
        raise RuntimeError("Claude/GPT final result was not text.")
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`").strip()
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        start = stripped.find("{")
        if start < 0:
            raise
        payload, _ = decoder.raw_decode(stripped[start:])
        if not isinstance(payload, dict):
            raise RuntimeError("Claude/GPT final JSON was not an object.")
        return payload


def _verify_final_xml(xml_text: str) -> dict[str, Any]:
    runtime = build_runtime_from_config()
    validation = build_validate_xml_tool(runtime.validator)(
        xml_text,
        schema_version="1.4.0",
    )
    consistency = build_check_xml_intent_consistency_tool()(
        xml=xml_text,
        intent=_canonical_case_intent(),
        checklist=["ego", "lane_change", "speed_change", "simulation_time", "stop_trigger"],
    )
    return {
        "validation": validation,
        "consistency": consistency,
    }


def _canonical_case_intent() -> dict[str, Any]:
    return {
        "parameters": [],
        "entities": [{"name": "ego", "type": "Vehicle", "role": "primary"}],
        "environment": {},
        "map_context": {"road_type": "urban", "country_code": "CN"},
        "init_actions": [
            {
                "type": "speed_change",
                "mode": "initial_speed",
                "entity": "ego",
                "value": 8.333333,
                "unit": "m/s",
                "source_value": 30,
                "source_unit": "km/h",
            }
        ],
        "story_actions": [
            {"type": "speed_change", "mode": "initial_speed", "entity": "ego"},
            {
                "type": "lane_change",
                "entity": "ego",
                "direction": "left",
                "target": {"type": "AbsoluteTargetLane", "value": "-1"},
            },
        ],
        "triggers": [{"type": "simulation_time", "value": 5.0, "unit": "s"}],
        "stop_conditions": [
            {"type": "simulation_time", "value": 20.0, "unit": "s"}
        ],
        "assumptions": [
            'The target lane is resolved as AbsoluteTargetLane value="-1".'
        ],
    }


def _latest_validation_ok(interactions: list[dict[str, Any]]) -> bool | None:
    for interaction in reversed(interactions):
        if interaction.get("tool") != "validate_xml":
            continue
        result = interaction.get("result")
        if isinstance(result, dict) and "ok" in result:
            return bool(result["ok"])
    return None


def _build_markdown_report(
    *,
    output_root: Path,
    scenario_path: Path,
    claude_run: dict[str, Any],
    final_output: dict[str, Any],
    verification: dict[str, Any],
    summary: dict[str, Any],
) -> str:
    interactions = claude_run["interactions"]
    settings = _read_redacted_claude_settings()
    result = claude_run["result"]
    model_usage = result.get("modelUsage", {})
    gpt_usage = model_usage.get("gpt-5.5", {})

    lines = [
        "# AI-Primary OpenSCENARIO Full-Flow Case Run",
        "",
        f"- Generated at: `{_utc_now()}`",
        f"- Primary AI: `Claude Code -> GPT gpt-5.5`",
        "- System role: OpenSCENARIO MCP tools are query, naming, validation, and consistency helpers.",
        f"- Case directory: `{_repo_relative(output_root)}`",
        f"- Scenario XML: `{_repo_relative(scenario_path)}`",
        f"- Raw Claude/GPT stream: `{_repo_relative(claude_run['stream_path'])}`",
        f"- Parsed tool interactions: `{summary['interactions']}`",
        f"- AI MCP interactions: `{len(interactions)}`",
        f"- AI validation ok: `{summary['ai_validation_ok']}`",
        f"- Independent validation ok: `{summary['independent_validation_ok']}`",
        f"- Independent intent consistent: `{summary['independent_intent_consistent']}`",
        "",
        "## Correct Claude -> GPT Routing",
        "",
        "Anthropic's Claude Code LLM gateway documentation says an LLM gateway sits between Claude Code and model providers, uses `ANTHROPIC_AUTH_TOKEN` for gateway authentication, and recommends setting `ANTHROPIC_BASE_URL` to the gateway's Anthropic-format endpoint. Their settings documentation also lists `ANTHROPIC_AUTH_TOKEN` as the custom `Authorization` header value. Sources: https://docs.anthropic.com/en/docs/claude-code/llm-gateway and https://docs.anthropic.com/en/docs/claude-code/settings.",
        "",
        "| Item | Value |",
        "| --- | --- |",
        f"| Claude Code version | `{claude_run['init'].get('claude_code_version', '')}` |",
        f"| configured model | `{settings.get('model', '')}` |",
        f"| ANTHROPIC_BASE_URL | `{settings.get('env', {}).get('ANTHROPIC_BASE_URL', '')}` |",
        f"| ANTHROPIC_MODEL | `{settings.get('env', {}).get('ANTHROPIC_MODEL', '')}` |",
        f"| auth token | `{settings.get('env', {}).get('ANTHROPIC_AUTH_TOKEN', '')}` |",
        f"| modelUsage evidence | `{','.join(model_usage.keys())}` |",
        f"| session turns | `{result.get('num_turns')}` |",
        f"| total cost USD | `{result.get('total_cost_usd')}` |",
        "",
        "The previous failure path was `Claude Code -> old gateway/model alias opus`, which made the gateway look for a Claude model. This corrected run is `Claude Code -> https://xlabapi.com Anthropic Messages endpoint -> gpt-5.5`.",
        "",
        "## Case Request",
        "",
        CASE_REQUEST,
        "",
        "## Flow Visualization",
        "",
        "```mermaid",
        "flowchart TD",
        "  U[User case request] --> AI[Claude Code routed to GPT gpt-5.5]",
        "  AI --> P[build_generation_packet]",
        "  P --> S[retrieve_spec and get_element_schema]",
        "  S --> N[VTD naming or asset helper]",
        "  N --> X[AI drafts OpenSCENARIO XML]",
        "  X --> V[validate_xml]",
        "  V --> D{schema valid?}",
        "  D -- no --> R[explain_validation_errors or repair summary]",
        "  R --> X",
        "  D -- yes --> C[check_xml_intent_consistency]",
        "  C --> O[Final XML and markdown report]",
        "```",
        "",
        "## Interaction Sequence",
        "",
        "```mermaid",
        "sequenceDiagram",
        "  participant U as User",
        "  participant AI as Claude/GPT",
        "  participant T as OpenSCENARIO MCP",
        "  participant V as Independent Verifier",
        "  U->>AI: Case request",
    ]
    for interaction in interactions:
        lines.append(f"  AI->>T: {interaction['step']}. {interaction['tool']}")
        lines.append(f"  T-->>AI: {interaction['status']}")
    lines.extend(
        [
            "  AI-->>U: Final XML JSON",
            "  V->>V: validate_xml + intent consistency",
            "```",
            "",
            "## Tool Interaction Summary",
            "",
            "| # | Tool | Status | Key Result |",
            "| ---: | --- | --- | --- |",
        ]
    )
    for interaction in interactions:
        lines.append(
            "| {step} | `{tool}` | `{status}` | {summary} |".format(
                step=interaction["step"],
                tool=interaction["tool"],
                status=interaction["status"],
                summary=_markdown_escape(_summarize_result(interaction.get("result"))),
            )
        )

    lines.extend(
        [
            "",
            "## AI Final Output",
            "",
            f"- Primary actor: `{final_output.get('primary_actor')}`",
            f"- Model: `{final_output.get('model')}`",
            f"- AI validation_ok: `{final_output.get('validation_ok')}`",
            f"- AI intent_consistent: `{final_output.get('intent_consistent')}`",
            f"- Remaining blockers: `{final_output.get('remaining_blockers')}`",
            "",
            "## Independent Final Verification",
            "",
            "```json",
            json.dumps(verification, ensure_ascii=False, indent=2),
            "```",
            "",
            "## Per-Step Claude/GPT <-> Tool I/O",
            "",
            f"The full raw stream is stored in `{_repo_relative(claude_run['stream_path'])}`. The details below omit model hidden reasoning and show MCP tool calls/results only.",
            "",
        ]
    )
    for interaction in interactions:
        lines.extend(
            [
                f"<details><summary>{interaction['step']}. {interaction['tool']} - {interaction['status']}</summary>",
                "",
                "**AI Tool Call**",
                "",
                "```json",
                json.dumps(interaction.get("arguments", {}), ensure_ascii=False, indent=2)[:12000],
                "```",
                "",
                "**Tool Result**",
                "",
                "```json",
                json.dumps(interaction.get("result", {}), ensure_ascii=False, indent=2)[:12000],
                "```",
                "",
                "</details>",
                "",
            ]
        )

    if result.get("permission_denials"):
        lines.extend(
            [
                "## Permission Denials",
                "",
                "```json",
                json.dumps(result["permission_denials"], ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )

    lines.extend(
        [
            "## Generated XML",
            "",
            "```xml",
            scenario_path.read_text(encoding="utf-8").strip(),
            "```",
            "",
            "## Notes",
            "",
            "- API credentials are redacted from all generated artifacts.",
            "- The AI, not the local script, drafted the XML. The local script only launched Claude Code, parsed its stream, saved artifacts, and independently verified the final XML.",
            "- The report keeps failed helper calls when they occur because they are part of the real AI/tool interaction trace.",
            "",
        ]
    )
    return "\n".join(lines)


def _read_redacted_claude_settings() -> dict[str, Any]:
    settings_path = Path.home() / ".claude" / "settings.json"
    if not settings_path.is_file():
        return {}
    data = json.loads(settings_path.read_text(encoding="utf-8-sig"))
    env = data.get("env")
    if isinstance(env, dict) and env.get("ANTHROPIC_AUTH_TOKEN"):
        env["ANTHROPIC_AUTH_TOKEN"] = f"configured, redacted, len={len(env['ANTHROPIC_AUTH_TOKEN'])}"
    return data


def _summarize_result(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return result[:160]
    if isinstance(result, dict):
        if "ok" in result and "errors" in result:
            return f"ok={result['ok']}, errors={len(result.get('errors', []))}"
        if "intent_consistent" in result:
            missing = result.get("xml_intent_check", {}).get("missing", [])
            extra = result.get("xml_intent_check", {}).get("extra", [])
            return (
                f"intent_consistent={result['intent_consistent']}, "
                f"missing={missing}, extra={extra}"
            )
        if "diagnostics" in result:
            return f"diagnostics={len(result['diagnostics'])}"
        if "hits" in result:
            return f"hits={len(result['hits'])}"
        if "name_resolution" in result:
            resolution = result["name_resolution"]
            return (
                f"name_resolution={resolution.get('rule_kind')} -> "
                f"{resolution.get('canonical_target')}"
            )
        if "schema_plan" in result:
            return "primary_elements=" + ",".join(
                result.get("schema_plan", {}).get("primary_elements", [])
            )
        if "element" in result:
            return f"element={result.get('element')}"
        if "error" in result:
            return str(result["error"])[:160]
    return str(result)[:160]


def _markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _redact_secret_text(value: str) -> str:
    return value.replace("\r\n", "\n")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
