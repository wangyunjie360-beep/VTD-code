# VTD Priority Knowledge Rework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a VTD-priority knowledge layer, naming-rule layer, and MCP tool surface so the XML-generation workflow can prefer real VTD assets, avoid runtime name collisions, and still preserve the existing OpenSCENARIO schema-validation path.

**Architecture:** Keep the existing `ElementRecord` / schema-knowledge path intact, add a parallel `VtdKnowledgeBase` loaded from structured VTD snapshot files, and expose VTD-specific retrieval and name-resolution tools from the MCP server. Build the VTD snapshot from static `VTD.2020` assets under the confirmed `RodDistro_6980_Rod4.6.1` layout, then update the skill to consult the VTD layer before emitting runtime-sensitive names.

**Tech Stack:** Python 3.14, `dataclasses`, JSON/JSONL knowledge snapshots, `pytest`, MCP server tool registration, static filesystem parsing of VTD assets, repository-local skill documentation

---

## File Structure

### Existing files to modify

- `src/openscenario_mcp/models.py`
  - Add VTD asset, naming-rule, and knowledge-base data contracts without disturbing the existing schema contracts.
- `src/openscenario_mcp/runtime.py`
  - Load both schema knowledge and VTD knowledge in parallel.
- `src/openscenario_mcp/server.py`
  - Register the new VTD MCP tools.
- `knowledge/source_inventory.json`
  - Add a tracked source entry for the VTD runtime snapshot source.
- `skills/openscenario-xml-generator/SKILL.md`
  - Teach the workflow to query VTD asset guidance before committing runtime-sensitive names.
- `README.md`
  - Document the new snapshot builder and VTD-aware tool flow.
- `docs/usage-guide-zh.md`
  - Add Chinese operator guidance for building and using the VTD snapshot.
- `docs/work-order.md`
  - Record completion counts, scope, and verification notes when implementation finishes.
- `tests/integration/test_server_registration.py`
  - Expect the new VTD tools.
- `tests/integration/test_tool_loop.py`
  - Cover a VTD-aware tool loop before schema validation.
- `tests/unit/test_source_inventory.py`
  - Extend the source-inventory contract to include the VTD runtime source.

### New source files to create

- `src/openscenario_mcp/knowledge/vtd_parsers.py`
  - Parse VTD definition files such as `resourceDirs.txt`, `SetupFiles/*.DAT`, `pbr_*.xml`, and `decalScatterConfig*.xml`.
- `src/openscenario_mcp/knowledge/vtd_snapshot.py`
  - Merge parsed definitions and scanned directory assets into normalized `VtdAssetRecord` and `VtdNameRule` collections.
- `src/openscenario_mcp/knowledge/vtd_loader.py`
  - Load JSONL/JSON snapshot files from `knowledge/structured/vtd/`.
- `src/openscenario_mcp/knowledge/vtd_search.py`
  - Search VTD assets and rules by canonical name, alias, namespace, and country scope.
- `src/openscenario_mcp/tools/retrieve_vtd_asset.py`
  - MCP tool for canonical VTD asset retrieval.
- `src/openscenario_mcp/tools/resolve_vtd_name.py`
  - MCP tool for conflict detection and canonical target resolution.
- `src/openscenario_mcp/tools/vtd_guidance.py`
  - Thin MCP wrapper that combines `retrieve_vtd_asset` and `resolve_vtd_name` into a compact guidance payload.
- `scripts/build_vtd_knowledge_snapshot.py`
  - Build the phase-1 repository-local VTD snapshot from the confirmed `VTD.2020` runtime tree.

### New structured knowledge outputs

