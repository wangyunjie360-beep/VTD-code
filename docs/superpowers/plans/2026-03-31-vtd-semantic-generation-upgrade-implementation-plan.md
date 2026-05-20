# VTD Semantic Generation Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the repository from a phase-1 VTD asset + schema helper stack into a phase-2 semantic generation support system with VTD semantic layers, OSC↔VTD bridge data, scenario-intent services, candidate recommendation, repair aggregation, and hard benchmark gates.

**Architecture:** Keep the existing OpenSCENARIO schema corpus and phase-1 VTD snapshot as immutable fact layers. Add derived semantic layers under `knowledge/structured/vtd/semantic/`, bridge layers under `knowledge/structured/bridges/osc_vtd/`, and scenario-level MCP services that expose intent normalization, schema subgraph retrieval, VTD candidate recommendation, repair aggregation, and XML-intent consistency checking. Defer the single-call `build_generation_packet` aggregation layer until the lower-level contracts are stable.

**Tech Stack:** Python 3.14, `dataclasses`, JSON/JSONL structured knowledge files, `pytest`, MCP server tool registration, repository-local benchmark assets, existing validator adapter, existing VTD snapshot builder, existing esmini-based runtime smoke path for non-VTD runtime checks

---

## Scope Guardrails

- This plan executes inside the current workspace on `master`; do not create worktrees for this phase because the user explicitly wants all visible changes in the current folder.
- Do not install or run VTD executables.
- Runtime-oriented validation in this plan means static checks plus the repository’s existing controllable runtime path such as esmini smoke coverage, not VTD playback.
- Keep `LLM-first, MCP-assisted` intact: MCP returns structure, candidates, constraints, and repair guidance; it does not become a rule-only XML generator.
- When this plan says `--runtime-root`, use the local verified default `D:\wyj\VTD-2020-install\VTD.2020\Runtime` when available; otherwise substitute the correct local `VTD.2020/Runtime` path explicitly instead of hard-failing the task.

## File Structure

### Existing files to modify

- `src/openscenario_mcp/models.py`
  - Add phase-2 semantic and bridge data contracts alongside the existing phase-1 contracts.
- `src/openscenario_mcp/runtime.py`
  - Load semantic VTD data, bridge data, and scenario-intent helpers in parallel with the existing schema and VTD bases.
- `src/openscenario_mcp/server.py`
  - Register the new phase-2 MCP tools in a stable contract order.
- `src/openscenario_mcp/knowledge/vtd_snapshot.py`
  - Materialize country taxonomy and reserved-name policies earlier during snapshot construction.
- `src/openscenario_mcp/knowledge/vtd_loader.py`
  - Load semantic derivatives and bridge records from structured JSONL/JSON outputs.
- `src/openscenario_mcp/knowledge/vtd_search.py`
  - Upgrade from flat lexical ranking to facet-aware ranking and policy-aware candidate search.
- `src/openscenario_mcp/knowledge/search.py`
  - Add schema subgraph and dependency-closure support on top of existing element search.
- `src/openscenario_mcp/tools/resolve_vtd_name.py`
  - Consume materialized name policies instead of relying only on live asset-name scans.
- `src/openscenario_mcp/tools/guidance.py`
  - Align the existing XML guidance contract with the new repair-aggregation and schema-subgraph outputs.
- `src/openscenario_mcp/generation/strategy.py`
  - Extend strategy helpers where needed for scenario-block planning, closure, and repair targeting.
- `scripts/build_vtd_knowledge_snapshot.py`
  - Emit semantic-layer and bridge-layer outputs in addition to the phase-1 fact outputs.
- `scripts/validate_benchmark_output.py`
  - Convert benchmark validation from a bookkeeping script into a failing quality gate.
- `benchmarks/intent-schema.json`
  - Tighten the sidecar contract to match the new executable scenario-intent IR.
- `benchmarks/guidance-inputs.json`
  - Expand benchmark guidance inputs to cover new benchmark families and guidance gold files.
- `skills/openscenario-xml-generator/SKILL.md`
  - Update the generation workflow to reference the phase-2 tool surface and intent closure loop.
- `README.md`
  - Document the phase-2 tool surface, semantic layers, and benchmark gate.
- `docs/usage-guide-zh.md`
  - Add Chinese operator guidance for phase-2 tool usage and benchmark expectations.
- `docs/work-order.md`
  - Track plan creation, active implementation batch, and verification status.
- `tests/integration/test_server_registration.py`
  - Expect the new MCP tools and semantic runtime wiring.
- `tests/integration/test_tool_loop.py`
  - Cover the phase-2 tool loop: intent -> schema subgraph -> VTD recommendation -> validate -> repair aggregation -> intent consistency.
