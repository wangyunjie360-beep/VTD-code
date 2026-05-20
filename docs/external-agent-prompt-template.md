# External Agent Prompt Template

Use this template when you want a fresh Codex session or another external agent to consume a `.guidance.json` packet while keeping final XML decisions with the model.

## Generic Template

```text
You are generating or repairing OpenSCENARIO XML.

Inputs:
- Prompt file: <prompt-file>
- Guidance packet: <guidance-json>

Working rules:
- The prompt text is the primary source of user intent.
- The guidance packet is schema-aware assistance, not a rigid plan.
- You own the XML design decisions.
- Prefer conservative XML and minimal valid structure.
- Do not add behavior that the prompt did not request.
- Use the guidance packet mainly for:
  - shared-name variant resolution
  - `choice` and `sequence` structure
  - required reference attributes
  - validator-driven repair ordering
- Keep repairs local after validator feedback.

Execution loop:
1. Read `prompt_text` and restate the intended scenario briefly.
2. Read `guidance.retrieval_hits` and `guidance.element_schema.strategy`.
3. Draft the XML yourself.
4. Run `validate_xml`.
5. If validation fails, run `explain_validation_errors`.
6. Use `repair_strategy` as a repair hint, not as a hard command.
7. Revalidate until the XML is schema-valid or you hit a bounded stop.

Required output:
- Final XML
- Short note explaining the main assumptions
- Short note explaining any remaining blockers
```

## Benchmark Template

Use this when you already generated:

- `benchmarks/results/<name>.guidance.json`

```text
Use the attached benchmark prompt and `.guidance.json` packet to draft OpenSCENARIO XML.

Constraints:
- Stay LLM-led: make the final XML decisions yourself.
- Use the packet only as schema-aware assistance.
- Keep the scenario minimal unless the prompt clearly requires more.
- Prefer the benchmark's intended target element and structure hints, but do not treat them as mandatory if the full prompt implies a better schema-valid path.
- After drafting, validate and repair locally.

Validation loop:
1. Draft XML.
2. Run `validate_xml`.
3. If validation fails, run `explain_validation_errors`.
4. Use `repair_strategy.recommended_actions` to prioritize the next local repair.
5. Stop when the XML is schema-valid and still matches the benchmark prompt intent.

Deliver:
- XML
- `parsed_intent`
- `xml_intent_check`
- A short explanation of any assumption made during drafting
```

## Minimal Session Recipe

1. Build a packet:

```powershell
py -3.14 scripts/build_benchmark_guidance.py `
  --benchmark minimal-single-vehicle `
  --results-dir benchmarks/results
```

2. Start the external agent with:

- `benchmarks/prompts/minimal-single-vehicle.md`
- `benchmarks/results/minimal-single-vehicle.guidance.json`
- the benchmark template above

## Notes

- If no `.guidance.json` exists yet, build one first with `scripts/build_guidance_packet.py` or `scripts/build_benchmark_guidance.py`.
- If the prompt is simple and the structure is obvious, you may skip the packet entirely.
- The packet is most useful when shared variants, `choice` wrappers, or validator repair loops are involved.
