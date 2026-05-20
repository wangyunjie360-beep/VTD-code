from __future__ import annotations

import argparse
import functools
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from openscenario_mcp.tools.validate import build_validate_xml_tool
from openscenario_mcp.validator.adapter import ValidatorAdapter


BENCHMARK_NAMES = [
    "minimal-single-vehicle",
    "two-vehicle-follow",
    "triggered-deceleration",
    "triggered-lane-change",
]


def default_repo_root() -> Path:
    return REPO_ROOT


@functools.lru_cache(maxsize=None)
def validate_xml_tool(module_name: str | None = None):
    adapter = ValidatorAdapter(module_name) if module_name else None
    return build_validate_xml_tool(adapter=adapter)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_result_xml(
    result_path: Path,
    *,
    validator_module: str | None,
) -> tuple[bool, str]:
    xml_text = result_path.read_text(encoding="utf-8")
    if not xml_text.strip():
        return False, f"empty XML result: {result_path.name}"

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        return False, f"XML is not well-formed: {exc}"

    if root.tag not in {"OpenScenario", "OpenSCENARIO"}:
        return False, f"unexpected XML root '{root.tag}'"

    validation_result = validate_xml_tool(validator_module)(xml_text)
    if validation_result["ok"]:
        return True, "schema valid"

    messages = ", ".join(
        error["message"] for error in validation_result["errors"] if error["message"]
    )
    if not messages:
        messages = "unknown schema validation error"
    return False, f"schema validation failed: {messages}"


def validate_intent_sidecar(
    intent_path: Path,
    schema: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        payload = load_json(intent_path)
    except json.JSONDecodeError as exc:
        return None, [f"Intent sidecar is not valid JSON for {intent_path.name}: {exc}"]
    except OSError as exc:
        return None, [f"Could not read {intent_path.name}: {exc}"]

    if not isinstance(payload, dict):
        return None, [f"Intent sidecar must contain a JSON object: {intent_path.name}"]

    errors: list[str] = []
    _validate_additional_properties(
        payload,
        schema.get("properties", {}),
        context=intent_path.name,
        errors=errors,
    )
    required_keys = schema.get("required", [])
    for key in required_keys:
        if key not in payload:
            errors.append(f"Intent sidecar is missing '{key}' in {intent_path.name}")

    parsed_intent = payload.get("parsed_intent")
    if not isinstance(parsed_intent, dict):
        errors.append(f"'parsed_intent' must be an object in {intent_path.name}")
    else:
        parsed_schema = schema.get("properties", {}).get("parsed_intent", {})
        _validate_additional_properties(
            parsed_intent,
            parsed_schema.get("properties", {}),
            context=f"{intent_path.name}:parsed_intent",
            errors=errors,
        )
        parsed_required = (
            parsed_schema.get("required", [])
        )
        for key in parsed_required:
            if key not in parsed_intent:
                errors.append(f"'parsed_intent' is missing '{key}' in {intent_path.name}")

    xml_intent_check = payload.get("xml_intent_check")
    if not isinstance(xml_intent_check, dict):
        errors.append(f"'xml_intent_check' must be an object in {intent_path.name}")
    else:
        xml_check_schema = schema.get("properties", {}).get("xml_intent_check", {})
        _validate_additional_properties(
            xml_intent_check,
            xml_check_schema.get("properties", {}),
            context=f"{intent_path.name}:xml_intent_check",
            errors=errors,
        )
        for key in ("matched", "missing", "extra"):
            value = xml_intent_check.get(key)
            if not isinstance(value, list) or any(
                not isinstance(item, str) for item in value
            ):
                errors.append(
                    f"'xml_intent_check.{key}' must be a list of strings in {intent_path.name}"
                )

    if not isinstance(payload.get("schema_valid"), bool):
        errors.append(f"'schema_valid' must be a boolean in {intent_path.name}")
    if not isinstance(payload.get("intent_consistent"), bool):
        errors.append(f"'intent_consistent' must be a boolean in {intent_path.name}")
    if not isinstance(payload.get("remaining_blockers"), list) or any(
        not isinstance(item, str) for item in payload.get("remaining_blockers", [])
    ):
        errors.append(
            f"'remaining_blockers' must be a list of strings in {intent_path.name}"
        )

    return payload if not errors else None, errors


def _validate_additional_properties(
    payload: dict[str, Any],
    allowed_properties: dict[str, Any],
    *,
    context: str,
    errors: list[str],
) -> None:
    if not isinstance(allowed_properties, dict):
        return
    unexpected_keys = sorted(
        key for key in payload.keys() if key not in allowed_properties
    )
    for key in unexpected_keys:
        errors.append(f"Unexpected property '{key}' in {context}")


def evaluate_benchmark(
    benchmark_name: str,
    results_dir: Path,
    schema: dict[str, Any],
    *,
    validator_module: str | None,
) -> tuple[dict[str, str] | None, list[str]]:
    xml_path = results_dir / f"{benchmark_name}.xml"
    intent_path = results_dir / f"{benchmark_name}.intent.json"

    structural_errors: list[str] = []
    if not xml_path.exists():
        structural_errors.append(f"Missing XML result: {xml_path.name}")
    if not intent_path.exists():
        structural_errors.append(f"Missing intent sidecar: {intent_path.name}")
    if structural_errors:
        return None, structural_errors

    payload, payload_errors = validate_intent_sidecar(intent_path, schema)
    if payload_errors:
        return None, payload_errors
    assert payload is not None

    xml_ok, xml_note = validate_result_xml(
        xml_path,
        validator_module=validator_module,
    )

    xml_intent_check = payload["xml_intent_check"]
    missing_items = list(xml_intent_check["missing"])
    extra_items = list(xml_intent_check["extra"])
    remaining_blockers = list(payload["remaining_blockers"])

    notes: list[str] = []
    if not xml_ok:
        notes.append(xml_note)
    if payload["schema_valid"] != xml_ok:
        notes.append("sidecar schema_valid disagrees with validator output")
    matched_items = list(xml_intent_check["matched"])
    if not matched_items:
        notes.append("xml_intent_check.matched is empty")
    if missing_items:
        notes.append("missing intent items: " + ", ".join(missing_items))
    if extra_items:
        notes.append("extra XML items: " + ", ".join(extra_items))
    if remaining_blockers:
        notes.append("remaining blockers: " + ", ".join(remaining_blockers))
    if not payload["intent_consistent"]:
        notes.append("intent_consistent is false")

    status = (
        "pass"
        if xml_ok
        and payload["schema_valid"]
        and payload["intent_consistent"]
        and bool(matched_items)
        and not missing_items
        and not extra_items
        and not remaining_blockers
        else "bounded_failure"
    )

    if not notes:
        notes.append("schema-valid and intent-consistent")

    return {
        "benchmark": benchmark_name,
        "status": status,
        "notes": "; ".join(notes),
    }, []


def render_run_log(entries: list[dict[str, str]], previous_text: str) -> str:
    marker = "## Task 8 TDD Verification"
    preserved_tail = ""
    if marker in previous_text:
        preserved_tail = previous_text[previous_text.index(marker) :].strip()

    lines = [
        "# Benchmark Run Log",
        "",
        "This file records the latest validation result for each benchmark prompt. A run is marked `pass` only when the XML is schema-valid and the sidecar reports `intent_consistent=true` with no missing, extra, or blocked items.",
        "",
        "## Benchmark Outcomes",
        "",
        "| benchmark | status | notes |",
        "| --- | --- | --- |",
    ]

    for entry in entries:
        notes = entry["notes"].replace("|", "/")
        lines.append(f"| {entry['benchmark']} | {entry['status']} | {notes} |")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Start a fresh Codex session after installation so the new skill is discoverable.",
            "- `pass` means schema-valid plus intent-consistent.",
            "- `bounded_failure` means the run produced an artifact, but it still failed schema validation or intent checks within the allowed retry budget.",
        ]
    )

    if preserved_tail:
        lines.extend(["", preserved_tail])

    return "\n".join(lines) + "\n"