- `tests/integration/test_benchmark_results.py`
  - Turn benchmark assets into a real regression gate.
- `tests/unit/test_vtd_loader.py`
  - Extend loader expectations for semantic outputs and bridge outputs.
- `tests/unit/test_vtd_search.py`
  - Cover the new ranking and facet-aware recommendation behavior.
- `tests/unit/test_resolve_vtd_name_tool.py`
  - Verify policy-materialized reserved-name and soft-namespace behavior.
- `tests/unit/test_benchmark_assets.py`
  - Tighten benchmark asset validation and invalid sample coverage.
- `tests/unit/test_diagnostics_tool.py`
  - Cover repair-batch aggregation categories and batch-scoped repair actions.

### New source files to create

- `src/openscenario_mcp/knowledge/vtd_semantic.py`
  - Build and normalize `VtdAssetFamily`, `VtdAssetVariant`, `VtdNamePolicy`, and provenance records from phase-1 assets and rules.
- `src/openscenario_mcp/knowledge/bridge_loader.py`
  - Load OSC↔VTD bridge records and policy recipes.
- `src/openscenario_mcp/knowledge/schema_graph.py`
  - Build schema subgraphs, reference closures, and assembly-order summaries.
- `src/openscenario_mcp/generation/intent.py`
  - Define scenario-intent normalization helpers and shared IR validation utilities.
- `src/openscenario_mcp/generation/intent_consistency.py`
  - Compare XML-derived facts back against scenario intent and checklist targets.
- `src/openscenario_mcp/generation/reference_closure.py`
  - Compute entity/parameter/variable/controller closure for scenario plans and repairs.
- `src/openscenario_mcp/tools/normalize_scenario_intent.py`
  - MCP tool for conservative prompt-to-intent normalization.
- `src/openscenario_mcp/tools/retrieve_schema_subgraph.py`
  - MCP tool for scenario-level schema closure retrieval.
- `src/openscenario_mcp/tools/recommend_vtd_candidates.py`
  - MCP tool for facet-aware VTD candidate recommendation.
- `src/openscenario_mcp/tools/summarize_validation_repairs.py`
  - MCP tool for root-cause grouping and minimal repair-batch planning.
- `src/openscenario_mcp/tools/check_xml_intent_consistency.py`
  - MCP tool for intent-vs-XML consistency checks.
- `src/openscenario_mcp/tools/build_generation_packet.py`
  - MCP aggregation tool that composes the lower-level phase-2 tools into a single scenario packet.

### New structured knowledge outputs

- `knowledge/structured/vtd/semantic/asset-families.jsonl`
- `knowledge/structured/vtd/semantic/asset-variants.jsonl`
- `knowledge/structured/vtd/semantic/name-policies.jsonl`
- `knowledge/structured/vtd/semantic/source-provenance.jsonl`
- `knowledge/structured/vtd/semantic/country-taxonomy.json`
- `knowledge/structured/bridges/osc_vtd/field-bindings.jsonl`
- `knowledge/structured/bridges/osc_vtd/generation-policies.jsonl`
- `knowledge/structured/bridges/osc_vtd/guidance-recipes.jsonl`

### New tests and fixtures

- `tests/unit/test_vtd_semantic_loader.py`
- `tests/unit/test_bridge_loader.py`
- `tests/unit/test_normalize_scenario_intent_tool.py`
- `tests/unit/test_schema_subgraph_tool.py`
- `tests/unit/test_recommend_vtd_candidates_tool.py`
- `tests/unit/test_summarize_validation_repairs_tool.py`
- `tests/unit/test_check_xml_intent_consistency_tool.py`
- `tests/unit/test_build_generation_packet_tool.py`
- `benchmarks/results/*.guidance.json`
  - Committed guidance gold files for each benchmark family.
- `benchmarks/invalid_xml/*.xml`
  - Expanded invalid XML fixtures per failure bucket.

## Task 1: Freeze Phase-2 Data Contracts And Output Locations

**Files:**
- Modify: `src/openscenario_mcp/models.py`
- Modify: `src/openscenario_mcp/runtime.py`
- Modify: `tests/unit/test_vtd_models.py`
- Create: `tests/unit/test_vtd_semantic_loader.py`
- Create: `tests/unit/test_bridge_loader.py`
- Create: `knowledge/structured/vtd/semantic/.gitkeep`
- Create: `knowledge/structured/bridges/osc_vtd/.gitkeep`

- [ ] **Step 1: Write the failing contract tests**

