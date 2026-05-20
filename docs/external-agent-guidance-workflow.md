# External Agent Guidance Workflow

This workflow keeps XML authorship with the LLM and uses MCP plus local helper scripts only as schema-aware assistance.

## Goal

Use the benchmark prompts or your own prompt text to build a `.guidance.json` packet first, then let an external agent or new Codex session read that packet before drafting or repairing XML.

The packet is advisory. It does not replace model judgment and it does not generate XML by itself.

## Recommended Loop

1. Build a guidance packet from a benchmark prompt or custom prompt.
2. Open the resulting `.guidance.json` in the agent session that will write XML.
3. Let the model draft XML freely, using the packet only for:
   - risky element selection
   - shared-name variant resolution
   - `choice` and `sequence` structure
   - reference attributes
   - validator-driven repair ordering
4. Run `validate_xml`.
5. If validation fails, run `explain_validation_errors` and use `repair_strategy` as a repair hint, not a hard command.
6. Revalidate and stop when the XML is both schema-valid and still aligned with the original intent.

## Benchmark Helper

Build a benchmark guidance packet:

```powershell
py -3.14 scripts/build_benchmark_guidance.py `
  --benchmark minimal-single-vehicle `
  --results-dir benchmarks/results
```

This writes:

```text
benchmarks/results/minimal-single-vehicle.guidance.json
```

The benchmark helper uses:

- `benchmarks/guidance-inputs.json`
- `build_xml_guidance`
- the current structured knowledge base and validator patterns

It does not generate `*.xml` or `*.intent.json`.

## Generic Prompt Helper

Build a guidance packet for any prompt file:

```powershell
py -3.14 scripts/build_guidance_packet.py `
  --prompt-file benchmarks/prompts/minimal-single-vehicle.md `
  --query storyboard `
  --element Storyboard `
  --output benchmarks/results/minimal-single-vehicle.guidance.json
```

Use `--parent-context` when the target element name is shared across multiple parents.

## How To Use The Packet In An Agent Session

The agent should treat the packet in this order:

1. `prompt_text`
   This is still the primary source of intent.
2. `guidance.retrieval_hits`
   Use `strategy_summary` to narrow likely element and repair choices.
3. `guidance.element_schema`
   Use `strategy` only when structure is risky or ambiguous.
4. `guidance.repair_diagnostics`
   Use `repair_strategy` after validator feedback to keep repairs local.

## Suggested Agent Prompt

Use the ready-to-send templates in `docs/external-agent-prompt-template.md`.

## When To Skip The Packet

You may skip `.guidance.json` for very small edits when:

- the target element is already obvious
- there is no shared-name variant risk
- there is no validator feedback yet

You should prefer the packet when:

- the prompt is underspecified
- the element graph includes `choice` wrappers
- shared element names such as `SetAction` or `CatalogReference` are involved
- you are repairing schema failures
