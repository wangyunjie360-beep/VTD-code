# OpenSCENARIO Work Order

Last updated: 2026-04-02

## Current Context

- Active branch: `master`
- Active workspace: `D:\wyj\OPenscenario`
- Current milestone: complete the phase-2 VTD semantic upgrade so OpenSCENARIO generation can use:
  - OpenSCENARIO schema knowledge
  - VTD static asset knowledge
  - VTD naming / collision guidance
  - VTD semantic derived knowledge
  - OSC ↔ VTD bridge rules
  - scenario intent and generation packet services
  - benchmark hard gates
- Priority rule in force:
  - `VTD static assets and runtime naming`
  - `VTD mapping / regional variant rules`
  - `OpenSCENARIO structured schema knowledge`
  - `model fallback reasoning`

## In Progress

- Update operator docs to fully reflect the completed phase-2 tool loop.
- Record the final phase-2 verification summary in this work order.
- Write the architecture spec for merging the OpenSCENARIO knowledge graph, MCP loop, skills, and benchmark assets into `claw-code` as a VTD-specialized runtime.
- Prepare the implementation handoff boundary:
  - planning and design stay in `D:\wyj\OPenscenario`
  - actual code implementation waits for a `claw-code` workspace that has a real `.git` repository

## Next Focus

- Convert the approved VTD-specialized `claw-code` design into a detailed implementation plan.
- Once a git-backed `claw-code` workspace is available, execute the migration in phases:
  - asset import and freeze
  - Rust knowledge runtime
  - domain tools and workflow kernel
  - runtime fusion
  - ego controller dual-mode delivery
  - benchmark and product hard gates

## Done

### Existing OpenSCENARIO baseline

- Preserved the full-schema OpenSCENARIO structured corpus and runtime tooling.
- Kept the schema-side element records under `knowledge/structured/elements/`.
- Kept the MCP-side schema / validation / diagnostics flow intact.

### VTD phase-1 knowledge contracts

- Added VTD-side data contracts in `src/openscenario_mcp/models.py`:
  - `VtdAssetRecord`
  - `VtdNameRule`
  - `VtdKnowledgeBase`
- Added `vtd-runtime` to `knowledge/source_inventory.json`.
- Added a compact VTD fixture tree under `tests/fixtures/vtd_runtime/`.

### VTD parser layer

- Added `src/openscenario_mcp/knowledge/vtd_parsers.py`.
- Implemented low-level literal parsers for:
  - `resourceDirs.txt`
  - `SIGDEF` / `EXTDEF` DAT rows
  - `pbr_objects.xml`
  - `decalScatter*.xml`
  - multi-root AddOn XML descriptors
- Hardened DAT parsing against mixed tab / multi-space column drift found in the real VTD tree.

### VTD snapshot normalization

- Added `src/openscenario_mcp/knowledge/vtd_snapshot.py`.
- Added deterministic phase-1 allowlist manifest:
  - `knowledge/structured/vtd/extractor_manifest.json`
- Built normalization for:
  - DAT + XML + directory scan merge
  - country-aware asset identity
  - external/model overlap suppression
  - rule-name uniqueness
  - runtime-root-relative `source_path` / `relative_path`
  - minimal country alias normalization (`USA -> US`, etc.)
- Kept `pbr_objects.xml` routing explicit; did not silently treat every `pbr_*.xml` sibling as object-mapping input.

### VTD snapshot writer / loader

- Added `src/openscenario_mcp/knowledge/vtd_loader.py`.
- Added `scripts/build_vtd_knowledge_snapshot.py`.
- Added loader coverage in `tests/unit/test_vtd_loader.py`.
- Generated the repository-local snapshot under `knowledge/structured/vtd/`.
- Tightened loader contracts so:
  - `assets_by_canonical_name` is non-lossy and list-valued
  - `runtime_root` is the real VTD Runtime root
  - release-tree assets stay under `Tools/RodDistro_6980_Rod4.6.1/...`
  - AddOn `source_path` keeps lexical provenance instead of collapsing through symlink targets

