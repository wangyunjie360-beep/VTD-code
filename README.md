# VTD-code

This repository contains an AI-primary VTD / OpenSCENARIO scenario-generation support system.

The intended workflow is:

```text
Natural-language scenario request
  -> AI model drafts and repairs the scenario
  -> local OpenSCENARIO MCP tools provide schema, VTD asset, naming, validation, and consistency evidence
  -> validated OpenSCENARIO XML plus traceable tool-interaction report
```

For full project handoff details, read `PROJECT_HANDOFF.md` first.

The repository also keeps the original `OpenDRIVE` + `OpenSCENARIO 1.1` esmini asset package used during development.

## Layout

```text
OPenscenario/
|- roads/
|  `- highway_edge_merge.xodr
|- scenarios/
|  |- highway_edge_merge_scripted.xosc
|  `- highway_edge_merge_controller_ready.xosc
|- tools/
|  `- esmini-v2.60.0/
`- tests/
   |- Test-OpenXAssets.ps1
   `- Test-EsminiRuntime.ps1
```

## Validation

```powershell
powershell -ExecutionPolicy Bypass -File tests\Test-OpenXAssets.ps1 -Target all
```

Runtime validation with the locally installed `esmini`:

```powershell
powershell -ExecutionPolicy Bypass -File tests\Test-EsminiRuntime.ps1 -EsminiPath 'D:\wyj\OPenscenario\tools\esmini-v2.60.0\esmini\bin\esmini.exe' -Target scripted
powershell -ExecutionPolicy Bypass -File tests\Test-EsminiRuntime.ps1 -EsminiPath 'D:\wyj\OPenscenario\tools\esmini-v2.60.0\esmini\bin\esmini.exe' -Target controller-ready
```

## Playback

`esmini` is installed locally at `D:\wyj\OPenscenario\tools\esmini-v2.60.0\esmini\bin\esmini.exe`. You can also add that directory to `PATH` later if you want a shorter command.

Scripted baseline:

```powershell
esmini --osc scenarios\highway_edge_merge_scripted.xosc --fixed_timestep 0.05
```

Controller-ready variant:

```powershell
esmini --osc scenarios\highway_edge_merge_controller_ready.xosc --fixed_timestep 0.05
```

## Python MCP Bootstrap

This repository now also includes a minimal Python package scaffold for `openscenario-mcp` under `src/openscenario_mcp`.

Package metadata and Python dependencies are declared in `pyproject.toml`:

- Python `>=3.12`
- `lxml`
- `mcp[cli]<2`
- `pytest`

Install the Python dependencies in your active environment, then run the package smoke test:

```powershell
python -m pip install -e .
python -m pytest tests/unit/test_package_import.py -v
```

## XML Validator

`openscenario_mcp.tools.validate.build_validate_xml_tool()` now wraps a module-backed validator adapter that defaults to `openscenario_mcp.validator.real_validator`.

The existing OpenX asset package under `roads/` and `scenarios/` targets OpenSCENARIO `1.1` for local `esmini` playback. Separately, the current MCP validator/generation stack introduced under `src/openscenario_mcp` is pinned to the local `ASAM OpenSCENARIO XML V1.4.0` schema at `knowledge/raw/schema/OpenSCENARIO.xsd` for this tooling work.

The real validator compiles that local OpenSCENARIO XML `1.4.0` schema with `lxml.etree.XMLSchema` and normalizes diagnostics into `{"line": ..., "column": ..., "message": ..., "rule_hint": ...}` entries under the tool response shape `{"ok": bool, "errors": [...]}`.

`knowledge/raw/validator/` is reserved for future custom validator wrappers or diagnostic enrichers if the project needs logic beyond direct schema validation.

## MCP Server

The MCP server composes its local runtime from:

- `knowledge/raw/docs/`
- `knowledge/raw/schema/`
- `knowledge/raw/validator/`
- `knowledge/structured/elements/*.json`
- `knowledge/diagnostics/patterns.json`

By default, `validate_xml` uses `openscenario_mcp.validator.real_validator`, which compiles the local XSD-backed schema at `knowledge/raw/schema/OpenSCENARIO.xsd`.

Run the server locally from the repository root:

```powershell
python -m openscenario_mcp
```

For Codex MCP registration, use the stable launcher at `scripts\start_mcp_server.cmd` and the exact config snippet documented in `docs/codex-mcp-setup.md`.

## Codex Skill Installation

Task 8 adds a project-local skill at `skills/openscenario-xml-generator/SKILL.md` plus the installer helper `scripts/install_codex_skill.py`.

Install it into Codex's discovered skill directory with:

```powershell
python scripts/install_codex_skill.py
```

Start a fresh Codex session after installation before running benchmarks so the new skill is discoverable.

## Real-Data Onboarding

Place user-supplied prose references in `knowledge/raw/docs/`. Keep the files in their original formats when possible so `source_path` values in structured records can point back to the exact raw source.

Place the schema files in `knowledge/raw/schema/`. The current runtime discovers the project root by locating `knowledge/raw/schema/OpenSCENARIO.xsd`, so keep that filename for the primary XML schema entry point.

Keep validator-specific helper assets in `knowledge/raw/validator/`. The runtime currently loads `openscenario_mcp.validator.real_validator`, so the project-specific validator integration point is `src/openscenario_mcp/validator/real_validator.py`. That module must expose:

```python
def validate(xml: str, schema_version: str) -> list[dict[str, object]]:
    ...
```

Each returned diagnostic should map cleanly into the normalized tool shape with `line`, `column`, `message`, and optional `rule_hint`.

## Structured Records

The first MVP scope is pinned in `knowledge/structured/mvp_scope.json`. When adding or correcting element records:

1. Copy the JSON shape used by existing files under `knowledge/structured/elements/`.
2. Fill `description`, `parent_contexts`, `required_attributes`, `optional_attributes`, `allowed_children`, `child_order`, `multiplicity`, `enum_constraints`, and `source_path`.
3. Prefer exact schema references in `source_path`, for example `knowledge/raw/schema/OpenSCENARIO.xsd#L2206`.
4. Keep records aligned with the element names listed in `mvp_scope.json` before expanding beyond the MVP.

The repository now also tracks the full structured schema corpus in `knowledge/structured/schema_scope.json`.

- `mvp_scope.json` remains the benchmark-oriented subset used by the early skill and loop tests.
- `schema_scope.json` is the authoritative full structured corpus scope for `knowledge/structured/elements/*.json`.
- `coverage_report.json` records the current zero-gap status:
  - `missing_elements`
  - `extra_structured_elements`
  - `dangling_child_references`
  - `records_missing_required_metadata`

Regenerate the full-coverage artifacts from the local XSD with:

```powershell
py -3.14 scripts/generate_xsd_record_stubs.py
py -3.14 scripts/report_schema_coverage.py
```

The five parallel review domains are tracked in:

- `knowledge/structured/manifests/domain-core-entities.txt`
- `knowledge/structured/manifests/domain-routing-geometry.txt`
- `knowledge/structured/manifests/domain-actions-control.txt`
- `knowledge/structured/manifests/domain-conditions-values.txt`
- `knowledge/structured/manifests/domain-traffic-environment.txt`

## Verification Commands

Use the local Python 3.14 launcher on this machine:

```powershell
py -3.14 -m pytest -v -p no:cacheprovider
py -3.14 scripts/validate_benchmark_output.py
```

The benchmark validator rewrites `benchmarks/results/run-log.md` with one `pass` or `bounded_failure` row per prompt.

## Launching The MCP Server

Run the server directly:

```powershell
py -3.14 -m openscenario_mcp
```

Or use the stable launcher that Codex registration points at:

```powershell
scripts\start_mcp_server.cmd
```

## Codex Registration

Register the MCP server in `C:\Users\EDY\.codex\config.toml`:

```toml
[mcp_servers.openscenario]
command = "D:\\wyj\\OPenscenario\\scripts\\start_mcp_server.cmd"
```

`docs/codex-mcp-setup.md` contains the same snippet plus the launcher details.

## Using The Skill In Codex

1. Install the skill with `python scripts/install_codex_skill.py`.
2. Start a fresh Codex session so the skill and MCP server are both discoverable.
3. Ask Codex to use `openscenario-xml-generator` for a VTD-oriented scenario request or benchmark prompt.
   Short phrasings such as `generate OpenX scene code`, `generate a VTD scene file`, or `generate a simulation scenario file` should be treated as the same workflow in this repository.
4. For repeatable checks, use the prompts under `benchmarks/prompts/` and compare the generated XML plus sidecar output to the committed examples in `benchmarks/results/`.

## Phase-2 Scenario Loop

The repository now exposes a phase-2 scenario-planning loop in addition to the original schema/VTD helpers.

Recommended order for a free-form VTD-oriented generation request:

1. `normalize_scenario_intent`
2. `build_generation_packet` or the lower-level `retrieve_schema_subgraph`
3. `recommend_vtd_candidates` for runtime-sensitive names and assets
4. `build_xml_guidance` / `retrieve_spec` / `get_element_schema`
5. `validate_xml`
6. `summarize_validation_repairs` when multiple validation errors appear together
7. `check_xml_intent_consistency`

This keeps the model in charge of scenario design while making the structure, naming, and repair surfaces more explicit.

## VTD Naming Loop

When the model is about to emit simulator-facing names or resources, keep the tool loop in this order:

1. Call `retrieve_vtd_asset` first to find real VTD candidates for the requested `asset_kind` and optional `country_code`.
2. Call `resolve_vtd_name` second before writing the name into XML.
   - If the result says `hard_constraint=True`, write `canonical_target` into XML and do not keep a soft-namespace `override_mapping`.
   - If the result says `hard_constraint=False` for a soft namespace such as `scenario_object`, `variable`, or `external_object`, write `safe_name` into XML and keep `override_mapping` only when you still need to preserve the user-facing label outside the XML.
3. Once the VTD asset and name are stable, call `build_xml_guidance` or the lower-level `retrieve_spec` plus `get_element_schema` tools for schema-specific structure help.
4. Run `validate_xml` on the full draft, then use `explain_validation_errors` for bounded repair if needed.

`build_vtd_guidance` remains available as a convenience wrapper when you want one compact VTD packet, but it does not replace the ordering above.

## Regenerating The VTD Snapshot

Rebuild the repository-local VTD snapshot from the confirmed local runtime with:

```powershell
py -3.14 scripts/build_vtd_knowledge_snapshot.py --runtime-root "D:\wyj\VTD-2020-install\VTD.2020\Runtime"
```

That command refreshes `knowledge/structured/vtd/` and should be run again whenever the underlying VTD runtime assets or naming rules change.

## Optional Guidance Packets

If you want an external agent or a fresh Codex session to get schema-aware help without reducing model decision freedom, build a `.guidance.json` packet first and let the model read it before drafting XML.

Benchmark helper:

```powershell
py -3.14 scripts/build_benchmark_guidance.py `
  --benchmark minimal-single-vehicle `
  --results-dir benchmarks/results
```

Generic helper:

```powershell
py -3.14 scripts/build_guidance_packet.py `
  --prompt-file benchmarks/prompts/minimal-single-vehicle.md `
  --query storyboard `
  --element Storyboard `
  --output benchmarks/results/minimal-single-vehicle.guidance.json
```

See `docs/external-agent-guidance-workflow.md` for the recommended LLM-first workflow.
See `docs/external-agent-prompt-template.md` for a ready-to-send external agent prompt.
See `docs/usage-guide-zh.md` for a full Chinese guide covering install, Codex setup, skill usage, and examples.

The committed benchmark guidance gold files now live directly under `benchmarks/results/*.guidance.json`.