```python
from openscenario_mcp.models import (
    OscVtdBindingRule,
    VtdAssetFamily,
    VtdAssetVariant,
    VtdNamePolicy,
)


def test_vtd_asset_family_contract() -> None:
    family = VtdAssetFamily(
        family_id="signal-family:warning-101",
        canonical_key="warning-101",
        asset_kind="signal",
        preferred_variant_id="signal-variant:cn:warning-101",
        variant_ids=["signal-variant:cn:warning-101"],
        country_scopes=["CN"],
        semantic_tags=["warning_sign"],
        selection_policy="prefer_exact_country",
        notes=[],
    )
    assert family.asset_kind == "signal"
```

- [ ] **Step 2: Run the new contract tests**

Run: `py -3.14 -m pytest tests/unit/test_vtd_models.py tests/unit/test_vtd_semantic_loader.py tests/unit/test_bridge_loader.py -v -p no:cacheprovider`

Expected: FAIL because the new phase-2 contracts and output directories do not exist yet.

- [ ] **Step 3: Add the phase-2 contract dataclasses and runtime placeholders**

Implement:

- `VtdAssetFamily`
- `VtdAssetVariant`
- `VtdNamePolicy`
- `OscVtdBindingRule`
- runtime placeholders for semantic-layer and bridge-layer loaders
- tracked `.gitkeep` files for the new structured output directories

- [ ] **Step 4: Re-run the contract tests**

Run: `py -3.14 -m pytest tests/unit/test_vtd_models.py tests/unit/test_vtd_semantic_loader.py tests/unit/test_bridge_loader.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit the phase-2 contract baseline**

```bash
git add src/openscenario_mcp/models.py src/openscenario_mcp/runtime.py tests/unit/test_vtd_models.py tests/unit/test_vtd_semantic_loader.py tests/unit/test_bridge_loader.py knowledge/structured/vtd/semantic knowledge/structured/bridges/osc_vtd
git commit -m "feat: add phase2 semantic contracts"
```

## Task 2: Materialize Country Taxonomy And Reserved-Name Policies In The Snapshot

**Files:**
- Modify: `src/openscenario_mcp/knowledge/vtd_snapshot.py`
- Modify: `src/openscenario_mcp/knowledge/vtd_loader.py`
- Modify: `src/openscenario_mcp/knowledge/vtd_search.py`
- Modify: `src/openscenario_mcp/tools/resolve_vtd_name.py`
- Modify: `scripts/build_vtd_knowledge_snapshot.py`
- Modify: `knowledge/structured/vtd/summary.json`
- Create: `knowledge/structured/vtd/semantic/country-taxonomy.json`
- Create: `knowledge/structured/vtd/semantic/name-policies.jsonl`
- Modify: `tests/unit/test_vtd_snapshot.py`
- Modify: `tests/unit/test_vtd_loader.py`
- Modify: `tests/unit/test_vtd_search.py`
- Modify: `tests/unit/test_resolve_vtd_name_tool.py`

- [ ] **Step 1: Write the failing taxonomy and reserved-name tests**

```python
def test_build_name_policies_writes_reserved_name_policy_for_soft_namespace() -> None:
    policies = build_name_policies(sample_vtd_knowledge_base())
    assert any(policy.namespace == "scenario_object" for policy in policies)
```

- [ ] **Step 2: Run the focused failing tests**

Run: `py -3.14 -m pytest tests/unit/test_vtd_snapshot.py tests/unit/test_vtd_loader.py tests/unit/test_vtd_search.py tests/unit/test_resolve_vtd_name_tool.py -v -p no:cacheprovider`

Expected: FAIL because reserved-name materialization and extraction-stage taxonomy normalization are not implemented.

- [ ] **Step 3: Implement taxonomy-first normalization and reserved-name materialization**

Implement:

- a single source of truth for country aliases inside snapshot building
- reserved-name and soft-namespace policies emitted into `name-policies.jsonl`
- loader support for the new semantic policy file
- `resolve_vtd_name` consuming materialized policies before fallback scans

- [ ] **Step 4: Rebuild the local VTD snapshot and re-run the tests**

Run: `py -3.14 scripts/build_vtd_knowledge_snapshot.py --runtime-root "<VTD_RUNTIME_ROOT>"`

Expected: PASS with `reserved-names` no longer equal to zero in `knowledge/structured/vtd/summary.json`

Use the verified local default `D:\wyj\VTD-2020-install\VTD.2020\Runtime` when it exists; otherwise substitute the correct local `VTD.2020/Runtime` path.

Run: `py -3.14 -m pytest tests/unit/test_vtd_snapshot.py tests/unit/test_vtd_loader.py tests/unit/test_vtd_search.py tests/unit/test_resolve_vtd_name_tool.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit the taxonomy and name-policy layer**