### Runtime + search integration

- Added `src/openscenario_mcp/knowledge/vtd_search.py`.
- Extended `src/openscenario_mcp/runtime.py` to load `vtd_knowledge_base`.
- Added runtime/search coverage in:
  - `tests/unit/test_vtd_search.py`
  - `tests/conftest.py`
- Preserved non-lossy canonical lookup behavior in runtime tests.
- Added explicit incomplete-snapshot and missing-bucket runtime error coverage.
- Added minimal country alias normalization in VTD search so filters like `CN` can still match snapshot values such as `China`.

### VTD MCP tools

- Added:
  - `src/openscenario_mcp/tools/retrieve_vtd_asset.py`
  - `src/openscenario_mcp/tools/resolve_vtd_name.py`
  - `src/openscenario_mcp/tools/vtd_guidance.py`
- Registered the three VTD tools through `src/openscenario_mcp/server.py`.
- Made `build_xml_guidance` registration optional so a clean tree does not depend on the untracked `guidance.py`.
- Aligned soft-namespace resolution with snapshot rule scope / severity instead of hardcoding stronger behavior.

### Phase-2 semantic upgrade

- Added phase-2 semantic and bridge contracts in `src/openscenario_mcp/models.py`:
  - `VtdAssetFamily`
  - `VtdAssetVariant`
  - `VtdNamePolicy`
  - `VtdSemanticKnowledgeBase`
  - `OscVtdBindingRule`
  - `OscVtdBridgeKnowledgeBase`
- Extended `src/openscenario_mcp/runtime.py` so runtime now exposes:
  - `vtd_semantic_knowledge_base`
  - `osc_vtd_bridge_knowledge_base`
- Materialized country taxonomy and name policy outputs under `knowledge/structured/vtd/semantic/`:
  - `country-taxonomy.json`
  - `name-policies.jsonl`
- Materialized semantic derived outputs under `knowledge/structured/vtd/semantic/`:
  - `asset-families.jsonl`
  - `asset-variants.jsonl`
  - `source-provenance.jsonl`
- Added the first OSC ↔ VTD bridge layer under `knowledge/structured/bridges/osc_vtd/`:
  - `field-bindings.jsonl`
  - `generation-policies.jsonl`
  - `guidance-recipes.jsonl`
- Added phase-2 scenario-level MCP tools:
  - `normalize_scenario_intent`
  - `check_xml_intent_consistency`
  - `build_generation_packet`
  - `retrieve_schema_subgraph`
  - `recommend_vtd_candidates`
  - `summarize_validation_repairs`
- Added `src/openscenario_mcp/knowledge/bridge_loader.py`
- Added `src/openscenario_mcp/knowledge/vtd_semantic.py`
- Added `src/openscenario_mcp/knowledge/schema_graph.py`
- Added phase-2 generation helpers:
  - `src/openscenario_mcp/generation/intent.py`
  - `src/openscenario_mcp/generation/intent_consistency.py`
  - `src/openscenario_mcp/generation/reference_closure.py`
- Tightened benchmark validation so `bounded_failure` now returns a nonzero exit code.
- Added committed benchmark guidance gold files:
  - `benchmarks/results/minimal-single-vehicle.guidance.json`
  - `benchmarks/results/two-vehicle-follow.guidance.json`
  - `benchmarks/results/triggered-deceleration.guidance.json`
  - `benchmarks/results/triggered-lane-change.guidance.json`

### Skill and workflow

- Updated `skills/openscenario-xml-generator/SKILL.md`.
- Updated `README.md`.
- Updated `docs/usage-guide-zh.md`.
- Added VTD-aware workflow regression in `tests/integration/test_tool_loop.py`.
- Explicitly documented the intended ordering:
  - `retrieve_vtd_asset`
  - `resolve_vtd_name`
  - schema/XML guidance
  - validation / repair

## Generated Snapshot State

Phase-1 source boundary is limited to the extractor allowlist under `knowledge/structured/vtd/extractor_manifest.json`:

