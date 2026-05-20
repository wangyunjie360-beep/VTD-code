# OpenSCENARIO Full Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the current OpenSCENARIO structured knowledge base from the current partial corpus to full `OpenSCENARIO.xsd` element coverage, plus the type and metadata support needed for reliable retrieval, validation repair, and XML generation.

**Architecture:** Treat `knowledge/raw/schema/OpenSCENARIO.xsd` as the authority of record. First build deterministic extraction and coverage-report tooling, then generate normalized stubs for all missing element records, then enrich those records in parallel by schema domain, and finally tighten retrieval/runtime/tests so full coverage becomes a continuously enforced invariant rather than a one-time milestone.

**Tech Stack:** Python 3.14, `pytest`, `xml.etree.ElementTree` or `lxml`, JSON structured records under `knowledge/structured/`, existing `openscenario_mcp` runtime/tooling, git worktrees, fresh subagents per task

---

## Full Coverage Definition

This plan defines "full" against the local XSD, not against prose docs:

- all `302` distinct XSD element names represented by structured records under `knowledge/structured/elements/`
- all child references in those records closed against existing structured records
- all relevant schema metadata preserved for generation:
  - parent contexts
  - required and optional attributes
  - child multiplicity
  - `sequence` / `choice` / `all` semantics
  - enum restrictions
  - simple type pattern / union hints where relevant
  - deprecation metadata from `xsd:appinfo`
  - contextual variants where one XML element name maps to multiple schema types
- runtime and retrieval code continue to load and return the expanded records
- coverage tests fail if any future XSD element is unrepresented

Current baseline before this plan:

- `knowledge/structured/elements/*.json`: `72` records
- XSD distinct element names: `302`
- missing structured element records: `230`

## Recommended Parallel Execution Topology

Use one controller and eight fresh implementation subagents on separate worktrees.

- Controller: owns the aggregation branch, sequencing, reviews, and final verification
- Worker A: extraction tooling and coverage-report infrastructure
- Worker B: core/root/entities/catalog domain records
- Worker C: positions/routing/trajectory/geometry domain records
- Worker D: actions/controllers/appearance/trailer domain records
- Worker E: conditions/triggers/value-logic domain records
- Worker F: traffic/environment/distribution domain records
- Worker G: runtime/retrieval/model integration
- Worker H: final regression gate, docs, and post-merge verification only

If your environment exposes explicit model tiers, use the highest-capability model available for all workers and both reviewers. If explicit `gpt5.4 xhigh` selection is unavailable, use the most capable worker role the environment supports.

## Planned File Structure

### Extraction and coverage infrastructure

- Create: `src/openscenario_mcp/knowledge/xsd_inventory.py`
- Create: `src/openscenario_mcp/knowledge/xsd_parser.py`
- Create: `scripts/report_schema_coverage.py`
- Create: `scripts/generate_xsd_record_stubs.py`
- Create: `knowledge/structured/schema_scope.json`
- Create: `knowledge/structured/coverage_report.json`
- Create: `knowledge/structured/manifests/domain-core-entities.txt`
- Create: `knowledge/structured/manifests/domain-routing-geometry.txt`
- Create: `knowledge/structured/manifests/domain-actions-control.txt`
- Create: `knowledge/structured/manifests/domain-conditions-values.txt`
- Create: `knowledge/structured/manifests/domain-traffic-environment.txt`

### Structured knowledge records

- Modify: `knowledge/structured/mvp_scope.json`
- Modify/Create: `knowledge/structured/elements/*.json`

### Runtime and retrieval integration

- Modify: `src/openscenario_mcp/models.py`
- Modify: `src/openscenario_mcp/knowledge/loader.py`
- Modify: `src/openscenario_mcp/runtime.py`
- Modify: `src/openscenario_mcp/knowledge/search.py`
- Modify: `src/openscenario_mcp/tools/schema.py`
- Modify: `src/openscenario_mcp/tools/retrieve_spec.py`

### Tests