- `knowledge/structured/vtd/assets/signals.jsonl`
- `knowledge/structured/vtd/assets/externals.jsonl`
- `knowledge/structured/vtd/assets/decals.jsonl`
- `knowledge/structured/vtd/assets/models.jsonl`
- `knowledge/structured/vtd/assets/styles.jsonl`
- `knowledge/structured/vtd/assets/tiles.jsonl`
- `knowledge/structured/vtd/assets/addons.jsonl`
- `knowledge/structured/vtd/assets/macros.jsonl`
- `knowledge/structured/vtd/assets/samples.jsonl`
- `knowledge/structured/vtd/rules/reserved-names.jsonl`
- `knowledge/structured/vtd/rules/aliases.jsonl`
- `knowledge/structured/vtd/rules/country-preferences.jsonl`
- `knowledge/structured/vtd/extractor_manifest.json`
- `knowledge/structured/vtd/summary.json`

### New tests and fixtures

- `tests/fixtures/vtd_runtime/`
  - Miniature static fixture tree with representative `DAT`, `XML`, `rmcr`, and model files.
- `tests/unit/test_vtd_models.py`
- `tests/unit/test_vtd_parsers.py`
- `tests/unit/test_vtd_snapshot.py`
- `tests/unit/test_vtd_loader.py`
- `tests/unit/test_vtd_search.py`
- `tests/unit/test_retrieve_vtd_asset_tool.py`
- `tests/unit/test_resolve_vtd_name_tool.py`
- `tests/unit/test_vtd_guidance_tool.py`

## Task 1: Define VTD Data Contracts And Fixture Inputs

**Files:**
- Modify: `src/openscenario_mcp/models.py`
- Modify: `knowledge/source_inventory.json`
- Modify: `tests/unit/test_source_inventory.py`
- Create: `knowledge/structured/vtd/assets/.gitkeep`
- Create: `knowledge/structured/vtd/rules/.gitkeep`
- Create: `tests/fixtures/vtd_runtime/README.md`
- Create: `tests/fixtures/vtd_runtime/Tools/resourceDirs.txt`
- Create: `tests/fixtures/vtd_runtime/Tools/pbr_objects.xml`
- Create: `tests/fixtures/vtd_runtime/DefaultProject/Config/decalScatterConfig01.xml`
- Create: `tests/fixtures/vtd_runtime/DefaultProject/Config/Macros/Town_500m.rmcr`
- Create: `tests/fixtures/vtd_runtime/Samples/sample01.tdo`
- Create: `tests/fixtures/vtd_runtime/VisualLib/Styles/VTL/Full/TexturePool/TxRoadStandard.rgb`
- Create: `tests/fixtures/vtd_runtime/VisualLib/TileLib/Standard/TileRoad01.attr`
- Create: `tests/fixtures/vtd_runtime/AddOns/OdrGateway/odrGateway.xml`
- Create: `tests/fixtures/vtd_runtime/VisualLib/Models/AddOns/CountryCN/SetupFiles/TT_EXTERNALS_ADD_COUNTRYCN.DAT`
- Create: `tests/fixtures/vtd_runtime/VisualLib/Models/AddOns/CountryCN/SetupFiles/TT_SIGNALS_ADD_COUNTRYCN.DAT`
- Create: `tests/unit/test_vtd_models.py`

- [ ] **Step 1: Write the failing model-contract and source-inventory tests**

```python
from openscenario_mcp.models import VtdAssetRecord, VtdKnowledgeBase, VtdNameRule


def test_vtd_asset_record_contract() -> None:
    record = VtdAssetRecord(
        asset_id="signal:CN_Sg101_Gefahrenstelle01",
        asset_kind="signal",
        canonical_name="CN_Sg101_Gefahrenstelle01",
        display_name="CN danger sign 101 small",
        aliases=["Sg101Gefahrstelle01.flt"],
        filename="CN_Sg101_Gefahrenstelle01.flt",
        relative_path="VisualLib/Models/AddOns/CountryCN/Signals/CN_Sg101_Gefahrenstelle01.flt",
        source_path="tests/fixtures/vtd_runtime/VisualLib/Models/AddOns/CountryCN/SetupFiles/TT_SIGNALS_ADD_COUNTRYCN.DAT#L1",
        country_codes=["CN"],
        variant_tags=[],
        group_path="CN-Signs-S",
        runtime_family="signal",
        metadata={"unit": "none"},
    )
    assert record.canonical_name == "CN_Sg101_Gefahrenstelle01"
```