def validate_results_directory(
    results_dir: Path,
    schema_path: Path,
    benchmark_names: Sequence[str],
    *,
    require_outputs: bool,
    validator_module: str | None,
) -> tuple[list[str], list[dict[str, str]], bool]:
    structural_errors: list[str] = []
    entries: list[dict[str, str]] = []
    found_outputs = False

    if not results_dir.exists():
        return [f"Results directory does not exist: {results_dir}"], entries, found_outputs

    run_log_path = results_dir / "run-log.md"
    if not run_log_path.exists():
        return [f"Missing run log scaffold: {run_log_path}"], entries, found_outputs

    try:
        schema = load_json(schema_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Could not load intent schema {schema_path}: {exc}"], entries, found_outputs

    for benchmark_name in benchmark_names:
        xml_path = results_dir / f"{benchmark_name}.xml"
        intent_path = results_dir / f"{benchmark_name}.intent.json"
        xml_exists = xml_path.exists()
        intent_exists = intent_path.exists()

        if not xml_exists and not intent_exists:
            if require_outputs or benchmark_name in BENCHMARK_NAMES:
                structural_errors.append(f"Missing XML result: {xml_path.name}")
                structural_errors.append(f"Missing intent sidecar: {intent_path.name}")
            continue

        found_outputs = True
        entry, entry_errors = evaluate_benchmark(
            benchmark_name,
            results_dir,
            schema,
            validator_module=validator_module,
        )
        structural_errors.extend(entry_errors)
        if entry is not None:
            entries.append(entry)

    return structural_errors, entries, found_outputs


def update_run_log(results_dir: Path, entries: list[dict[str, str]]) -> Path:
    run_log_path = results_dir / "run-log.md"
    previous_text = run_log_path.read_text(encoding="utf-8")
    run_log_path.write_text(render_run_log(entries, previous_text), encoding="utf-8")
    return run_log_path


def build_parser() -> argparse.ArgumentParser:
    repo_root = default_repo_root()
    parser = argparse.ArgumentParser(
        description="Validate benchmark result XML and intent sidecars."
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "benchmarks" / "results",
        help="Directory containing benchmark result XML and intent sidecars.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=repo_root / "benchmarks" / "intent-schema.json",
        help="Intent schema used to validate result sidecars.",
    )
    parser.add_argument(
        "--benchmarks",
        nargs="*",
        default=BENCHMARK_NAMES,
        help="Benchmark names to validate without file extensions.",
    )
    parser.add_argument(
        "--require-outputs",
        action="store_true",
        help="Fail if any expected XML result or intent sidecar is missing.",
    )
    parser.add_argument(
        "--validator-module",
        default=None,
        help="Optional validator module import path. Defaults to the real validator.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    errors, entries, found_outputs = validate_results_directory(
        results_dir=args.results_dir,
        schema_path=args.schema,
        benchmark_names=args.benchmarks,
        require_outputs=args.require_outputs,
        validator_module=args.validator_module,
    )
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    if not found_outputs:
        print(
            "No benchmark result XML or intent sidecars are present yet; benchmark scaffolding is valid."
        )
        return 0

    run_log_path = update_run_log(args.results_dir, entries)
    print(f"Validated benchmark outputs in {args.results_dir}")
    print(f"Updated run log: {run_log_path}")
    if any(entry["status"] != "pass" for entry in entries):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