- Create: `tests/unit/test_xsd_inventory.py`
- Create: `tests/unit/test_schema_coverage_report.py`
- Create: `tests/unit/test_full_schema_scope.py`
- Create: `tests/unit/test_domain_core_entities.py`
- Create: `tests/unit/test_domain_routing_geometry.py`
- Create: `tests/unit/test_domain_actions_control.py`
- Create: `tests/unit/test_domain_conditions_values.py`
- Create: `tests/unit/test_domain_traffic_environment.py`
- Modify: `tests/unit/test_loader.py`
- Modify: `tests/unit/test_schema_tool.py`
- Modify: `tests/unit/test_retrieve_spec_tool.py`
- Modify: `tests/unit/test_source_inventory.py`
- Modify: `tests/unit/test_validate_tool.py`
- Modify: `tests/unit/test_diagnostics_tool.py`
- Modify: `tests/unit/test_benchmark_assets.py`
- Modify/Create: `tests/fixtures/knowledge/*.json`
- Modify: `tests/integration/test_server_registration.py`
- Modify: `tests/integration/test_tool_loop.py`
- Modify: `tests/integration/test_benchmark_results.py`

## Task 1: Build The Coverage Contract

**Files:**
- Create: `tests/unit/test_xsd_inventory.py`
- Create: `tests/unit/test_schema_coverage_report.py`
- Create: `scripts/report_schema_coverage.py`

- [ ] **Step 1: Write the failing XSD inventory test**

```python
from openscenario_mcp.knowledge.xsd_inventory import load_xsd_inventory


def test_xsd_inventory_counts_distinct_element_names() -> None:
    inventory = load_xsd_inventory("knowledge/raw/schema/OpenSCENARIO.xsd")

    assert "OpenSCENARIO" in inventory.element_names
    assert "Storyboard" in inventory.element_names
    assert len(inventory.element_names) >= 300
```

- [ ] **Step 2: Write the failing coverage report test**

```python
from scripts.report_schema_coverage import build_schema_coverage_report


def test_schema_coverage_report_lists_missing_records() -> None:
    report = build_schema_coverage_report()

    assert report["xsd_element_count"] >= 300
    assert "OpenSCENARIO" in report["structured_elements"]
    assert "AbsoluteSpeed" in report["missing_elements"]
```

- [ ] **Step 3: Run the coverage tests to confirm they fail**

Run: `py -3.14 -m pytest tests/unit/test_xsd_inventory.py tests/unit/test_schema_coverage_report.py -v -p no:cacheprovider`

Expected: FAIL with missing module or missing function errors.

- [ ] **Step 4: Implement minimal XSD inventory and coverage report code**

Implementation requirements:

- `load_xsd_inventory()` must parse the local XSD and return:
  - `element_names`
  - `simple_type_names`
  - `complex_type_names`
  - `group_names`
- `build_schema_coverage_report()` must compare XSD names to `knowledge/structured/elements/*.json`
- the report must include:
  - `xsd_element_count`
  - `structured_element_count`
  - `structured_elements`
  - `missing_elements`
  - `extra_structured_elements`
  - `dangling_child_references`
  - `records_missing_required_metadata`

- [ ] **Step 5: Re-run the tests and confirm they pass**

Run: `py -3.14 -m pytest tests/unit/test_xsd_inventory.py tests/unit/test_schema_coverage_report.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 6: Commit the coverage contract**

Run: `git add tests/unit/test_xsd_inventory.py tests/unit/test_schema_coverage_report.py scripts/report_schema_coverage.py src/openscenario_mcp/knowledge/xsd_inventory.py`

Run: `git commit -m "test: add xsd inventory and coverage contract"`

## Task 2: Add Deterministic XSD Parsing And Stub Generation

**Files:**
- Create: `src/openscenario_mcp/knowledge/xsd_parser.py`
- Create: `scripts/generate_xsd_record_stubs.py`
- Create: `tests/unit/test_full_schema_scope.py`
- Modify: `tests/unit/test_loader.py`
- Modify: `knowledge/structured/mvp_scope.json`
- Create: `knowledge/structured/schema_scope.json`

- [ ] **Step 1: Write the failing parser test**

```python
from openscenario_mcp.knowledge.xsd_parser import parse_element_definition


def test_parse_variable_action_extracts_choice_and_attribute_metadata() -> None:
    record = parse_element_definition("VariableAction")

    assert record["element"] == "VariableAction"
    assert record["content_model_kind"] == "choice"
    assert record["required_attributes"][0]["name"] == "variableRef"
```

- [ ] **Step 2: Write the failing scope normalization test**

```python
import json
from pathlib import Path


def test_schema_scope_tracks_full_element_population() -> None:
    payload = json.loads(Path("knowledge/structured/schema_scope.json").read_text(encoding="utf-8"))

    assert payload["mode"] == "full"
    assert payload["xsd_element_count"] >= 300