- `Tools/resourceDirs.txt`
- `VisualLib/Models`
- `VisualLib/ModelsPBR`
- `VisualLib/Styles`
- `VisualLib/TileLib`
- `VisualLib/Models/**/SetupFiles/*.DAT`
- `Tools/pbr_*.xml`
- `DefaultProject/Config/*.xml`
- `DefaultProject/Config/Macros/*.rmcr`
- `Samples/*.tdo`
- `AddOns/**/*.xml`

Current `knowledge/structured/vtd/summary.json` reports:

- Asset counts
  - `signals = 4626`
  - `externals = 1200`
  - `decals = 78`
  - `models = 534`
  - `styles = 884`
  - `tiles = 159`
  - `addons = 5`
  - `macros = 14`
  - `samples = 9`
- Asset total
  - `7509`
- Rule counts
  - `aliases = 5767`
  - `country-preferences = 2484`
  - `reserved-names = 57787`
- Rule total
  - `66038`
- Semantic counts
  - `country-taxonomy = 11`
  - `name-policies = 55232`
- Runtime root
  - `D:/wyj/VTD-2020-install/VTD.2020/Runtime`
- Release root
  - `D:/wyj/VTD-2020-install/VTD.2020/Runtime/Tools/RodDistro_6980_Rod4.6.1`

## Verification

### Task 8 delivery rerun

- Rebuilt:
  - `py -3.14 scripts/build_vtd_knowledge_snapshot.py --runtime-root "D:\wyj\VTD-2020-install\VTD.2020\Runtime"`
- Result:
  - snapshot rewritten deterministically under `knowledge/structured/vtd/`
  - `asset_total = 7512`
  - `rule_total = 8254`
  - `runtime_root = D:/wyj/VTD-2020-install/VTD.2020/Runtime`
  - `release_name = RodDistro_6980_Rod4.6.1`

### Boundary subset

- Re-ran:
  - `py -3.14 -m pytest tests/unit/test_vtd_loader.py -k "boundary or invalid" -v -p no:cacheprovider`
- Result:
  - `5 passed, 5 deselected`

### Focused VTD suite

- Re-ran:
  - `py -3.14 -m pytest tests/unit/test_vtd_models.py tests/unit/test_vtd_parsers.py tests/unit/test_vtd_snapshot.py tests/unit/test_vtd_loader.py tests/unit/test_vtd_search.py tests/unit/test_retrieve_vtd_asset_tool.py tests/unit/test_resolve_vtd_name_tool.py tests/unit/test_vtd_guidance_tool.py tests/integration/test_server_registration.py tests/integration/test_tool_loop.py -v -p no:cacheprovider`
- Result:
  - `72 passed`

### Runtime search / tool subset

- Ran:
  - `py -3.14 -m pytest tests/unit/test_vtd_search.py tests/unit/test_vtd_loader.py tests/integration/test_server_registration.py -q -p no:cacheprovider`
- Result:
  - `22 passed`

### Tool registration subset

- Ran:
  - `py -3.14 -m pytest tests/unit/test_retrieve_vtd_asset_tool.py tests/unit/test_resolve_vtd_name_tool.py tests/unit/test_vtd_guidance_tool.py tests/integration/test_server_registration.py -q -p no:cacheprovider`
- Result:
  - `10 passed`

### Phase-2 focused suite

- Re-ran:
  - `py -3.14 -m pytest tests/unit/test_vtd_models.py tests/unit/test_vtd_snapshot.py tests/unit/test_vtd_loader.py tests/unit/test_vtd_search.py tests/unit/test_resolve_vtd_name_tool.py tests/unit/test_vtd_semantic_loader.py tests/unit/test_bridge_loader.py tests/unit/test_normalize_scenario_intent_tool.py tests/unit/test_check_xml_intent_consistency_tool.py tests/unit/test_schema_subgraph_tool.py tests/unit/test_recommend_vtd_candidates_tool.py tests/unit/test_summarize_validation_repairs_tool.py tests/unit/test_build_generation_packet_tool.py tests/unit/test_benchmark_assets.py tests/unit/test_benchmark_guidance_runner.py tests/unit/test_guidance_tool.py tests/unit/test_guidance_runner.py tests/unit/test_diagnostics_tool.py tests/integration/test_server_registration.py tests/integration/test_tool_loop.py tests/integration/test_benchmark_results.py -v -p no:cacheprovider`
