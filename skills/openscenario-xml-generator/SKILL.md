---
name: openscenario-xml-generator
description: Use when generating or repairing OpenSCENARIO XML from natural-language scenario requests in this repository for VTD-oriented scenario development with the local MCP tools
---

# OpenSCENARIO XML Generator

## Overview
Let the model lead scenario design and XML drafting for VTD-oriented OpenSCENARIO scenario files, then use MCP as a schema-aware assistant for risky structure decisions, validation, and bounded repair. Do not rely on freehand XML alone when the schema, variants, or validator feedback become ambiguous.

## When to Use
- Converting a scenario request into OpenSCENARIO XML intended for VTD use
- Repairing generated XML after schema feedback before handing it to a VTD-facing workflow
- Producing benchmark runs that need traceable intent and validation evidence
- Treat short user phrasings such as `OpenX scene code`, `VTD scene file`, `simulation scenario file`, or similar wording as requests for the same VTD-oriented OpenSCENARIO XML workflow even when the user does not say `OpenSCENARIO XML` explicitly.

## Required Intermediate State
Keep these artifacts before treating a run as successful:
- `parsed_intent`: serialize the request into the shared `openscenario_mcp.models.ScenarioIntent` shape with `parameters`, `entities`, `environment`, `map_context`, `init_actions`, `story_actions`, `triggers`, `stop_conditions`, and `assumptions`.
- `xml_intent_check`: checklist that maps each requested behavior to the XML block or element that should encode it.
- `schema_valid`: set only from `validate_xml`.
- `intent_consistent`: set only after checking the repaired XML back against `parsed_intent` and `xml_intent_check`.
- `remaining_blockers`: unresolved gaps, unsupported requests, or exhausted retries.

## Workflow
1. Parse the user request into `parsed_intent` first. Prefer `normalize_scenario_intent` when available so the request is stabilized into a shared intermediate form before drafting any XML.
2. Build `xml_intent_check` from that parsed intent so every requested behavior has a planned XML home or an explicit assumption.
3. When you need a scenario-level planning packet, prefer `build_generation_packet` as a compact phase-2 aggregator over manually rebuilding the same intent/schema/VTD plan from scratch.
4. When the draft needs concrete simulator-facing assets or runtime-sensitive names, stabilize the VTD side before schema guidance:
   - Use `retrieve_vtd_asset` first to shortlist real VTD candidates for the asset kind and country you are about to reference.
   - Use `resolve_vtd_name` second before committing any runtime-facing or namespace-sensitive name into XML.
   - If `resolve_vtd_name` returns `hard_constraint=True`, treat `canonical_target` as mandatory in XML and do not carry a soft rename `override_mapping`.
   - If `resolve_vtd_name` returns `hard_constraint=False` for a soft namespace such as `scenario_object`, `variable`, or `external_object`, emit `safe_name` in XML and retain `override_mapping` when you still need to preserve the user's requested label outside the XML.
5. Only after the VTD asset choice and naming state are stable, use MCP whenever the next step is structurally risky or validator feedback is ambiguous:
   - Use `retrieve_schema_subgraph` when you need a scenario-level structure closure instead of a single-element lookup.
   - Use `recommend_vtd_candidates` when you want a combined candidate ranking plus name-resolution view for one runtime-sensitive field.
   - Use `build_xml_guidance` when you already know the candidate element and want one optional combined drafting or repair packet.
   - Use `retrieve_spec` for the behavior you are about to encode.
   - Read `strategy_summary` from `retrieve_spec` hits to shortlist branch, ordering, and repair expectations before pulling the full element record.
   - Use `get_element_schema` for the exact element you are about to emit.
   - When an element name is shared across multiple parents, call `get_element_schema` with `parent_context` set to the parent element you are currently filling.
   - Read and use the richer schema fields when they are present:
     - `content_model_kind`
     - `child_groups`
     - `contextual_variants`
     - `reference_kind`
     - `semantic_constraints`
     - `strategy`
   - Treat the returned `strategy` as the machine-readable drafting and repair plan for the current element:
     - `branch_selection` tells you how many choice branches may be emitted.
     - `variant_resolution` tells you whether the current parent context resolves a shared-name variant.
     - `reference_requirements` tells you which reference attributes should be wired first.
     - `repair_priority` tells you what to fix first after validation feedback.
   - If `contextual_variants` shows a `deprecated` branch, prefer a non-`deprecated` branch unless the request explicitly requires the legacy path.
