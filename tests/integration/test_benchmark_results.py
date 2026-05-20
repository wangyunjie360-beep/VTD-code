from __future__ import annotations

from scripts.validate_benchmark_output import validate_results_directory

import json
import re
from pathlib import Path


def test_every_benchmark_prompt_has_a_recorded_result() -> None:
    prompts = sorted(Path("benchmarks/prompts").glob("*.md"))
    run_log = Path("benchmarks/results/run-log.md").read_text(encoding="utf-8")

    assert prompts

    for prompt in prompts:
        stem = prompt.stem
        xml_path = Path(f"benchmarks/results/{stem}.xml")
        intent_path = Path(f"benchmarks/results/{stem}.intent.json")
        guidance_path = Path(f"benchmarks/results/{stem}.guidance.json")

        assert xml_path.exists(), stem
        assert intent_path.exists(), stem
        assert guidance_path.exists(), stem

        report = json.loads(intent_path.read_text(encoding="utf-8"))
        guidance = json.loads(guidance_path.read_text(encoding="utf-8"))
        assert "parsed_intent" in report
        assert "xml_intent_check" in report
        assert "schema_valid" in report
        assert "intent_consistent" in report
        assert "remaining_blockers" in report
        parsed_intent = report["parsed_intent"]
        for key in ("story_actions", "triggers", "stop_conditions"):
            assert isinstance(parsed_intent[key], list)
            assert all(isinstance(item, (str, dict)) for item in parsed_intent[key])
        assert isinstance(report["xml_intent_check"]["matched"], list)
        assert isinstance(report["xml_intent_check"]["missing"], list)
        assert isinstance(report["xml_intent_check"]["extra"], list)
        assert report["xml_intent_check"]["matched"]
        assert guidance["guidance"]["element"]

        row_pattern = rf"^\|\s*{re.escape(stem)}\s*\|\s*pass\s*\|"
        assert re.search(row_pattern, run_log, re.MULTILINE), stem

    errors, entries, found_outputs = validate_results_directory(
        Path("benchmarks/results"),
        Path("benchmarks/intent-schema.json"),
        [prompt.stem for prompt in prompts],
        require_outputs=True,
        validator_module=None,
    )
    assert found_outputs is True
    assert errors == []
    assert all(entry["status"] == "pass" for entry in entries)