```

- [ ] **Step 3: Write the failing loader-baseline test update**

Replace the current exact-match assumption between `mvp_scope.json` and every structured file with a full-coverage-aware contract:

```python
def test_schema_scope_matches_structured_element_files() -> None:
    schema_scope = json.loads(Path("knowledge/structured/schema_scope.json").read_text(encoding="utf-8"))
    file_elements = {
        load_element_record(path).element
        for path in Path("knowledge/structured/elements").glob("*.json")
    }

    assert file_elements == set(schema_scope["elements"])
```

- [ ] **Step 4: Run the parser, scope, and loader-baseline tests to verify failure**

Run: `py -3.14 -m pytest tests/unit/test_full_schema_scope.py tests/unit/test_loader.py -v -p no:cacheprovider`

Expected: FAIL because parser and scope file do not exist yet.

- [ ] **Step 5: Implement deterministic parsing helpers**

Implementation requirements:

- parse global element definitions and the complex types they reference
- resolve:
  - `required_attributes`
  - `optional_attributes`
  - `allowed_children`
  - `multiplicity`
  - `content_model_kind`
  - `child_groups`
  - enum restrictions
  - deprecation flags from `xsd:appinfo`
  - source line anchors
- preserve same output shape as `ElementRecord`, with current extended metadata fields

- [ ] **Step 6: Convert scope ownership from MVP-only to dual-scope**

Implementation requirements:

- keep `knowledge/structured/mvp_scope.json` as the benchmark-oriented subset for backward compatibility
- introduce `knowledge/structured/schema_scope.json` as the authoritative full structured corpus scope
- update `tests/unit/test_loader.py` to compare all on-disk structured records against `schema_scope.json`, not `mvp_scope.json`
- ensure the stub-generation baseline is green before any domain workers branch off

- [ ] **Step 7: Implement the stub generator**

The generator must:

- emit one JSON file per missing XSD element name
- populate structural facts deterministically from the XSD
- leave descriptions and semantic notes conservative rather than invented
- generate `knowledge/structured/schema_scope.json`
- generate `knowledge/structured/coverage_report.json`

- [ ] **Step 8: Run the generator**

Run: `py -3.14 scripts/generate_xsd_record_stubs.py`

Expected: new JSON files appear for every currently missing element, and `schema_scope.json` is regenerated to match the full file set.

- [ ] **Step 9: Re-run the scope and loader tests**

Run: `py -3.14 -m pytest tests/unit/test_full_schema_scope.py tests/unit/test_loader.py -v -p no:cacheprovider`

Expected: PASS. Do not proceed to parallel domain work from a failing baseline.

- [ ] **Step 10: Commit the parser and generated stubs**

Run: `git add src/openscenario_mcp/knowledge/xsd_parser.py scripts/generate_xsd_record_stubs.py knowledge/structured/schema_scope.json knowledge/structured/coverage_report.json knowledge/structured/elements`

Run: `git commit -m "feat: seed full xsd element records from schema"`

## Task 3: Partition The Full Schema Into Stable Parallel Domains

**Files:**
- Create: `knowledge/structured/manifests/domain-core-entities.txt`
- Create: `knowledge/structured/manifests/domain-routing-geometry.txt`
- Create: `knowledge/structured/manifests/domain-actions-control.txt`
- Create: `knowledge/structured/manifests/domain-conditions-values.txt`
- Create: `knowledge/structured/manifests/domain-traffic-environment.txt`
- Modify: `knowledge/structured/schema_scope.json`

- [ ] **Step 1: Write the failing manifest test**

```python
from pathlib import Path


def test_domain_manifests_partition_every_structured_element_once() -> None:
    manifests = sorted(Path("knowledge/structured/manifests").glob("domain-*.txt"))
    assert len(manifests) == 5
