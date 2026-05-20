from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_path(relative_path: str) -> Path:
    return REPO_ROOT / relative_path


def test_benchmark_assets_exist() -> None:
    expected_files = [
        "skills/openscenario-xml-generator/SKILL.md",
        "scripts/build_benchmark_guidance.py",
        "scripts/build_guidance_packet.py",
        "scripts/install_codex_skill.py",
        "scripts/validate_benchmark_output.py",
        "benchmarks/guidance-inputs.json",
        "benchmarks/intent-schema.json",
        "benchmarks/prompts/minimal-single-vehicle.md",
        "benchmarks/prompts/two-vehicle-follow.md",
        "benchmarks/prompts/triggered-deceleration.md",
        "benchmarks/prompts/triggered-lane-change.md",
        "benchmarks/invalid_xml/missing-actors.xml",
        "benchmarks/invalid_xml/invalid-enum.xml",
        "benchmarks/results/.gitkeep",
        "benchmarks/results/minimal-single-vehicle.guidance.json",
        "benchmarks/results/two-vehicle-follow.guidance.json",
        "benchmarks/results/triggered-deceleration.guidance.json",
        "benchmarks/results/triggered-lane-change.guidance.json",
        "benchmarks/results/run-log.md",
    ]

    for relative_path in expected_files:
        assert repo_path(relative_path).exists(), relative_path


def test_intent_schema_defines_required_result_keys() -> None:
    schema = json.loads(
        repo_path("benchmarks/intent-schema.json").read_text(encoding="utf-8")
    )

    assert schema["type"] == "object"
    assert schema["required"] == [
        "parsed_intent",
        "xml_intent_check",
        "schema_valid",
        "intent_consistent",
        "remaining_blockers",
    ]
    assert set(schema["properties"]) >= {
        "parsed_intent",
        "xml_intent_check",
        "schema_valid",
        "intent_consistent",
        "remaining_blockers",
    }
    assert schema["properties"]["xml_intent_check"]["required"] == [
        "matched",
        "missing",
        "extra",
    ]


def test_skill_guidance_mentions_required_workflow() -> None:
    skill_text = repo_path("skills/openscenario-xml-generator/SKILL.md").read_text(
        encoding="utf-8"
    )

    required_fragments = [
        "ScenarioIntent",
        "build_xml_guidance",
        "retrieve_spec",
        "strategy_summary",
        "get_element_schema",
        "parent_context",
        "strategy",
        "validate_xml",
        "explain_validation_errors",
        "repair_strategy",
        "repair only the affected region",
        "bounded retry",
        "xml_intent_check",
        "OpenX scene code",
        "VTD",
        "VTD scene file",
        "simulation scenario file",
        "content_model_kind",
        "child_groups",
        "contextual_variants",
        "reference_kind",
        "parent_context",
        "strategy",
        "deprecated",
    ]

    for fragment in required_fragments:
        assert fragment in skill_text, fragment


def test_run_log_records_benchmark_outcomes() -> None:
    run_log_text = repo_path("benchmarks/results/run-log.md").read_text(
        encoding="utf-8"
    )

    assert "Benchmark Outcomes" in run_log_text
    for benchmark in (
        "minimal-single-vehicle",
        "two-vehicle-follow",
        "triggered-deceleration",
        "triggered-lane-change",
    ):
        assert f"| {benchmark} | pass |" in run_log_text


def test_run_log_records_task_8_tdd_evidence() -> None:
    run_log_text = repo_path("benchmarks/results/run-log.md").read_text(
        encoding="utf-8"
    )

    assert "Task 8 TDD Verification" in run_log_text
    assert "RED reproduction" in run_log_text
    assert "GREEN verification" in run_log_text


def test_validate_benchmark_output_accepts_scaffold_without_results() -> None:
    results_dir = repo_path("benchmarks/results")
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_benchmark_output.py",
            "--results-dir",
            str(results_dir),
            "--schema",
            str(repo_path("benchmarks/intent-schema.json")),
            "--benchmarks",
            "does-not-exist-yet",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "scaffolding is valid" in result.stdout


def test_validate_benchmark_output_requires_default_benchmark_outputs(
    tmp_path: Path,
) -> None:
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    results_dir.joinpath("run-log.md").write_text(
        repo_path("benchmarks/results/run-log.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_benchmark_output.py",
            "--results-dir",
            str(results_dir),
            "--schema",
            str(repo_path("benchmarks/intent-schema.json")),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Missing XML result" in result.stderr


def test_validate_benchmark_output_rejects_schema_invalid_result_xml(
    tmp_path: Path,
) -> None:
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    results_dir.joinpath("run-log.md").write_text(
        repo_path("benchmarks/results/run-log.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    results_dir.joinpath("minimal-single-vehicle.xml").write_text(
        repo_path("benchmarks/invalid_xml/missing-actors.xml").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    results_dir.joinpath("minimal-single-vehicle.intent.json").write_text(
        json.dumps(
            {
                "parsed_intent": {
                    "parameters": [],
                    "entities": [],
                    "environment": {},
                    "map_context": {},
                    "init_actions": [],
                    "story_actions": [],
                    "triggers": [],
                    "stop_conditions": [],
                    "assumptions": [],
                },
                "xml_intent_check": {
                    "matched": [],
                    "missing": ["Actors"],
                    "extra": [],
                },
                "schema_valid": False,
                "intent_consistent": False,
                "remaining_blockers": ["schema invalid"],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_benchmark_output.py",
            "--results-dir",
            str(results_dir),
            "--schema",
            str(repo_path("benchmarks/intent-schema.json")),
            "--benchmarks",
            "minimal-single-vehicle",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Validated benchmark outputs" in result.stdout

    updated_run_log = results_dir.joinpath("run-log.md").read_text(encoding="utf-8")
    assert "minimal-single-vehicle" in updated_run_log
    assert "bounded_failure" in updated_run_log