- [ ] **Step 2: Run the failing tests**

Run: `py -3.14 -m pytest tests/unit/test_vtd_models.py tests/unit/test_source_inventory.py -v -p no:cacheprovider`

Expected: FAIL with missing `VtdAssetRecord` / `VtdNameRule` / `VtdKnowledgeBase` types and missing `vtd-runtime` inventory entry.

- [ ] **Step 3: Add the new dataclasses, source entry, and fixture tree**

Implement:

- `VtdAssetRecord`
- `VtdNameRule`
- `VtdKnowledgeBase`
- a `vtd-runtime` entry in `knowledge/source_inventory.json`
- empty structured VTD snapshot directories under `knowledge/structured/vtd/`
- a compact static fixture tree under `tests/fixtures/vtd_runtime/`

- [ ] **Step 4: Re-run the tests**

Run: `py -3.14 -m pytest tests/unit/test_vtd_models.py tests/unit/test_source_inventory.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit the contract and fixture baseline**

```bash
git add src/openscenario_mcp/models.py knowledge/source_inventory.json knowledge/structured/vtd tests/fixtures/vtd_runtime tests/unit/test_vtd_models.py tests/unit/test_source_inventory.py
git commit -m "feat: add vtd knowledge contracts baseline"
```

## Task 2: Implement Low-Level VTD Parser Helpers

**Files:**
- Create: `src/openscenario_mcp/knowledge/vtd_parsers.py`
- Create: `tests/unit/test_vtd_parsers.py`
- Modify: `tests/fixtures/vtd_runtime/Tools/resourceDirs.txt`
- Modify: `tests/fixtures/vtd_runtime/Tools/pbr_objects.xml`
- Modify: `tests/fixtures/vtd_runtime/DefaultProject/Config/decalScatterConfig01.xml`
- Modify: `tests/fixtures/vtd_runtime/AddOns/OdrGateway/odrGateway.xml`
- Modify: `tests/fixtures/vtd_runtime/VisualLib/Models/AddOns/CountryCN/SetupFiles/TT_EXTERNALS_ADD_COUNTRYCN.DAT`
- Modify: `tests/fixtures/vtd_runtime/VisualLib/Models/AddOns/CountryCN/SetupFiles/TT_SIGNALS_ADD_COUNTRYCN.DAT`

- [ ] **Step 1: Write the failing parser tests**

Cover:

- `parse_resource_dirs()`
- `parse_dat_definitions()`
- `parse_pbr_objects()`
- `parse_decal_scatter()`
- `parse_addon_xml_descriptor()`

Use fixture assertions like:

```python
def test_parse_signal_dat_extracts_canonical_name_and_group() -> None:
    entries = parse_dat_definitions(FIXTURE_SIGNAL_DAT, definition_kind="signal")
    assert entries[0]["canonical_name"] == "CN_Sg101_Gefahrenstelle01"
    assert entries[0]["group_path"] == "CN-Signs-S"
```

- [ ] **Step 2: Run the failing parser tests**

Run: `py -3.14 -m pytest tests/unit/test_vtd_parsers.py -v -p no:cacheprovider`

Expected: FAIL because the parser module does not exist yet.

- [ ] **Step 3: Implement parser helpers for the phase-1 source formats**

Implement functions that:

- keep original `source_path`
- preserve canonical names and aliases separately
- do conservative parsing only for the confirmed source formats
- avoid fuzzy inference beyond the spec-approved normalization rules
- extract minimal addon XML metadata such as root element, config kind, and source path without inventing deeper semantics

- [ ] **Step 4: Re-run the parser tests**

Run: `py -3.14 -m pytest tests/unit/test_vtd_parsers.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit the parser helpers**