```

Expand the test so it also asserts:

- every structured element file appears in exactly one manifest
- no manifest contains duplicate entries
- the union of all manifest entries equals `knowledge/structured/elements/*.json`

- [ ] **Step 2: Create the domain manifests with exact file ownership**

Partition every element file into exactly one domain manifest.

Required ownership rules:

- same-name contextual variants stay in the same domain
- parent-child chains stay together when practical
- no element file appears in more than one manifest
- each manifest should be sized so one worker can finish it independently

- [ ] **Step 3: Update `schema_scope.json` with per-domain counts**

Include:

- `domains`
- `element_count`
- `missing_semantic_notes_count`
- `missing_contextual_variant_count`

- [ ] **Step 4: Re-run the manifest test**

Run: `py -3.14 -m pytest tests/unit/test_full_schema_scope.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit the manifests**

Run: `git add knowledge/structured/manifests knowledge/structured/schema_scope.json tests/unit/test_full_schema_scope.py`

Run: `git commit -m "chore: partition full schema into review domains"`

## Task 4: Enrich Core, Root, Entity, And Catalog Records

**Files:**
- Modify: all files listed in `knowledge/structured/manifests/domain-core-entities.txt`
- Modify: `knowledge/structured/coverage_report.json`
- Create: `tests/unit/test_domain_core_entities.py`

- [ ] **Step 1: Write domain-specific failing tests**

Add tests asserting representative core records carry:

- contextual variants where one element name maps to multiple types
- deprecation metadata where present
- `reference_kind` on `entityRef`, `parameterRef`, `catalogRef`, and similar link attributes

- [ ] **Step 2: Run the domain tests to verify failure**

Run: `py -3.14 -m pytest tests/unit/test_domain_core_entities.py -v -p no:cacheprovider`

Expected: FAIL on missing or incomplete enriched metadata for at least one representative record in this domain.

- [ ] **Step 3: Enrich all core/entity/catalog records in the manifest**

Manual enrichment requirements:

- descriptions must be schema-faithful and short
- `semantic_constraints` should only capture constraints that are clearly implied by XSD structure or explicit schema typing
- child references must stay closed

- [ ] **Step 4: Recompute coverage report**

Run: `py -3.14 scripts/report_schema_coverage.py`

Expected: report updates without missing files for this domain.

- [ ] **Step 5: Re-run the domain tests**

Run: `py -3.14 -m pytest tests/unit/test_domain_core_entities.py -v -p no:cacheprovider`

Expected: PASS for the new assertions.

- [ ] **Step 6: Commit the domain**

Run: `git add knowledge/structured/elements knowledge/structured/coverage_report.json tests/unit/test_domain_core_entities.py`

Run: `git commit -m "feat: enrich core and entity schema domain"`

## Task 5: Enrich Position, Routing, Geometry, And Trajectory Records

**Files:**
- Modify: all files listed in `knowledge/structured/manifests/domain-routing-geometry.txt`
- Modify: `knowledge/structured/coverage_report.json`
- Create: `tests/unit/test_domain_routing_geometry.py`

- [ ] **Step 1: Write representative failing tests**

Representative records must cover:

- `Position` and its variants
- route and trajectory wrappers
- geometric control-point structures
- repeated child cardinality edge cases

- [ ] **Step 2: Run the tests to verify failure**

Run: `py -3.14 -m pytest tests/unit/test_domain_routing_geometry.py -v -p no:cacheprovider`

Expected: FAIL on incomplete routing or geometry semantics.

- [ ] **Step 3: Enrich every file in the manifest**

Required metadata focus:

- `choice` groups for position variants
- `all` groups where child order is intentionally unconstrained
- source line anchors for geometry and spline elements

- [ ] **Step 4: Recompute coverage report and rerun tests**

Run: `py -3.14 scripts/report_schema_coverage.py`

Run: `py -3.14 -m pytest tests/unit/test_domain_routing_geometry.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit the domain**

Run: `git add knowledge/structured/elements knowledge/structured/coverage_report.json tests/unit/test_domain_routing_geometry.py`

Run: `git commit -m "feat: enrich routing and geometry schema domain"`

## Task 6: Enrich Action, Controller, Appearance, And Trailer Records

**Files:**
- Modify: all files listed in `knowledge/structured/manifests/domain-actions-control.txt`
- Modify: `knowledge/structured/coverage_report.json`
- Create: `tests/unit/test_domain_actions_control.py`

- [ ] **Step 1: Write representative failing tests**

Representative records must cover:

- shared element names with contextual variants
- deprecated parameter-side action branches
- controller and appearance actions
- trailer and coupling branches

- [ ] **Step 2: Run the tests to verify failure**

Run: `py -3.14 -m pytest tests/unit/test_domain_actions_control.py -v -p no:cacheprovider`

Expected: FAIL on missing contextual variants or incomplete action semantics.

- [ ] **Step 3: Enrich every file in the manifest**

Required metadata focus:

- `contextual_variants`
- deprecation flags
- `reference_kind` for controller/entity/trailer references

- [ ] **Step 4: Recompute coverage report and rerun tests**

Run: `py -3.14 scripts/report_schema_coverage.py`

Run: `py -3.14 -m pytest tests/unit/test_domain_actions_control.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit the domain**

Run: `git add knowledge/structured/elements knowledge/structured/coverage_report.json tests/unit/test_domain_actions_control.py`

Run: `git commit -m "feat: enrich actions and control schema domain"`

## Task 7: Enrich Conditions, Triggers, And Value Logic Records

**Files:**
- Modify: all files listed in `knowledge/structured/manifests/domain-conditions-values.txt`
- Modify: `knowledge/structured/coverage_report.json`
- Create: `tests/unit/test_domain_conditions_values.py`

- [ ] **Step 1: Write representative failing tests**

Representative records must cover:

- `ByEntityCondition` / `ByValueCondition`
- trigger wrappers
- value-constraint logic
- condition-rule enums and context-sensitive references

- [ ] **Step 2: Run the tests to verify failure**

Run: `py -3.14 -m pytest tests/unit/test_domain_conditions_values.py -v -p no:cacheprovider`

Expected: FAIL on missing or weak condition semantics.

- [ ] **Step 3: Enrich every file in the manifest**

Required metadata focus:

- closed condition child references
- rule enums and typed references
- exact-one-of condition branches

- [ ] **Step 4: Recompute coverage report and rerun tests**

Run: `py -3.14 scripts/report_schema_coverage.py`

Run: `py -3.14 -m pytest tests/unit/test_domain_conditions_values.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit the domain**

Run: `git add knowledge/structured/elements knowledge/structured/coverage_report.json tests/unit/test_domain_conditions_values.py`

Run: `git commit -m "feat: enrich conditions and triggers schema domain"`

## Task 8: Enrich Traffic, Environment, And Distribution Records

**Files:**
- Modify: all files listed in `knowledge/structured/manifests/domain-traffic-environment.txt`
- Modify: `knowledge/structured/coverage_report.json`
- Create: `tests/unit/test_domain_traffic_environment.py`

- [ ] **Step 1: Write representative failing tests**

Representative records must cover:

- environment branches
- traffic generation and sink/source/swarm branches
- parameter value distribution branches
- stochastic and deterministic distribution wrappers

- [ ] **Step 2: Run the tests to verify failure**

Run: `py -3.14 -m pytest tests/unit/test_domain_traffic_environment.py -v -p no:cacheprovider`

Expected: FAIL on missing environment or distribution metadata.

- [ ] **Step 3: Enrich every file in the manifest**

Required metadata focus:

- deeply nested distribution wrappers
- required repeated children
- deprecated enums from `appinfo`

- [ ] **Step 4: Recompute coverage report and rerun tests**

Run: `py -3.14 scripts/report_schema_coverage.py`

Run: `py -3.14 -m pytest tests/unit/test_domain_traffic_environment.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit the domain**

Run: `git add knowledge/structured/elements knowledge/structured/coverage_report.json tests/unit/test_domain_traffic_environment.py`

Run: `git commit -m "feat: enrich traffic and environment schema domain"`

## Task 9: Upgrade Runtime And Retrieval For Full Metadata

**Files:**
- Modify: `src/openscenario_mcp/knowledge/loader.py`
- Modify: `src/openscenario_mcp/runtime.py`
- Modify: `src/openscenario_mcp/knowledge/search.py`
- Modify: `src/openscenario_mcp/tools/retrieve_spec.py`
- Modify: `src/openscenario_mcp/tools/schema.py`
- Modify: `tests/unit/test_retrieve_spec_tool.py`
- Modify: `tests/unit/test_schema_tool.py`

- [ ] **Step 1: Write failing retrieval and schema-tool tests**

Add tests asserting:

- `get_element_schema` returns `content_model_kind`, `child_groups`, `semantic_constraints`, and `contextual_variants`
- `retrieve_spec` can surface:
  - contextual variant hints
  - deprecated warnings
  - typed references

- [ ] **Step 2: Run the tests to verify failure**

Run: `py -3.14 -m pytest tests/unit/test_schema_tool.py tests/unit/test_retrieve_spec_tool.py -v -p no:cacheprovider`

Expected: FAIL on missing surfaced metadata.

- [ ] **Step 3: Implement minimal runtime and retrieval changes**

Implementation requirements:

- stay backward-compatible with existing structured files
- keep `retrieve_spec` concise
- avoid inventing prose not grounded in XSD-backed records

- [ ] **Step 4: Re-run the tests**

Run: `py -3.14 -m pytest tests/unit/test_schema_tool.py tests/unit/test_retrieve_spec_tool.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit runtime and retrieval updates**

Run: `git add src/openscenario_mcp/knowledge/loader.py src/openscenario_mcp/runtime.py src/openscenario_mcp/knowledge/search.py src/openscenario_mcp/tools/retrieve_spec.py src/openscenario_mcp/tools/schema.py tests/unit`

Run: `git commit -m "feat: surface full schema metadata through runtime tools"`

## Task 10: Enforce Zero-Gap Coverage And Final Verification

**Files:**
- Modify: `knowledge/structured/coverage_report.json`
- Modify: `knowledge/structured/schema_scope.json`
- Modify: `tests/unit/test_loader.py`
- Modify: `tests/integration/test_server_registration.py`
- Modify: `README.md`
- Create: `docs/manual-acceptance/full-schema-coverage-checklist.md`

- [ ] **Step 1: Write the failing zero-gap test**

```python
from scripts.report_schema_coverage import build_schema_coverage_report


def test_no_xsd_elements_are_missing_from_structured_records() -> None:
    report = build_schema_coverage_report()

    assert report["missing_elements"] == []
    assert report["extra_structured_elements"] == []
    assert report["dangling_child_references"] == []
    assert report["records_missing_required_metadata"] == []
```

- [ ] **Step 2: Run the zero-gap test to verify failure or confirm remaining gaps**

Run: `py -3.14 -m pytest tests/unit/test_schema_coverage_report.py -v -p no:cacheprovider`

Expected: FAIL until every remaining missing record is resolved.

- [ ] **Step 3: Close any remaining gaps and regenerate reports**

Run: `py -3.14 scripts/generate_xsd_record_stubs.py`

Run: `py -3.14 scripts/report_schema_coverage.py`

Expected: `missing_elements` becomes `[]`.

- [ ] **Step 4: Run the full targeted verification suite**

Run: `py -3.14 -m pytest tests/unit/test_xsd_inventory.py tests/unit/test_schema_coverage_report.py tests/unit/test_full_schema_scope.py tests/unit/test_domain_core_entities.py tests/unit/test_domain_routing_geometry.py tests/unit/test_domain_actions_control.py tests/unit/test_domain_conditions_values.py tests/unit/test_domain_traffic_environment.py tests/unit/test_loader.py tests/unit/test_source_inventory.py tests/unit/test_schema_tool.py tests/unit/test_retrieve_spec_tool.py tests/unit/test_validate_tool.py tests/unit/test_diagnostics_tool.py tests/unit/test_benchmark_assets.py tests/integration/test_server_registration.py tests/integration/test_tool_loop.py tests/integration/test_benchmark_results.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Run MCP smoke verification**

Run: `py -3.14 -m openscenario_mcp`

Expected: process starts cleanly without record-loading failures.

- [ ] **Step 6: Update docs**

Document:

- the full-coverage definition
- how coverage is regenerated
- how to review domain manifests
- how to inspect `coverage_report.json`

- [ ] **Step 7: Commit final full-coverage state**

Run: `git add knowledge/structured src/openscenario_mcp tests README.md docs/manual-acceptance/full-schema-coverage-checklist.md scripts`

Run: `git commit -m "feat: complete full xsd schema coverage"`

## Execution Notes For The Controller

Before execution starts:

- create one global worktree per worker branch
- seed each worktree from the same verified baseline
- keep domain manifests immutable once workers start

During execution:

- do not allow two workers to edit the same manifest-owned JSON file
- do not allow two workers to edit the same test file; Tasks 4 through 8 own only their domain-specific test module, while shared test modules are reserved for Tasks 2, 9, and 10
- after each worker finishes, run spec review first, then code-quality review
- merge domain branches into an integration branch only after their targeted tests pass

Suggested merge order:

1. Task 1 and Task 2 infrastructure
2. Task 3 manifests
3. Tasks 4 through 8 domain branches in any order
4. Task 9 runtime/retrieval integration
5. Task 10 final verification and docs