```bash
git add src/openscenario_mcp/knowledge/vtd_snapshot.py src/openscenario_mcp/knowledge/vtd_loader.py src/openscenario_mcp/knowledge/vtd_search.py src/openscenario_mcp/tools/resolve_vtd_name.py scripts/build_vtd_knowledge_snapshot.py knowledge/structured/vtd/summary.json knowledge/structured/vtd/semantic/country-taxonomy.json knowledge/structured/vtd/semantic/name-policies.jsonl tests/unit/test_vtd_snapshot.py tests/unit/test_vtd_loader.py tests/unit/test_vtd_search.py tests/unit/test_resolve_vtd_name_tool.py
git commit -m "feat: materialize vtd taxonomy and name policies"
```

## Task 3: Build The VTD Semantic Derived Layer

**Files:**
- Create: `src/openscenario_mcp/knowledge/vtd_semantic.py`
- Modify: `src/openscenario_mcp/knowledge/vtd_loader.py`
- Modify: `scripts/build_vtd_knowledge_snapshot.py`
- Create: `knowledge/structured/vtd/semantic/asset-families.jsonl`
- Create: `knowledge/structured/vtd/semantic/asset-variants.jsonl`
- Create: `knowledge/structured/vtd/semantic/source-provenance.jsonl`
- Modify: `tests/unit/test_vtd_semantic_loader.py`
- Modify: `tests/unit/test_vtd_loader.py`

- [ ] **Step 1: Write the failing semantic-layer tests**

```python
def test_build_vtd_semantic_records_groups_variants_into_family() -> None:
    semantic = build_vtd_semantic_records(sample_vtd_knowledge_base())
    family = semantic.families_by_id["signal-family:sharedsignal01"]
    assert family.variant_ids
    assert family.preferred_variant_id in family.variant_ids
```

- [ ] **Step 2: Run the failing semantic-layer tests**

Run: `py -3.14 -m pytest tests/unit/test_vtd_semantic_loader.py tests/unit/test_vtd_loader.py -v -p no:cacheprovider`

Expected: FAIL because semantic-layer builders and loaders do not exist yet.

- [ ] **Step 3: Implement family, variant, and provenance derivation**

Implement:

- semantic grouping of phase-1 assets into family/variant/provenance records
- deterministic JSONL writers for the semantic outputs
- runtime loader support for the semantic directory

- [ ] **Step 4: Rebuild the snapshot and re-run the semantic tests**

Run: `py -3.14 scripts/build_vtd_knowledge_snapshot.py --runtime-root "<VTD_RUNTIME_ROOT>"`

Expected: PASS with the three new semantic output files written.

Use the verified local default `D:\wyj\VTD-2020-install\VTD.2020\Runtime` when it exists; otherwise substitute the correct local `VTD.2020/Runtime` path.

Run: `py -3.14 -m pytest tests/unit/test_vtd_semantic_loader.py tests/unit/test_vtd_loader.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit the semantic derived layer**

```bash
git add src/openscenario_mcp/knowledge/vtd_semantic.py src/openscenario_mcp/knowledge/vtd_loader.py scripts/build_vtd_knowledge_snapshot.py knowledge/structured/vtd/semantic/asset-families.jsonl knowledge/structured/vtd/semantic/asset-variants.jsonl knowledge/structured/vtd/semantic/source-provenance.jsonl tests/unit/test_vtd_semantic_loader.py tests/unit/test_vtd_loader.py
git commit -m "feat: derive vtd semantic asset families"
```

## Task 4: Add The First OSC ↔ VTD Bridge Layer

**Files:**
- Create: `src/openscenario_mcp/knowledge/bridge_loader.py`
- Modify: `src/openscenario_mcp/runtime.py`
- Create: `knowledge/structured/bridges/osc_vtd/field-bindings.jsonl`
- Create: `knowledge/structured/bridges/osc_vtd/generation-policies.jsonl`
- Create: `knowledge/structured/bridges/osc_vtd/guidance-recipes.jsonl`
- Modify: `tests/unit/test_bridge_loader.py`

- [ ] **Step 1: Write the failing bridge-layer tests**

```python
def test_load_bridge_bindings_covers_first_batch_fields() -> None:
    bridge = load_osc_vtd_bridge(REPO_ROOT / "knowledge" / "structured" / "bridges" / "osc_vtd")
    assert ("ScenarioObject", "name") in bridge.bindings_by_field
    assert ("Vehicle", "model3d") in bridge.bindings_by_field