```bash
git add src/openscenario_mcp/knowledge/vtd_parsers.py tests/unit/test_vtd_parsers.py tests/fixtures/vtd_runtime
git commit -m "feat: add phase1 vtd parser helpers"
```

## Task 3: Build Snapshot Normalization And Naming Rules

**Files:**
- Create: `src/openscenario_mcp/knowledge/vtd_snapshot.py`
- Create: `tests/unit/test_vtd_snapshot.py`
- Create: `knowledge/structured/vtd/extractor_manifest.json`

- [ ] **Step 1: Write the failing snapshot and naming-rule tests**

Cover:

- canonical asset merge from DAT + XML + directory scan
- namespace-aware collision detection
- severity classification `info | warning | high`
- country-specific preference rule generation
- extractor manifest allowlist shape
- bucket routing for `VisualLib/Styles`, `VisualLib/TileLib`, `AddOns` XML, `Macros/*.rmcr`, and `Samples/*.tdo`

```python
def test_build_name_rule_marks_exact_same_namespace_collision_as_high() -> None:
    rules = build_name_rules(
        assets=[...],
        candidate_names=[("CN_Sg101_Gefahrenstelle01", "runtime_asset", "signal", "CN")],
    )
    assert rules[0].severity == "high"
```

- [ ] **Step 2: Run the failing tests**

Run: `py -3.14 -m pytest tests/unit/test_vtd_snapshot.py -v -p no:cacheprovider`

Expected: FAIL because the snapshot builder module does not exist yet.

- [ ] **Step 3: Implement the snapshot builder and extractor manifest**

Implement logic that:

- scans the fixture/runtime tree for relevant files only
- merges parsed definitions into normalized `VtdAssetRecord` instances
- emits `VtdNameRule` records with explicit `namespace`, `asset_kind`, and `country_code` scope
- writes a deterministic `extractor_manifest.json` that acts as the phase-1 allowlist for:
  - `Tools/resourceDirs.txt`
  - `VisualLib/Models`
  - `VisualLib/ModelsPBR`
  - `VisualLib/Styles`
  - `VisualLib/TileLib`
  - `SetupFiles/*.DAT`
  - `Tools/pbr_*.xml`
  - `DefaultProject/Config/*.xml`
  - `DefaultProject/Config/Macros/*.rmcr`
  - `Samples/*.tdo`
  - `AddOns/**/*.xml`
- routes directory-scanned assets into explicit buckets:
  - styles -> `styles.jsonl`
  - tiles -> `tiles.jsonl`
  - addon XML descriptors -> `addons.jsonl`
  - macros -> `macros.jsonl`
  - samples -> `samples.jsonl`

- [ ] **Step 4: Re-run the snapshot tests**

