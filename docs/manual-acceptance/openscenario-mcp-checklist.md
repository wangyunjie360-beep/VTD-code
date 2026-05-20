# OpenSCENARIO MCP Manual Acceptance

- [ ] Raw docs copied into `knowledge/raw/docs/`
- [x] Schema copied into `knowledge/raw/schema/`
- [x] Real validator wired through `validate(xml, schema_version)`
- [x] `python -m pytest -v` passes
- [x] MCP server starts locally
- [x] One benchmark prompt is exercised through the skill manually
- [x] Full structured schema coverage is present under `knowledge/structured/elements/`
- [x] `knowledge/structured/coverage_report.json` reports zero missing elements or dangling child references

## Verification Notes

- `knowledge/raw/docs/` still contains only `.gitkeep`, so real prose docs still need to be copied in.
- `knowledge/raw/schema/OpenSCENARIO.xsd` is present and is the schema used by the current runtime.
- `src/openscenario_mcp/validator/real_validator.py` is the active validator entry point behind `validate_xml`.
- `py -3.14 -m pytest tests/unit/test_xsd_inventory.py tests/unit/test_schema_coverage_report.py tests/unit/test_full_schema_scope.py tests/unit/test_domain_core_entities.py tests/unit/test_domain_routing_geometry.py tests/unit/test_domain_actions_control.py tests/unit/test_domain_conditions_values.py tests/unit/test_domain_traffic_environment.py tests/unit/test_loader.py tests/unit/test_source_inventory.py tests/unit/test_schema_tool.py tests/unit/test_retrieve_spec_tool.py tests/unit/test_validate_tool.py tests/unit/test_diagnostics_tool.py tests/unit/test_benchmark_assets.py tests/integration/test_server_registration.py tests/integration/test_tool_loop.py tests/integration/test_benchmark_results.py -v -p no:cacheprovider` passed with 75 tests on this worktree.
- `py -3.14 -m openscenario_mcp` was started successfully and stayed alive until terminated after the smoke check.
- The current Codex session already has the registered `openscenario` MCP tools available, confirmed by live `retrieve_spec` calls.
- Benchmark prompts under `benchmarks/prompts/` were exercised manually through the skill-guided workflow, and the recorded outputs now live under `benchmarks/results/`.
- `knowledge/structured/schema_scope.json` tracks the full represented XSD set and the one Windows alias collision: `OpenScenario -> OpenSCENARIO`.
- `knowledge/structured/coverage_report.json` currently reports `missing_elements = []`, `extra_structured_elements = []`, `dangling_child_references = []`, and `records_missing_required_metadata = []`.