```

- [ ] **Step 2: Run the failing bridge tests**

Run: `py -3.14 -m pytest tests/unit/test_bridge_loader.py -v -p no:cacheprovider`

Expected: FAIL because the bridge files and loader do not exist yet.

- [ ] **Step 3: Add the first-batch bridge inventory and loader**

Implement the first bridge batch explicitly for:

- `ScenarioObject.name`
- `Vehicle.model3d`
- `ExternalObjectReference.name`
- `TrafficSignalController.name`
- `TrafficSignalStateAction.name`
- `TrafficSignalAction.name`

Keep bridge semantics only in `knowledge/structured/bridges/osc_vtd/*.jsonl`; do not duplicate bridge truth into `knowledge/structured/elements/*.json`.

- [ ] **Step 4: Re-run the bridge tests**

Run: `py -3.14 -m pytest tests/unit/test_bridge_loader.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit the bridge layer**

```bash
git add src/openscenario_mcp/knowledge/bridge_loader.py src/openscenario_mcp/runtime.py knowledge/structured/bridges/osc_vtd/field-bindings.jsonl knowledge/structured/bridges/osc_vtd/generation-policies.jsonl knowledge/structured/bridges/osc_vtd/guidance-recipes.jsonl tests/unit/test_bridge_loader.py
git commit -m "feat: add first osc-vtd bridge bindings"
```

## Task 5: Add Executable Scenario Intent IR And Consistency Utilities

**Files:**
- Create: `src/openscenario_mcp/generation/intent.py`
- Create: `src/openscenario_mcp/generation/intent_consistency.py`
- Create: `src/openscenario_mcp/generation/reference_closure.py`
- Create: `src/openscenario_mcp/tools/normalize_scenario_intent.py`
- Create: `src/openscenario_mcp/tools/check_xml_intent_consistency.py`
- Modify: `src/openscenario_mcp/models.py`
- Modify: `src/openscenario_mcp/server.py`
- Modify: `benchmarks/intent-schema.json`
- Create: `tests/unit/test_normalize_scenario_intent_tool.py`
- Create: `tests/unit/test_check_xml_intent_consistency_tool.py`
- Modify: `tests/integration/test_benchmark_results.py`

- [ ] **Step 1: Write the failing intent and consistency tests**

```python
def test_normalize_scenario_intent_returns_partial_ir_with_unresolved_slots() -> None:
    result = normalize_scenario_intent("一辆主车在高速上触发变道")
    assert result["intent"]["entities"]
    assert "map_context" in result["intent"]
    assert isinstance(result["unresolved_slots"], list)
```

- [ ] **Step 2: Run the failing intent tests**

Run: `py -3.14 -m pytest tests/unit/test_normalize_scenario_intent_tool.py tests/unit/test_check_xml_intent_consistency_tool.py tests/integration/test_benchmark_results.py -v -p no:cacheprovider`

Expected: FAIL because the phase-2 scenario-intent utilities do not exist yet and the benchmark sidecar contract is still too weak.

- [ ] **Step 3: Implement conservative scenario-intent normalization and consistency checks**

Implement:

- a conservative prompt-to-intent normalizer that returns unresolved slots instead of inventing details
- explicit `xml_intent_check`
- reference-closure helpers for entities, parameters, variables, and controllers
- XML-to-intent consistency checks used by benchmark validation
- MCP registration for `normalize_scenario_intent` and `check_xml_intent_consistency`

- [ ] **Step 4: Re-run the intent tests**

Run: `py -3.14 -m pytest tests/unit/test_normalize_scenario_intent_tool.py tests/unit/test_check_xml_intent_consistency_tool.py tests/integration/test_benchmark_results.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit the intent IR layer**

```bash
git add src/openscenario_mcp/generation/intent.py src/openscenario_mcp/generation/intent_consistency.py src/openscenario_mcp/generation/reference_closure.py src/openscenario_mcp/tools/normalize_scenario_intent.py src/openscenario_mcp/tools/check_xml_intent_consistency.py src/openscenario_mcp/models.py src/openscenario_mcp/server.py benchmarks/intent-schema.json tests/unit/test_normalize_scenario_intent_tool.py tests/unit/test_check_xml_intent_consistency_tool.py tests/integration/test_benchmark_results.py
git commit -m "feat: add scenario intent ir utilities"
```

## Task 6: Add Schema Subgraph Retrieval And VTD Candidate Recommendation Tools

**Files:**
- Create: `src/openscenario_mcp/knowledge/schema_graph.py`
- Create: `src/openscenario_mcp/tools/retrieve_schema_subgraph.py`
- Create: `src/openscenario_mcp/tools/recommend_vtd_candidates.py`
- Modify: `src/openscenario_mcp/knowledge/search.py`
- Modify: `src/openscenario_mcp/knowledge/vtd_search.py`
- Modify: `src/openscenario_mcp/server.py`
- Create: `tests/unit/test_schema_subgraph_tool.py`
- Create: `tests/unit/test_recommend_vtd_candidates_tool.py`
- Modify: `tests/integration/test_server_registration.py`
- Modify: `tests/integration/test_tool_loop.py`

- [ ] **Step 1: Write the failing schema-subgraph and candidate tests**

```python
def test_retrieve_schema_subgraph_returns_required_paths_and_choice_points() -> None:
    result = retrieve_schema_subgraph(query="lane change", roots=["Storyboard"], depth=3)
    assert result["required_paths"]
    assert result["choice_points"]
```

- [ ] **Step 2: Run the failing tool tests**

Run: `py -3.14 -m pytest tests/unit/test_schema_subgraph_tool.py tests/unit/test_recommend_vtd_candidates_tool.py tests/integration/test_server_registration.py tests/integration/test_tool_loop.py -v -p no:cacheprovider`

Expected: FAIL because the new tools are not registered and the search layers do not provide the necessary graph and ranking outputs.

- [ ] **Step 3: Implement schema subgraph and facet-aware recommendation**

Implement:

- schema graph closure, required paths, reference bindings, and assembly order
- VTD candidate ranking that considers policy, asset kind, country scope, alias, and collision status
- MCP registration for the two new tools

- [ ] **Step 4: Re-run the new tool and integration tests**

Run: `py -3.14 -m pytest tests/unit/test_schema_subgraph_tool.py tests/unit/test_recommend_vtd_candidates_tool.py tests/integration/test_server_registration.py tests/integration/test_tool_loop.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit the schema-subgraph and recommendation tools**

```bash
git add src/openscenario_mcp/knowledge/schema_graph.py src/openscenario_mcp/tools/retrieve_schema_subgraph.py src/openscenario_mcp/tools/recommend_vtd_candidates.py src/openscenario_mcp/knowledge/search.py src/openscenario_mcp/knowledge/vtd_search.py src/openscenario_mcp/server.py tests/unit/test_schema_subgraph_tool.py tests/unit/test_recommend_vtd_candidates_tool.py tests/integration/test_server_registration.py tests/integration/test_tool_loop.py
git commit -m "feat: add schema subgraph and vtd recommendation tools"
```

## Task 7: Add Repair Aggregation And Stable XML Guidance Wiring

**Files:**
- Create: `src/openscenario_mcp/tools/summarize_validation_repairs.py`
- Modify: `src/openscenario_mcp/tools/guidance.py`
- Modify: `src/openscenario_mcp/validator/classifier.py`
- Modify: `src/openscenario_mcp/tools/diagnostics.py`
- Modify: `src/openscenario_mcp/server.py`
- Create: `tests/unit/test_summarize_validation_repairs_tool.py`
- Modify: `tests/unit/test_diagnostics_tool.py`
- Modify: `tests/unit/test_guidance_tool.py`

- [ ] **Step 1: Write the failing repair-aggregation tests**

```python
def test_summarize_validation_repairs_groups_cascaded_errors_under_one_root_cause() -> None:
    result = summarize_validation_repairs(
        errors=[
            {"message": "Element 'Storyboard': Missing child element 'Init'."},
            {"message": "Element 'StopTrigger': This element is not expected."},
        ]
    )
    assert result["root_causes"]
    assert result["repair_batches"][0]["minimal_patch_scope"]
```

- [ ] **Step 2: Run the failing repair tests**

Run: `py -3.14 -m pytest tests/unit/test_summarize_validation_repairs_tool.py tests/unit/test_diagnostics_tool.py tests/unit/test_guidance_tool.py -v -p no:cacheprovider`

Expected: FAIL because repair aggregation and minimal patch scoping are not implemented.

- [ ] **Step 3: Implement repair-batch aggregation and stable guidance registration**

Implement:

- repair-batch summaries with root-cause grouping and minimal patch scope
- `build_xml_guidance` consuming repair batches instead of only flat action labels
- stable MCP registration for `build_xml_guidance` once the contract is no longer optional

- [ ] **Step 4: Re-run the repair and guidance tests**

Run: `py -3.14 -m pytest tests/unit/test_summarize_validation_repairs_tool.py tests/unit/test_diagnostics_tool.py tests/unit/test_guidance_tool.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit the repair aggregation layer**

```bash
git add src/openscenario_mcp/tools/summarize_validation_repairs.py src/openscenario_mcp/tools/guidance.py src/openscenario_mcp/validator/classifier.py src/openscenario_mcp/tools/diagnostics.py src/openscenario_mcp/server.py tests/unit/test_summarize_validation_repairs_tool.py tests/unit/test_diagnostics_tool.py tests/unit/test_guidance_tool.py
git commit -m "feat: add repair aggregation guidance"
```

## Task 8: Add The Scenario-Level MCP Aggregation Packet

**Files:**
- Create: `src/openscenario_mcp/tools/build_generation_packet.py`
- Modify: `src/openscenario_mcp/server.py`
- Modify: `src/openscenario_mcp/generation/runner.py`
- Create: `tests/unit/test_build_generation_packet_tool.py`
- Modify: `tests/unit/test_guidance_runner.py`
- Modify: `tests/unit/test_benchmark_guidance_runner.py`

- [ ] **Step 1: Write the failing generation-packet tests**

```python
def test_build_generation_packet_composes_intent_schema_vtd_and_validation_plans() -> None:
    result = build_generation_packet(
        request="生成一个主车触发变道的 VTD 场景",
        country_code="CN",
        stage="draft",
    )
    assert result["intent"]
    assert result["schema_plan"]
    assert result["vtd_plan"]
    assert result["validation_plan"]
```

- [ ] **Step 2: Run the failing generation-packet tests**

Run: `py -3.14 -m pytest tests/unit/test_build_generation_packet_tool.py tests/unit/test_guidance_runner.py tests/unit/test_benchmark_guidance_runner.py -v -p no:cacheprovider`

Expected: FAIL because the aggregation tool does not exist and the runner scripts only build single-element guidance packets.

- [ ] **Step 3: Implement `build_generation_packet` as a thin aggregator**

Implement:

- allowed `stage` values `draft`, `repair`, `benchmark`
- composition over the lower-level phase-2 tools
- runner support for packet writing without replacing the lower-level tools
- in the first version, `build_generation_packet` must always return `intent`, `schema_plan`, `vtd_plan`, and `validation_plan`; `naming_plan` and `open_questions` may remain empty but the keys should still exist so the contract stays stable

- [ ] **Step 4: Re-run the generation-packet tests**

Run: `py -3.14 -m pytest tests/unit/test_build_generation_packet_tool.py tests/unit/test_guidance_runner.py tests/unit/test_benchmark_guidance_runner.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit the generation-packet tool**

```bash
git add src/openscenario_mcp/tools/build_generation_packet.py src/openscenario_mcp/server.py src/openscenario_mcp/generation/runner.py tests/unit/test_build_generation_packet_tool.py tests/unit/test_guidance_runner.py tests/unit/test_benchmark_guidance_runner.py
git commit -m "feat: add generation packet tool"
```

## Task 9: Turn Benchmark Validation Into A Hard Gate

**Files:**
- Modify: `scripts/validate_benchmark_output.py`
- Modify: `benchmarks/intent-schema.json`
- Modify: `benchmarks/guidance-inputs.json`
- Create: `benchmarks/results/minimal-single-vehicle.guidance.json`
- Create: `benchmarks/results/two-vehicle-follow.guidance.json`
- Create: `benchmarks/results/triggered-deceleration.guidance.json`
- Create: `benchmarks/results/triggered-lane-change.guidance.json`
- Modify: `benchmarks/invalid_xml/invalid-enum.xml`
- Modify: `tests/unit/test_benchmark_assets.py`
- Modify: `tests/unit/test_benchmark_guidance_runner.py`
- Modify: `tests/integration/test_benchmark_results.py`
- Modify: `tests/Test-EsminiRuntime.ps1`

- [ ] **Step 1: Write the failing hard-gate tests**

```python
def test_validate_benchmark_output_returns_nonzero_on_bounded_failure(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate_benchmark_output.py", "--results-dir", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
```

- [ ] **Step 2: Run the failing benchmark tests**

Run: `py -3.14 -m pytest tests/unit/test_benchmark_assets.py tests/unit/test_benchmark_guidance_runner.py tests/integration/test_benchmark_results.py -v -p no:cacheprovider`

Expected: FAIL because benchmark validation is still permissive and the guidance gold files are missing.

- [ ] **Step 3: Tighten the benchmark gate and add gold assets**

Implement:

- nonzero exit on benchmark failure
- strict JSON-schema-aligned sidecar validation
- committed guidance gold files
- explicit invalid-enum negative coverage
- esmini-based smoke gate for runtime-path regressions without invoking VTD

- [ ] **Step 4: Re-run the benchmark tests**

Run: `py -3.14 -m pytest tests/unit/test_benchmark_assets.py tests/unit/test_benchmark_guidance_runner.py tests/integration/test_benchmark_results.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit the hard benchmark gate**

```bash
git add scripts/validate_benchmark_output.py benchmarks/intent-schema.json benchmarks/guidance-inputs.json benchmarks/results/*.guidance.json benchmarks/invalid_xml/invalid-enum.xml tests/unit/test_benchmark_assets.py tests/unit/test_benchmark_guidance_runner.py tests/integration/test_benchmark_results.py tests/Test-EsminiRuntime.ps1
git commit -m "test: harden benchmark gate for phase2"
```

## Task 10: Update Operator Docs, Skill Guidance, And Work Order

**Files:**
- Modify: `skills/openscenario-xml-generator/SKILL.md`
- Modify: `README.md`
- Modify: `docs/usage-guide-zh.md`
- Modify: `docs/work-order.md`
- Modify: `tests/unit/test_benchmark_assets.py`

- [ ] **Step 1: Write the failing docs/skill regression test**

```python
def test_phase2_docs_reference_new_tool_loop() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    skill = Path("skills/openscenario-xml-generator/SKILL.md").read_text(encoding="utf-8")
    usage = Path("docs/usage-guide-zh.md").read_text(encoding="utf-8")
    assert "normalize_scenario_intent" in readme
    assert "recommend_vtd_candidates" in readme
    assert "check_xml_intent_consistency" in readme
    assert "normalize_scenario_intent" in skill
    assert "check_xml_intent_consistency" in usage
```

- [ ] **Step 2: Run the failing docs regression test**

Run: `py -3.14 -m pytest tests/unit/test_benchmark_assets.py -k "phase2 or benchmark" -v -p no:cacheprovider`

Expected: FAIL because the docs and skill do not yet reference the phase-2 tool loop and hard gate.

- [ ] **Step 3: Update the docs, skill, and work-order narrative**

Document:

- the phase-2 tool order
- the meaning of intent closure
- the benchmark hard gate
- the fact that runtime smoke coverage uses repository-controlled paths, not VTD execution

- [ ] **Step 4: Re-run the docs regression test**

Run: `py -3.14 -m pytest tests/unit/test_benchmark_assets.py -k "phase2 or benchmark" -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit the operator documentation refresh**

```bash
git add skills/openscenario-xml-generator/SKILL.md README.md docs/usage-guide-zh.md docs/work-order.md tests/unit/test_benchmark_assets.py
git commit -m "docs: document phase2 semantic workflow"
```

## Task 11: Final Full Verification

**Files:**
- Modify: `docs/work-order.md`

- [ ] **Step 1: Run the phase-2 focused verification suite**

Run: `py -3.14 -m pytest tests/unit/test_vtd_models.py tests/unit/test_vtd_snapshot.py tests/unit/test_vtd_loader.py tests/unit/test_vtd_search.py tests/unit/test_resolve_vtd_name_tool.py tests/unit/test_vtd_semantic_loader.py tests/unit/test_bridge_loader.py tests/unit/test_normalize_scenario_intent_tool.py tests/unit/test_check_xml_intent_consistency_tool.py tests/unit/test_schema_subgraph_tool.py tests/unit/test_recommend_vtd_candidates_tool.py tests/unit/test_summarize_validation_repairs_tool.py tests/unit/test_build_generation_packet_tool.py tests/unit/test_benchmark_assets.py tests/unit/test_benchmark_guidance_runner.py tests/unit/test_guidance_tool.py tests/unit/test_guidance_runner.py tests/unit/test_diagnostics_tool.py tests/integration/test_server_registration.py tests/integration/test_tool_loop.py tests/integration/test_benchmark_results.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 2: Rebuild the VTD snapshot and rerun the benchmark validator**

Run: `py -3.14 scripts/build_vtd_knowledge_snapshot.py --runtime-root "<VTD_RUNTIME_ROOT>"`

Expected: PASS with semantic outputs and updated summary written deterministically.

Use the verified local default `D:\wyj\VTD-2020-install\VTD.2020\Runtime` when it exists; otherwise substitute the correct local `VTD.2020/Runtime` path.

Run: `py -3.14 scripts/validate_benchmark_output.py --results-dir benchmarks/results`

Expected: PASS with exit code `0`

- [ ] **Step 3: Run the full repository test suite**

Run: `py -3.14 -m pytest -q -p no:cacheprovider`

Expected: PASS

- [ ] **Step 4: Record verification results in the work order**

Update `docs/work-order.md` with:

- the active completed phase-2 tasks
- snapshot regeneration result
- focused suite result
- benchmark gate result
- full-suite result

- [ ] **Step 5: Commit the verification update**

```bash
git add docs/work-order.md
git commit -m "docs: record phase2 verification results"
```