Run: `py -3.14 -m pytest tests/unit/test_vtd_snapshot.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit the normalization layer**

```bash
git add src/openscenario_mcp/knowledge/vtd_snapshot.py knowledge/structured/vtd/extractor_manifest.json tests/unit/test_vtd_snapshot.py
git commit -m "feat: normalize vtd assets and naming rules"
```

## Task 4: Implement The Snapshot Writer And Loader

**Files:**
- Create: `src/openscenario_mcp/knowledge/vtd_loader.py`
- Create: `tests/unit/test_vtd_loader.py`
- Create: `scripts/build_vtd_knowledge_snapshot.py`
- Modify: `knowledge/structured/vtd/assets/signals.jsonl`
- Modify: `knowledge/structured/vtd/assets/externals.jsonl`
- Modify: `knowledge/structured/vtd/assets/decals.jsonl`
- Modify: `knowledge/structured/vtd/assets/models.jsonl`
- Modify: `knowledge/structured/vtd/assets/styles.jsonl`
- Modify: `knowledge/structured/vtd/assets/tiles.jsonl`
- Modify: `knowledge/structured/vtd/assets/addons.jsonl`
- Modify: `knowledge/structured/vtd/assets/macros.jsonl`
- Modify: `knowledge/structured/vtd/assets/samples.jsonl`
- Modify: `knowledge/structured/vtd/rules/reserved-names.jsonl`
- Modify: `knowledge/structured/vtd/rules/aliases.jsonl`
- Modify: `knowledge/structured/vtd/rules/country-preferences.jsonl`
- Create: `knowledge/structured/vtd/summary.json`

- [ ] **Step 1: Write the failing loader and snapshot-writer tests**

Cover:

- loading JSONL records from `knowledge/structured/vtd/`
- summary counts and source metadata
- deterministic ordering of emitted JSONL lines
- strict phase-1 boundary checks for:
  - expected `VTD.2020` runtime tree
  - expected `RodDistro_6980_Rod4.6.1` release
  - reject or fail fast on wrong layout / wrong release
  - reject manifest entries that point outside the phase-1 allowlist
  - ignore or reject in-tree files that are not part of the approved phase-1 source set

```python
def test_load_vtd_snapshot_reads_assets_and_rules(tmp_path: Path) -> None:
    snapshot = load_vtd_snapshot(tmp_path)
    assert "CN_Sg101_Gefahrenstelle01" in snapshot.assets_by_canonical_name