6. Draft conservative XML. Prefer the smallest valid structure, avoid speculative catalogs or actors, and keep assumptions explicit.
   - Default to VTD-oriented, simulator-friendly OpenSCENARIO structures unless the prompt explicitly requires something else.
7. Run `validate_xml` on every full draft.
8. If validation fails, run `explain_validation_errors` on the returned `errors`.
   - Read `repair_strategy` when it is present.
   - Treat `repair_strategy.recommended_actions` as the priority order for the next repair pass.
   - Treat `repair_strategy.focus_strategy` as the parent element's structure-aware repair boundary.
   - When multiple validator errors appear together, prefer `summarize_validation_repairs` to group them into a minimal patch scope before editing.
9. Repair only the affected region. Do not rewrite unrelated valid blocks just because one subtree failed validation.
10. Re-run `validate_xml` after each repair. Stop after a bounded retry budget of 3 repair cycles.
11. After schema validation succeeds, compare the XML back to `parsed_intent` and `xml_intent_check`. Prefer `check_xml_intent_consistency` when available. Missing requested behavior, contradicted assumptions, or drift from the parsed intent means the run is still not successful.
12. If the retry budget is exhausted or blockers remain, stop and report a bounded failure instead of guessing.

## Conservative Drafting Rules
- Prefer minimal child sets and the narrowest schema-supported enums confirmed by MCP queries.
- Treat `content_model_kind` as authoritative:
  - `choice`: emit exactly one allowed branch from the relevant `child_groups`
  - `sequence`: preserve the declared `child_order`
  - `all`: do not invent order constraints that the schema does not require
- Treat `reference_kind` as authoritative when wiring `entityRef`, `parameterRef`, `variableRef`, `controllerRef`, and similar attributes.
- Inspect `contextual_variants` before emitting shared element names like `SetAction`, `ModifyAction`, or `CatalogReference`.
- Avoid `deprecated` variants when a non-`deprecated` variant is available for the same intent.
- Do not invent road data, trigger semantics, controller logic, or actor behavior that the request did not justify.
- Prefer VTD-friendly conservative XML over elaborate but weakly justified scenario structure.
- When the prompt is underspecified, record the assumption in `parsed_intent.assumptions` and keep the XML aligned with that assumption.

## Common Mistakes
- Writing XML before serializing `ScenarioIntent`
- Skipping `retrieve_vtd_asset` and `resolve_vtd_name` before locking runtime-facing asset names
- Skipping MCP lookups because the element seems familiar
- Running `validate_xml` without `explain_validation_errors` on failure
- Rewriting the whole document instead of repairing only the affected region
- Marking success after schema validity without checking intent consistency
- Interpreting `OpenX`, `VTD scene file`, or `simulation file` as a request for some non-OpenSCENARIO format when the surrounding task is scenario generation in this repository

## Quick Reference
- Parse first: `ScenarioIntent`
- Plan second: `xml_intent_check`
- Prefer phase-2 intent helpers when available: `normalize_scenario_intent`, `build_generation_packet`
- Stabilize VTD names first: `retrieve_vtd_asset` then `resolve_vtd_name`
- Use scenario-level structure help when needed: `retrieve_schema_subgraph`
- Use combined candidate ranking when needed: `recommend_vtd_candidates`
- Respect the VTD result fields: `hard_constraint`, `canonical_target`, `safe_name`, `override_mapping`
- Only after VTD naming is stable, query MCP for risky XML blocks: `build_xml_guidance`, `retrieve_spec`, and `get_element_schema`
- Use the optional local helper when helpful: `build_xml_guidance`
- Use returned metadata: `content_model_kind`, `child_groups`, `contextual_variants`, `reference_kind`
- Validate every draft: `validate_xml`
- Diagnose failures: `explain_validation_errors`
- Aggregate multi-error repairs when needed: `summarize_validation_repairs`
- Re-check the result against intent: `check_xml_intent_consistency`
- Use repair ordering when available: `repair_strategy`
- Repair scope: repair only the affected region
- Retry discipline: bounded retry budget of 3 repair cycles
