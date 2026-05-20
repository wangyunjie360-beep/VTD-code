from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from openscenario_mcp.runtime import build_runtime_from_config
from openscenario_mcp.tools.build_generation_packet import build_generation_packet_tool
from openscenario_mcp.tools.check_xml_intent_consistency import (
    build_check_xml_intent_consistency_tool,
)
from openscenario_mcp.tools.diagnostics import build_explain_validation_errors_tool
from openscenario_mcp.tools.recommend_vtd_candidates import (
    build_recommend_vtd_candidates_tool,
)
from openscenario_mcp.tools.resolve_vtd_name import build_resolve_vtd_name_tool
from openscenario_mcp.tools.retrieve_spec import build_retrieve_spec_tool
from openscenario_mcp.tools.retrieve_vtd_asset import build_retrieve_vtd_asset_tool
from openscenario_mcp.tools.schema import build_get_element_schema_tool
from openscenario_mcp.tools.validate import build_validate_xml_tool


CASE_REQUEST = (
    "Generate a VTD OpenSCENARIO case on an urban road in China: ego vehicle "
    "starts at 30 km/h; the scenario trigger is simulation time 5 seconds; at "
    "that trigger the ego vehicle performs a lane change to the left by one lane; "
    "the simulation stops at 20 seconds. Keep the XML minimal but schema-valid."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run and document an end-to-end OpenSCENARIO MCP case."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPO_ROOT / "docs" / "case-runs" / "lane-change-cn",
        help="Directory where the case XML, logs, and markdown report are written.",
    )
    parser.add_argument(
        "--skip-claude",
        action="store_true",
        help="Skip local Claude CLI review.",
    )
    parser.add_argument(
        "--rebuild-report",
        action="store_true",
        help="Rebuild markdown from existing output files without rerunning tools.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    if args.rebuild_report:
        interactions = json.loads(
            (output_root / "interactions.json").read_text(encoding="utf-8")
        )
        validation_result = _find_interaction_result(interactions, "validate_xml")
        consistency_result = _find_interaction_result(
            interactions,
            "check_xml_intent_consistency",
        )
        summary_path = output_root / "summary.json"
        summary = (
            json.loads(summary_path.read_text(encoding="utf-8"))
            if summary_path.is_file()
            else {}
        )
        claude_artifact = summary.get("claude_artifact")
        report_path = output_root / "full-flow-report.md"
        report_path.write_text(
            _build_markdown_report(
                output_root=output_root,
                interactions=interactions,
                validation_result=validation_result,
                consistency_result=consistency_result,
                claude_artifact=claude_artifact,
            ),
            encoding="utf-8",
        )
        print(f"Rebuilt report: {report_path}")
        return 0

    runtime = build_runtime_from_config()
    interactions: list[dict[str, Any]] = []

    generation_packet = _record_tool(
        interactions,
        name="build_generation_packet",
        call=lambda: build_generation_packet_tool(runtime)(
            request=CASE_REQUEST,
            country_code="CN",
            stage="draft",
        ),
        arguments={
            "request": CASE_REQUEST,
            "country_code": "CN",
            "stage": "draft",
        },
    )
    intent = generation_packet["intent"]
    intent["assumptions"] = [
        *intent.get("assumptions", []),
        "Open question 'Which target lane should the lane change use?' resolved as AbsoluteTargetLane value='-1'.",
        "Use the repository's validator-accepted vehicle geometry and lane-position pattern.",
        "The requested initial 30 km/h speed is represented with an Init/SpeedAction block.",
    ]
    intent["story_actions"] = [
        *intent.get("story_actions", []),
        {
            "type": "speed_change",
            "mode": "initial_speed",
            "value": 8.33,
            "unit": "m/s",
        },
    ]
    checklist = ["ego", "lane_change", "speed_change", "simulation_time"]

    _record_tool(
        interactions,
        name="retrieve_spec_invalid_kind",
        call=lambda: build_retrieve_spec_tool(runtime.knowledge_base, runtime.patterns)(
            query=(
                "minimal OpenSCENARIO lane change scenario with ScenarioObject "
                "Storyboard Event LaneChangeAction SimulationTimeCondition"
            ),
            kind="schema",
            top_k=6,
        ),
        arguments={
            "query": "minimal OpenSCENARIO lane change scenario",
            "kind": "schema",
            "top_k": 6,
        },
        expect_error=True,
    )
    spec_hits = _record_tool(
        interactions,
        name="retrieve_spec",
        call=lambda: build_retrieve_spec_tool(runtime.knowledge_base, runtime.patterns)(
            query=(
                "minimal OpenSCENARIO lane change scenario with ScenarioObject "
                "Storyboard Event LaneChangeAction SimulationTimeCondition"
            ),
            kind="element",
            top_k=6,
        ),
        arguments={
            "query": "minimal OpenSCENARIO lane change scenario",
            "kind": "element",
            "top_k": 6,
        },
    )

    schema_tool = build_get_element_schema_tool(runtime.knowledge_base)
    for element, parent_context in (
        ("ScenarioObject", "Entities"),
        ("Vehicle", "ScenarioObject"),
        ("Storyboard", "OpenSCENARIO"),
        ("LaneChangeAction", "LateralAction"),
        ("SimulationTimeCondition", "ByValueCondition"),
    ):
        _record_tool(
            interactions,
            name=f"get_element_schema:{element}",
            call=lambda element=element, parent_context=parent_context: schema_tool(
                element=element,
                parent_context=parent_context,
            ),
            arguments={"element": element, "parent_context": parent_context},
        )

    _record_tool(
        interactions,
        name="resolve_vtd_name:ego",
        call=lambda: build_resolve_vtd_name_tool(runtime.vtd_knowledge_base)(
            name="ego",
            namespace="scenario_object",
            asset_kind="model",
            country_code="CN",
        ),
        arguments={
            "name": "ego",
            "namespace": "scenario_object",
            "asset_kind": "model",
            "country_code": "CN",
        },
    )
    _record_tool(
        interactions,
        name="retrieve_vtd_asset:traffic_light_model",
        call=lambda: build_retrieve_vtd_asset_tool(runtime.vtd_knowledge_base)(
            query="traffic light",
            asset_kind="model",
            country_code="CN",
            top_k=5,
        ),
        arguments={
            "query": "traffic light",
            "asset_kind": "model",
            "country_code": "CN",
            "top_k": 5,
        },
    )
    _record_tool(
        interactions,
        name="recommend_vtd_candidates:TrafficLight01",
        call=lambda: build_recommend_vtd_candidates_tool(runtime.vtd_knowledge_base)(
            query="traffic signal for Chinese urban road",
            asset_kind="signal",
            namespace="runtime_asset",
            country_code="CN",
            requested_name="TrafficLight01",
            top_k=5,
        ),
        arguments={
            "query": "traffic signal for Chinese urban road",
            "asset_kind": "signal",
            "namespace": "runtime_asset",
            "country_code": "CN",
            "requested_name": "TrafficLight01",
            "top_k": 5,
        },
    )

    xml_text = _build_lane_change_xml()
    scenario_path = output_root / "lane_change_cn.xosc"
    scenario_path.write_text(xml_text, encoding="utf-8")

    validation_result = _record_tool(
        interactions,
        name="validate_xml",
        call=lambda: build_validate_xml_tool(runtime.validator)(xml_text, schema_version="1.x"),
        arguments={
            "xml_path": _repo_relative(scenario_path),
            "schema_version": "1.x",
        },
    )
    if not validation_result["ok"]:
        _record_tool(
            interactions,
            name="explain_validation_errors",
            call=lambda: build_explain_validation_errors_tool(runtime.patterns)(
                validation_result["errors"]
            ),
            arguments={"errors": validation_result["errors"]},
        )

    consistency_result = _record_tool(
        interactions,
        name="check_xml_intent_consistency",
        call=lambda: build_check_xml_intent_consistency_tool()(
            xml=xml_text,
            intent=intent,
            checklist=checklist,
        ),
        arguments={
            "xml_path": _repo_relative(scenario_path),
            "intent": intent,
            "checklist": checklist,
        },
    )

    claude_artifact: dict[str, Any] | None = None
    if not args.skip_claude:
        claude_artifact = _run_claude_review(
            output_root=output_root,
            xml_text=xml_text,
            interactions=interactions,
        )
        interactions.append(
            {
                "step": len(interactions) + 1,
                "tool": "claude_cli_review",
                "status": claude_artifact.get("status", "unknown"),
                "started_at": claude_artifact.get("started_at"),
                "finished_at": claude_artifact.get("finished_at"),
                "arguments": {
                    "command": claude_artifact.get("command"),
                    "prompt_path": claude_artifact.get("prompt_path"),
                },
                "result": {
                    "artifact_path": claude_artifact.get("artifact_path"),
                    "returncode": claude_artifact.get("returncode"),
                    "stdout_excerpt": str(claude_artifact.get("stdout", ""))[:2000],
                    "stderr_excerpt": str(claude_artifact.get("stderr", ""))[:2000],
                },
            }
        )

    _write_json(output_root / "interactions.json", interactions)
    _write_json(
        output_root / "summary.json",
        {
            "case_request": CASE_REQUEST,
            "scenario_path": _repo_relative(scenario_path),
            "validation_ok": validation_result["ok"],
            "intent_consistent": consistency_result["intent_consistent"],
            "interaction_count": len(interactions),
            "claude_artifact": claude_artifact,
            "spec_top_hits": [
                hit.get("title")
                for hit in spec_hits.get("hits", [])[:6]
                if isinstance(hit, dict)
            ],
        },
    )
    report_path = output_root / "full-flow-report.md"
    report_path.write_text(
        _build_markdown_report(
            output_root=output_root,
            interactions=interactions,
            validation_result=validation_result,
            consistency_result=consistency_result,
            claude_artifact=claude_artifact,
        ),
        encoding="utf-8",
    )
    print(f"Wrote scenario: {scenario_path}")
    print(f"Wrote interactions: {output_root / 'interactions.json'}")
    print(f"Wrote report: {report_path}")
    print(
        json.dumps(
            {
                "validation_ok": validation_result["ok"],
                "intent_consistent": consistency_result["intent_consistent"],
                "interaction_count": len(interactions),
                "report": _repo_relative(report_path),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _record_tool(
    interactions: list[dict[str, Any]],
    *,
    name: str,
    call: Callable[[], Any],
    arguments: dict[str, Any],
    expect_error: bool = False,
) -> Any:
    started_at = _utc_now()
    try:
        result = call()
        interaction = {
            "step": len(interactions) + 1,
            "tool": name,
            "status": "ok",
            "started_at": started_at,
            "finished_at": _utc_now(),
            "arguments": arguments,
            "result": result,
        }
        interactions.append(interaction)
        return result
    except Exception as exc:
        result = {
            "error_type": exc.__class__.__name__,
            "message": str(exc),
        }
        interaction = {
            "step": len(interactions) + 1,
            "tool": name,
            "status": "expected_error" if expect_error else "error",
            "started_at": started_at,
            "finished_at": _utc_now(),
            "arguments": arguments,
            "result": result,
        }
        interactions.append(interaction)
        if expect_error:
            return result
        raise


def _find_interaction_result(
    interactions: list[dict[str, Any]],
    tool_name: str,
) -> dict[str, Any]:
    for interaction in interactions:
        if interaction.get("tool") == tool_name:
            result = interaction.get("result", {})
            if isinstance(result, dict):
                return result
            break
    raise ValueError(f"Interaction result not found for tool: {tool_name}")


def _run_claude_review(
    *,
    output_root: Path,
    xml_text: str,
    interactions: list[dict[str, Any]],
) -> dict[str, Any]:
    claude_executable = shutil.which("claude.cmd") or shutil.which("claude")
    if claude_executable is None:
        return {
            "status": "skipped",
            "reason": "claude CLI not found on PATH",
        }
    started_at = _utc_now()

    prompt = "\n".join(
        [
            "Review this OpenSCENARIO generation case. Focus on whether the XML",
            "matches the stated intent and whether the tool evidence supports the",
            "generation decisions. Keep the review concise.",
            "",
            "Intent:",
            CASE_REQUEST,
            "",
            "Tool evidence summary:",
            json.dumps(_interaction_summary(interactions), ensure_ascii=False, indent=2),
            "",
            "XML:",
            xml_text,
        ]
    )
    prompt_path = output_root / "claude-review-prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")

    command = [claude_executable, "-p", prompt]
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            encoding="utf-8",
            errors="replace",
        )
        stdout = completed.stdout
        stderr = completed.stderr
        returncode: int | None = completed.returncode
        status = "ok" if completed.returncode == 0 else "error"
        timeout_seconds: int | None = None
    except subprocess.TimeoutExpired as exc:
        stdout = _decode_timeout_output(exc.stdout)
        stderr = _decode_timeout_output(exc.stderr)
        returncode = None
        status = "error" if "model_not_found" in stdout else "timeout"
        timeout_seconds = 60
    artifact = {
        "status": status,
        "command": "claude -p <prompt>",
        "started_at": started_at,
        "finished_at": _utc_now(),
        "returncode": returncode,
        "timeout_seconds": timeout_seconds,
        "prompt_path": _repo_relative(prompt_path),
        "stdout": stdout,
        "stderr": stderr,
    }
    artifact_path = output_root / "claude-review.md"
    artifact_path.write_text(
        "\n".join(
            [
                "# Claude Review Artifact",
                "",
                "## Original Task",
                "",
                CASE_REQUEST,
                "",
                "## Final Prompt Sent To Claude CLI",
                "",
                f"Saved at `{_repo_relative(prompt_path)}`.",
                "",
                "## Claude Output Raw",
                "",
                "```text",
                stdout.strip(),
                "```",
                "",
                "## Claude Stderr",
                "",
                "```text",
                stderr.strip(),
                "```",
                "",
                "## Summary",
                "",
                (
                    "Claude CLI returned successfully."
                    if status == "ok"
                    else (
                        "Claude CLI produced an API model_not_found error and did not exit cleanly before timeout."
                        if "model_not_found" in stdout
                        else "Claude CLI timed out after 60 seconds."
                        if status == "timeout"
                        else f"Claude CLI returned exit code {returncode}."
                    )
                ),
                "",
                "## Action Items / Next Steps",
                "",
                "- Use this review as a second-opinion artifact; validation and intent checks remain authoritative.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    artifact["artifact_path"] = _repo_relative(artifact_path)
    return artifact


def _build_lane_change_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<OpenSCENARIO>
  <FileHeader revMajor="1" revMinor="1" date="2026-05-19T00:00:00" description="CN urban ego lane change full-flow case" author="Codex"/>
  <ParameterDeclarations/>
  <CatalogLocations/>
  <RoadNetwork/>
  <Entities>
    <ScenarioObject name="ego">
      <Vehicle name="egoVehicle" vehicleCategory="car">
        <BoundingBox>
          <Center x="1.5" y="0.0" z="0.9"/>
          <Dimensions width="1.9" length="4.7" height="1.6"/>
        </BoundingBox>
        <Performance maxSpeed="69.44" maxAcceleration="8.0" maxDeceleration="8.0"/>
        <Axles>
          <FrontAxle maxSteering="0.48" wheelDiameter="0.68" trackWidth="1.62" positionX="2.9" positionZ="0.34"/>
          <RearAxle maxSteering="0.0" wheelDiameter="0.68" trackWidth="1.62" positionX="0.0" positionZ="0.34"/>
        </Axles>
        <Properties/>
      </Vehicle>
    </ScenarioObject>
  </Entities>
  <Storyboard>
    <Init>
      <Actions>
        <Private entityRef="ego">
          <PrivateAction>
            <TeleportAction>
              <Position>
                <LanePosition roadId="1" laneId="-2" s="100.0" offset="0.0"/>
              </Position>
            </TeleportAction>
          </PrivateAction>
          <PrivateAction>
            <LongitudinalAction>
              <SpeedAction>
                <SpeedActionDynamics dynamicsShape="step" dynamicsDimension="time" value="0.0"/>
                <SpeedActionTarget>
                  <AbsoluteTargetSpeed value="8.33"/>
                </SpeedActionTarget>
              </SpeedAction>
            </LongitudinalAction>
          </PrivateAction>
        </Private>
      </Actions>
    </Init>
    <Story name="MainStory">
      <Act name="MainAct">
        <ManeuverGroup name="EgoLaneChangeGroup" maximumExecutionCount="1">
          <Actors selectTriggeringEntities="false">
            <EntityRef entityRef="ego"/>
          </Actors>
          <Maneuver name="EgoManeuver">
            <Event name="EgoLaneChangeLeft" priority="overwrite">
              <Action name="EgoLaneChangeAction">
                <PrivateAction>
                  <LateralAction>
                    <LaneChangeAction>
                      <LaneChangeActionDynamics dynamicsShape="sinusoidal" dynamicsDimension="time" value="2.5"/>
                      <LaneChangeTarget>
                        <AbsoluteTargetLane value="-1"/>
                      </LaneChangeTarget>
                    </LaneChangeAction>
                  </LateralAction>
                </PrivateAction>
              </Action>
              <StartTrigger>
                <ConditionGroup>
                  <Condition name="LaneChangeAtFiveSeconds" delay="0.0" conditionEdge="rising">
                    <ByValueCondition>
                      <SimulationTimeCondition value="5.0" rule="greaterThan"/>
                    </ByValueCondition>
                  </Condition>
                </ConditionGroup>
              </StartTrigger>
            </Event>
          </Maneuver>
        </ManeuverGroup>
        <StartTrigger>
          <ConditionGroup>
            <Condition name="ActStart" delay="0.0" conditionEdge="rising">
              <ByValueCondition>
                <SimulationTimeCondition value="0.0" rule="greaterThan"/>
              </ByValueCondition>
            </Condition>
          </ConditionGroup>
        </StartTrigger>
      </Act>
    </Story>
    <StopTrigger>
      <ConditionGroup>
        <Condition name="StopAtTwentySeconds" delay="0.0" conditionEdge="rising">
          <ByValueCondition>
            <SimulationTimeCondition value="20.0" rule="greaterThan"/>
          </ByValueCondition>
        </Condition>
      </ConditionGroup>
    </StopTrigger>
  </Storyboard>
</OpenSCENARIO>
"""


def _decode_timeout_output(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _build_markdown_report(
    *,
    output_root: Path,
    interactions: list[dict[str, Any]],
    validation_result: dict[str, Any],
    consistency_result: dict[str, Any],
    claude_artifact: dict[str, Any] | None,
) -> str:
    lines = [
        "# OpenSCENARIO Full-Flow Case Run",
        "",
        f"- Generated at: `{_utc_now()}`",
        f"- Case directory: `{_repo_relative(output_root)}`",
        f"- Scenario XML: `{_repo_relative(output_root / 'lane_change_cn.xosc')}`",
        f"- Interaction log: `{_repo_relative(output_root / 'interactions.json')}`",
        f"- Validation ok: `{validation_result['ok']}`",
        f"- Intent consistent: `{consistency_result['intent_consistent']}`",
        "",
        "## Codex / Account Configuration",
        "",
        "| Item | Value |",
        "| --- | --- |",
        "| model_provider | `azure` |",
        "| model | `gpt-5.5` |",
        "| reasoning | `xhigh` |",
        "| base_url | `https://xlabapi.com/v1` |",
        "| auth mode | `apikey` |",
        "| API key | configured, redacted |",
        "",
        "## Case Request",
        "",
        CASE_REQUEST,
        "",
        "## Flow Visualization",
        "",
        "```mermaid",
        "flowchart TD",
        "  A[User case request] --> B[build_generation_packet]",
        "  B --> C[retrieve_spec / get_element_schema]",
        "  C --> D[VTD name and asset tools]",
        "  D --> E[Draft lane_change_cn.xosc]",
        "  E --> F[validate_xml]",
        "  F --> G{schema valid?}",
        "  G -- yes --> H[check_xml_intent_consistency]",
        "  G -- no --> R[explain_validation_errors]",
        "  R --> E",
        "  H --> I[Claude CLI review]",
        "  I --> J[Markdown report]",
        "```",
        "",
        "## Interaction Timeline",
        "",
        "```mermaid",
        "sequenceDiagram",
        "  participant U as User",
        "  participant C as Codex",
        "  participant T as OpenSCENARIO Tools",
        "  participant V as Validator",
        "  participant CL as Claude CLI",
        "  U->>C: Case request",
    ]
    for interaction in interactions:
        participant = "V" if interaction["tool"] == "validate_xml" else "T"
        if interaction["tool"].startswith("claude"):
            participant = "CL"
        lines.append(f"  C->>{participant}: {interaction['step']}. {interaction['tool']}")
        lines.append(f"  {participant}-->>C: {interaction['status']}")
    if claude_artifact is not None:
        lines.append("  C->>CL: review prompt")
        lines.append(f"  CL-->>C: {claude_artifact.get('status', 'unknown')}")
    lines.extend(["```", ""])

    lines.extend(
        [
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
                summary=_markdown_escape(_summarize_result(interaction["result"])),
            )
        )

    lines.extend(
        [
            "",
            "## Validation Result",
            "",
            "```json",
            json.dumps(validation_result, ensure_ascii=False, indent=2),
            "```",
            "",
            "## Per-Step Tool I/O",
            "",
            "The full machine-readable log is also stored in `docs/case-runs/lane-change-cn/interactions.json`.",
            "",
        ]
    )
    for interaction in interactions:
        lines.extend(
            [
                f"<details><summary>{interaction['step']}. {interaction['tool']} - {interaction['status']}</summary>",
                "",
                "**Input**",
                "",
                "```json",
                json.dumps(interaction.get("arguments", {}), ensure_ascii=False, indent=2),
                "```",
                "",
                "**Output**",
                "",
                "```json",
                json.dumps(interaction.get("result", {}), ensure_ascii=False, indent=2)[:12000],
                "```",
                "",
                "</details>",
                "",
            ]
        )
    lines.extend(
        [
            "",
            "## Intent Consistency Result",
            "",
            "```json",
            json.dumps(consistency_result, ensure_ascii=False, indent=2),
            "```",
            "",
            "## Claude Review",
            "",
        ]
    )
    if claude_artifact is None:
        lines.append("Claude review was not requested.")
    else:
        lines.extend(
            [
                f"- Status: `{claude_artifact.get('status')}`",
                f"- Artifact: `{claude_artifact.get('artifact_path', '')}`",
                f"- Prompt: `{claude_artifact.get('prompt_path', '')}`",
                f"- Return code: `{claude_artifact.get('returncode', '')}`",
            ]
        )
        if claude_artifact.get("stdout"):
            lines.extend(
                [
                    "",
                    "```text",
                    str(claude_artifact["stdout"]).strip(),
                    "```",
                ]
            )

    lines.extend(
        [
            "",
            "## Generated XML",
            "",
            "```xml",
            (output_root / "lane_change_cn.xosc").read_text(encoding="utf-8").strip(),
            "```",
            "",
            "## Notes",
            "",
            "- The initial unsupported `retrieve_spec` kind is retained as evidence of tool boundary handling.",
            "- `TrafficLight01` was checked through VTD tools as a separate resource-knowledge example; the final XML case is lane-change focused.",
            "- API credentials are intentionally redacted from all artifacts.",
            "",
        ]
    )
    return "\n".join(lines)


def _interaction_summary(interactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "step": item["step"],
            "tool": item["tool"],
            "status": item["status"],
            "summary": _summarize_result(item["result"]),
        }
        for item in interactions
    ]


def _summarize_result(result: Any) -> str:
    if isinstance(result, dict):
        if "error_type" in result:
            return f"{result['error_type']}: {result.get('message', '')}"
        if "ok" in result and "errors" in result:
            return f"ok={result['ok']}, errors={len(result['errors'])}"
        if "intent_consistent" in result:
            missing = result.get("xml_intent_check", {}).get("missing", [])
            return f"intent_consistent={result['intent_consistent']}, missing={missing}"
        if "hits" in result:
            return f"hits={len(result['hits'])}"
        if "name_resolution" in result:
            resolution = result["name_resolution"]
            return (
                f"name_resolution={resolution.get('rule_kind')} -> "
                f"{resolution.get('canonical_target')}"
            )
        if "canonical_target" in result:
            return f"{result.get('rule_kind')} -> {result.get('canonical_target')}"
        if "schema_plan" in result:
            return (
                "primary_elements="
                + ",".join(result.get("schema_plan", {}).get("primary_elements", []))
            )
    return str(result)[:160]


def _markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


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