```

- [ ] **Step 2: Run the failing tests**

Run: `py -3.14 -m pytest tests/unit/test_vtd_loader.py -v -p no:cacheprovider`

Expected: FAIL because the loader and writer do not exist yet.

- [ ] **Step 3: Implement the loader and snapshot builder script**

Script contract:

```bash
py -3.14 scripts/build_vtd_knowledge_snapshot.py --runtime-root "D:\wyj\VTD-2020-install\VTD.2020\Runtime"
```

The script should:

- read only static assets from the confirmed phase-1 runtime tree
- write repository-local structured outputs under `knowledge/structured/vtd/`
- never copy raw VTD binaries or install anything
- fail fast if:
  - the runtime path is not a `VTD.2020` layout
  - the expected `RodDistro_6980_Rod4.6.1` tree is missing
  - the manifest allowlist points outside the approved phase-1 source set

- [ ] **Step 4: Generate the first repository-local snapshot from the real VTD runtime**

Run: `py -3.14 scripts/build_vtd_knowledge_snapshot.py --runtime-root "D:\wyj\VTD-2020-install\VTD.2020\Runtime"`

Expected: writes `knowledge/structured/vtd/assets/*.jsonl`, `knowledge/structured/vtd/rules/*.jsonl`, and `knowledge/structured/vtd/summary.json` with non-zero counts for at least signals, externals, models, styles, tiles, addons, macros, and samples.

- [ ] **Step 5: Run the boundary-failure tests**

Run: `py -3.14 -m pytest tests/unit/test_vtd_loader.py -k "boundary or invalid" -v -p no:cacheprovider`

Expected: PASS with explicit failures for:

- wrong release fixture cases
- wrong layout fixture cases
- manifest allowlist escape attempts
- in-tree but out-of-scope files

- [ ] **Step 6: Re-run the loader tests**

Run: `py -3.14 -m pytest tests/unit/test_vtd_loader.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 7: Commit the writer/loader and generated snapshot**

```bash
git add src/openscenario_mcp/knowledge/vtd_loader.py scripts/build_vtd_knowledge_snapshot.py knowledge/structured/vtd tests/unit/test_vtd_loader.py
git commit -m "feat: add vtd snapshot loader and builder"
```

## Task 5: Integrate VTD Knowledge Into Runtime And Search

**Files:**
- Modify: `src/openscenario_mcp/runtime.py`
- Create: `src/openscenario_mcp/knowledge/vtd_search.py`
- Create: `tests/unit/test_vtd_search.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Write the failing runtime and search tests**

Cover:

- runtime exposes both schema knowledge and VTD knowledge
- VTD search matches canonical name, alias, namespace, and country filter
- missing VTD snapshot produces a clear loader error

```python
def test_runtime_loads_vtd_knowledge_base(sample_project_root: Path) -> None:
    runtime = _build_runtime(project_root=sample_project_root)
    assert runtime.vtd_knowledge_base.assets_by_canonical_name
```

- [ ] **Step 2: Run the failing tests**

Run: `py -3.14 -m pytest tests/unit/test_vtd_search.py tests/integration/test_server_registration.py -v -p no:cacheprovider`

Expected: FAIL because `Runtime` does not carry `vtd_knowledge_base` yet.

- [ ] **Step 3: Add runtime loading and VTD search helpers**

Implement:

- `Runtime.vtd_knowledge_base`
- repository-local load path resolution for `knowledge/structured/vtd/`
- search helpers that score canonical-name hits above alias hits and keep namespace filtering explicit

- [ ] **Step 4: Re-run the tests**

Run: `py -3.14 -m pytest tests/unit/test_vtd_search.py tests/unit/test_vtd_loader.py tests/integration/test_server_registration.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit the runtime/search integration**

```bash
git add src/openscenario_mcp/runtime.py src/openscenario_mcp/knowledge/vtd_search.py tests/conftest.py tests/unit/test_vtd_search.py tests/integration/test_server_registration.py
git commit -m "feat: load vtd knowledge in runtime"
```

## Task 6: Add VTD MCP Tools And Register Them

**Files:**
- Create: `src/openscenario_mcp/tools/retrieve_vtd_asset.py`
- Create: `src/openscenario_mcp/tools/resolve_vtd_name.py`
- Create: `src/openscenario_mcp/tools/vtd_guidance.py`
- Modify: `src/openscenario_mcp/server.py`
- Create: `tests/unit/test_retrieve_vtd_asset_tool.py`
- Create: `tests/unit/test_resolve_vtd_name_tool.py`
- Create: `tests/unit/test_vtd_guidance_tool.py`
- Modify: `tests/integration/test_server_registration.py`

- [ ] **Step 1: Write the failing MCP tool tests**

Cover:

- `retrieve_vtd_asset` contract
- `resolve_vtd_name` contract
- `build_vtd_guidance` thin-wrapper behavior
- server registration for the three new tools
- namespace matrix behavior for:
  - `runtime_asset`
  - `scenario_object`
  - `variable`
  - `external_object`
- hard collision, soft exact collision, soft approximate collision, and explicit user override behavior

```python
def test_resolve_vtd_name_returns_high_for_exact_runtime_asset_collision() -> None:
    tool = build_resolve_vtd_name_tool(sample_vtd_knowledge_base())
    result = tool(
        name="CN_Sg101_Gefahrenstelle01",
        namespace="runtime_asset",
        asset_kind="signal",
        country_code="CN",
    )
    assert result["severity"] == "high"


def test_resolve_vtd_name_returns_safe_name_for_soft_namespace_exact_collision() -> None:
    tool = build_resolve_vtd_name_tool(sample_vtd_knowledge_base())
    result = tool(
        name="CN_Sg101_Gefahrenstelle01",
        namespace="scenario_object",
        asset_kind="vehicle",
        country_code="CN",
    )
    assert result["severity"] == "high"
    assert result["safe_name"] != "CN_Sg101_Gefahrenstelle01"
    assert result["hard_constraint"] is False


def test_resolve_vtd_name_preserves_override_mapping_for_soft_namespace() -> None:
    tool = build_resolve_vtd_name_tool(sample_vtd_knowledge_base())
    result = tool(
        name="CN_Sg101_Gefahrenstelle01",
        namespace="variable",
        asset_kind="logic",
        country_code="CN",
        user_override=True,
    )
    assert result["safe_name"]
    assert result["override_mapping"]["requested_name"] == "CN_Sg101_Gefahrenstelle01"


def test_resolve_vtd_name_ignores_override_for_hard_runtime_asset_constraint() -> None:
    tool = build_resolve_vtd_name_tool(sample_vtd_knowledge_base())
    result = tool(
        name="NonCanonicalSignalName",
        namespace="runtime_asset",
        asset_kind="signal",
        country_code="CN",
        user_override=True,
    )
    assert result["hard_constraint"] is True
    assert result["canonical_target"] == "CN_Sg101_Gefahrenstelle01"
    assert result["reason"]
    assert result["source_paths"]
    assert "override_mapping" not in result
```

- [ ] **Step 2: Run the failing tests**

Run: `py -3.14 -m pytest tests/unit/test_retrieve_vtd_asset_tool.py tests/unit/test_resolve_vtd_name_tool.py tests/unit/test_vtd_guidance_tool.py tests/integration/test_server_registration.py -v -p no:cacheprovider`

Expected: FAIL because the tool modules and server registration do not exist yet.

- [ ] **Step 3: Implement and register the VTD tools**

Implementation rules:

- `retrieve_vtd_asset` returns canonical assets and aliases only from the VTD snapshot
- `resolve_vtd_name` honors the phase-1 `namespace` / `asset_kind` / `country_code` contract
- `build_vtd_guidance` only composes the other two tools and does not invent new resolution logic
- `resolve_vtd_name` must return stable fields for soft-namespace auto-rename and explanation:
  - `hard_constraint`
  - `safe_name`
  - `override_mapping`
  - `reason`
  - `alternatives`
- when `namespace == "runtime_asset"` and `user_override=True`, the tool must still return:
  - `hard_constraint=True`
  - `canonical_target`
  - `reason`
  - `source_paths`
  - no soft-namespace `override_mapping`

- [ ] **Step 4: Re-run the MCP tool tests**

Run: `py -3.14 -m pytest tests/unit/test_retrieve_vtd_asset_tool.py tests/unit/test_resolve_vtd_name_tool.py tests/unit/test_vtd_guidance_tool.py tests/integration/test_server_registration.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit the VTD tool surface**

```bash
git add src/openscenario_mcp/tools/retrieve_vtd_asset.py src/openscenario_mcp/tools/resolve_vtd_name.py src/openscenario_mcp/tools/vtd_guidance.py src/openscenario_mcp/server.py tests/unit/test_retrieve_vtd_asset_tool.py tests/unit/test_resolve_vtd_name_tool.py tests/unit/test_vtd_guidance_tool.py tests/integration/test_server_registration.py
git commit -m "feat: expose vtd asset tools through mcp"
```

## Task 7: Update The Skill Workflow And Tool-Loop Regressions

**Files:**
- Modify: `skills/openscenario-xml-generator/SKILL.md`
- Modify: `README.md`
- Modify: `docs/usage-guide-zh.md`
- Modify: `tests/integration/test_tool_loop.py`

- [ ] **Step 1: Write the failing VTD-aware tool-loop regression**

Cover a workflow where the model:

1. asks for a VTD asset candidate
2. resolves a name collision
3. then proceeds to existing XML guidance / validation
4. retains an override mapping for soft namespaces but not for hard runtime-asset constraints

```python
def test_tool_loop_surfaces_vtd_name_resolution_before_schema_guidance(...) -> None:
    ...
```

- [ ] **Step 2: Run the failing regression**

Run: `py -3.14 -m pytest tests/integration/test_tool_loop.py -v -p no:cacheprovider`

Expected: FAIL because the current loop does not include the VTD-aware guidance sequence yet.

- [ ] **Step 3: Update the skill and operator docs**

Document:

- when to call `retrieve_vtd_asset`
- when to call `resolve_vtd_name`
- how hard vs soft VTD constraints should affect XML generation
- how to regenerate the VTD snapshot locally

- [ ] **Step 4: Re-run the tool-loop regression**

Run: `py -3.14 -m pytest tests/integration/test_tool_loop.py tests/integration/test_server_registration.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Commit the skill and workflow documentation**

```bash
git add skills/openscenario-xml-generator/SKILL.md README.md docs/usage-guide-zh.md tests/integration/test_tool_loop.py
git commit -m "feat: teach xml generator skill to consult vtd knowledge"
```

## Task 8: Full Verification And Delivery Snapshot

**Files:**
- Modify: `knowledge/structured/vtd/assets/signals.jsonl`
- Modify: `knowledge/structured/vtd/assets/externals.jsonl`
- Modify: `knowledge/structured/vtd/assets/decals.jsonl`
- Modify: `knowledge/structured/vtd/assets/models.jsonl`
- Modify: `knowledge/structured/vtd/assets/styles.jsonl`
- Modify: `knowledge/structured/vtd/assets/tiles.jsonl`
- Modify: `knowledge/structured/vtd/assets/addons.jsonl`
- Modify: `knowledge/structured/vtd/assets/macros.jsonl`
- Modify: `knowledge/structured/vtd/assets/samples.jsonl`
- Modify: `knowledge/structured/vtd/rules/*.jsonl`
- Modify: `knowledge/structured/vtd/summary.json`
- Modify: `docs/work-order.md`

- [ ] **Step 1: Rebuild the VTD snapshot from the confirmed runtime tree**

Run: `py -3.14 scripts/build_vtd_knowledge_snapshot.py --runtime-root "D:\wyj\VTD-2020-install\VTD.2020\Runtime"`

Expected: deterministic rewrite of the snapshot files and `summary.json`.

- [ ] **Step 2: Inspect the generated summary**

Run: `Get-Content knowledge\\structured\\vtd\\summary.json`

Expected:

- non-zero counts for `signals`, `externals`, and `models`
- non-zero counts for `styles`, `tiles`, `addons`, `macros`, and `samples`
- a recorded `runtime_root`
- a recorded `rod_release` of `RodDistro_6980_Rod4.6.1`

- [ ] **Step 3: Run the strict-boundary verification commands**

Run: `py -3.14 -m pytest tests/unit/test_vtd_loader.py -k "boundary or invalid" -v -p no:cacheprovider`

Expected: PASS with explicit validation that:

- unsupported layouts fail fast
- wrong releases fail fast
- allowlist escapes fail fast
- in-tree but out-of-scope files are ignored or rejected by contract

- [ ] **Step 4: Run the focused regression suite**

Run: `py -3.14 -m pytest tests/unit/test_vtd_models.py tests/unit/test_vtd_parsers.py tests/unit/test_vtd_snapshot.py tests/unit/test_vtd_loader.py tests/unit/test_vtd_search.py tests/unit/test_retrieve_vtd_asset_tool.py tests/unit/test_resolve_vtd_name_tool.py tests/unit/test_vtd_guidance_tool.py tests/integration/test_server_registration.py tests/integration/test_tool_loop.py -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 5: Run the full project suite**

Run: `py -3.14 -m pytest -v -p no:cacheprovider`

Expected: PASS

- [ ] **Step 6: Update the work order with delivered scope and verification counts**

Record:

- phase-1 source boundary
- generated asset/rule counts
- test pass counts
- any deliberate exclusions

- [ ] **Step 7: Commit the final VTD-priority rework**

```bash
git add knowledge/structured/vtd docs/work-order.md
git commit -m "feat: add vtd-priority knowledge layer"
```

## Notes For Implementers

- Do not install or run VTD. This project phase only reads static assets from the existing installation tree.
- Do not collapse VTD asset knowledge into `ElementRecord`; keep the schema layer and the VTD layer separate.
- Treat `severity` as the canonical enum `info | warning | high`. Use “high-risk” only in prose, not in serialized data.
- When implementing conflict handling for soft namespaces, preserve user intent in explanations even when auto-renaming to a safe internal name.
- Keep the phase-1 extractor strict. If a source file is not in the approved manifest, ignore it rather than guessing.
