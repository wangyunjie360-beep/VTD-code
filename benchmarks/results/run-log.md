# Benchmark Run Log

This file records the latest validation result for each benchmark prompt. A run is marked `pass` only when the XML is schema-valid and the sidecar reports `intent_consistent=true` with no missing, extra, or blocked items.

## Benchmark Outcomes

| benchmark | status | notes |
| --- | --- | --- |
| minimal-single-vehicle | pass | schema-valid and intent-consistent |
| two-vehicle-follow | pass | schema-valid and intent-consistent |
| triggered-deceleration | pass | schema-valid and intent-consistent |
| triggered-lane-change | pass | schema-valid and intent-consistent |

## Notes

- Start a fresh Codex session after installation so the new skill is discoverable.
- `pass` means schema-valid plus intent-consistent.
- `bounded_failure` means the run produced an artifact, but it still failed schema validation or intent checks within the allowed retry budget.

## Task 8 TDD Verification

### RED reproduction

Reproduced the failing state by copying `tests/unit/test_benchmark_assets.py` into a temporary root with no Task 8 assets and running:

```powershell
python -m pytest <temp>\tests\unit\test_benchmark_assets.py -v -p no:cacheprovider
```

Observed failure summary:

- `test_benchmark_assets_exist` failed on missing `skills/openscenario-xml-generator/SKILL.md`
- the remaining benchmark-asset checks also failed because the benchmark scaffolding was absent

### GREEN verification

Ran the focused benchmark asset suite in this worktree after implementing Task 8:

```powershell
python -m pytest tests/unit/test_benchmark_assets.py -v -p no:cacheprovider
```

Observed result:

- `7 passed in 0.29s`
- `python scripts/validate_benchmark_output.py` reported that the benchmark scaffolding is valid with no result XML or intent sidecars present yet