- Result:
  - `118 passed`

### Benchmark hard gate

- Re-ran:
  - `py -3.14 scripts/validate_benchmark_output.py --results-dir benchmarks/results`
- Result:
  - exit code `0`
  - `run-log.md` updated from real validation output

### Full suite

- Re-ran:
  - `py -3.14 -m pytest -q -p no:cacheprovider`
- Result:
  - `211 passed in 9.61s`
- Remaining failures:
  - none

## Known Follow-ups

- Decide whether `TrafficSignalAction.name` should be represented as a synthetic bridge binding in a later bridge batch.
- Decide whether the phase-2 placeholder metadata (`status`, `exists`, `root`) should be upgraded into a typed contract instead of remaining a metadata convention.
- Decide whether benchmark sidecar validation should move from the current structural checker to a full JSON Schema evaluator.
- Resolve the legacy `ParameterDeclaration.json` / `test_variable_closure.py` mismatch outside the phase-2 scope if deeper benchmark semantics are required later.

## Deliberate Exclusions

- Did not install or run VTD executables.
- Did not ingest installer binaries (`.bin`, `.tar`, `.tgz`) into the knowledge graph.
- Did not change schema-side `knowledge/structured/elements/*.json` during VTD phase-1 work.
- Did not force untracked local `guidance.py` to become a required clean-tree dependency.

## Recent Commits

- `935f9aa` `feat: add repair aggregation guidance`
- `9871333` `feat: add schema subgraph and vtd recommendation tools`
- `7b86c45` `test: harden benchmark gate for phase2`
- `d535c2d` `feat: add generation packet tool`
- `6b308d5` `feat: add scenario intent ir utilities`
- `f0a1986` `feat: add first osc-vtd bridge bindings`
- `7c4102a` `feat: derive vtd semantic asset families`
- `c4e9b0b` `feat: consume vtd taxonomy and name policies`
- `fd0683a` `fix: align vtd snapshot buckets with summary`
- `2692b6a` `feat: build vtd taxonomy and policy snapshot`
- `46517aa` `fix: preserve runtime positional compatibility`
- `7db8dd9` `fix: stabilize phase2 placeholder runtime contracts`
- `7f8160e` `feat: add phase2 semantic contracts`
- `946d4c2` `feat: teach xml generator skill to consult vtd knowledge`
- `3e419df` `fix: align soft vtd name resolution with rule scope`
- `50223c9` `fix: make xml guidance server registration optional`
- `db3faf9` `feat: expose vtd asset tools through mcp`
- `0739af1` `fix: normalize vtd country alias filters`
- `3a60997` `fix: prefer exact country matches in vtd search`
- `e6b77dd` `test: cover missing vtd bucket error`
- `5d00f96` `test: tighten task5 runtime coverage`
- `bf07659` `feat: load vtd knowledge in runtime`
- `416bdff` `fix: tighten vtd snapshot loader contracts`
- `e74f63b` `feat: add vtd snapshot loader and builder`
- `e914361` `fix: normalize vtd country aliases`
- `eb44eaf` `fix: tighten vtd snapshot name matching`
- `72472f7` `fix: eliminate vtd snapshot overlaps and name collisions`
- `810e0d8` `fix: refine vtd snapshot asset matching`
- `b16cfc9` `fix: tighten vtd snapshot contracts`
- `34da91a` `fix: close vtd snapshot spec gaps`
- `c4fb850` `feat: normalize vtd assets and naming rules`
- `0d96f53` `fix: tolerate dat whitespace drift`
- `e75a13e` `fix: align vtd parsers with real source formats`
- `4df57e1` `fix: structure vtd name rule scope`
- `792d190` `fix: align vtd baseline contracts`
- `c97cfe2` `feat: add vtd knowledge contracts baseline`
