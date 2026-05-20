# OpenSCENARIO MCP Design

## Goal

Create a reusable OpenSCENARIO generation system in which:

- Codex handles scene understanding, decomposition, and XML drafting
- an MCP server handles specification retrieval, XML validation, and error explanation
- the system can turn natural-language scenario requests into OpenSCENARIO 1.x XML that is structurally valid against the available schema and validator

The design assumes the current source materials are:

- OpenSCENARIO documentation covering concepts, structure, and syntax rules
- an XML schema or equivalent grammar specification
- a Python-accessible validator that can check XML and return failures

## Design Summary

The system is intentionally split into two responsibilities:

- `MCP capability layer`: exposes deterministic tools for retrieval and validation
- `Codex workflow layer`: performs reasoning, plans the scenario structure, drafts XML, and iterates until validation passes or the attempt budget is exhausted

This separation keeps the MCP server stable and low-risk while allowing the Codex-side generation workflow to evolve independently.

## Target Outcome

The first usable version should support this loop:

1. A user describes an OpenSCENARIO scene in natural language.
2. Codex converts the request into a structured scenario intent.
3. Codex queries the MCP server for the specific schema constraints it needs.
4. Codex drafts XML in conservative, spec-backed blocks.
5. Codex sends the XML to the validator through MCP.
6. If validation fails, Codex receives structured diagnostics, repairs the XML, and retries.
7. Codex returns validated XML or a bounded failure report with the remaining blockers.

## Architecture

### MCP Server Responsibilities

The MCP server should not generate XML and should not contain scene-planning logic.

Its responsibilities are:

- retrieve specification facts from the user's documentation set
- expose normalized schema structure for specific elements
- run XML validation through the existing Python validator
- translate raw validator output into repair-oriented diagnostics

### Codex Skill Responsibilities

The Codex-side OpenSCENARIO skill is responsible for:

- interpreting the user request
- building a structured intermediate representation of scenario intent
- deciding which schema facts are needed before writing each XML block
- producing the XML draft
- driving the validate-and-repair loop
- deciding when the XML is valid enough to return or when to stop with a failure report

### Knowledge Base Responsibilities

The knowledge base should sit behind the MCP server and convert raw materials into model-usable records.

It should contain:

- raw source documents for traceability
- structured per-element schema records
- diagnostic mappings from common validation failures to repair guidance

## MCP Tool Surface

The initial MCP server should expose four tools.

### `retrieve_spec`

Purpose:

- retrieve concise, source-linked specification summaries by concept, element, attribute, or error topic

Expected behavior:

- accept a query and a result type hint
- return a small set of high-signal matches
- include source paths so Codex can cite and re-query precisely

The response should prefer:

- element purpose
- required constraints
- allowed contexts
- critical notes

It should avoid returning long raw document excerpts unless the requested information cannot be summarized safely.

### `get_element_schema`

Purpose:

- return the structural contract for one specific XML element

Expected behavior:

- report required and optional attributes
- report allowed child elements
- report multiplicity rules
- report child ordering requirements
- report enum or value constraints when available

This tool exists so Codex does not have to infer structure from prose.

### `validate_xml`

Purpose:

- validate a supplied XML document against the available OpenSCENARIO schema and validator

Expected behavior:

- return `ok: true` when validation succeeds
- return normalized error records when validation fails

Each error record should include, when available:

- line
- column
- raw validator message
- a coarse error category if it can be derived immediately

The tool should preserve the original validator message for debugging and downstream interpretation.

### `explain_validation_errors`

Purpose:

- convert raw validator failures into repair-oriented diagnostics

Expected behavior:

- classify common failure types such as missing required children, illegal attributes, unexpected elements, ordering violations, and invalid enum values
- identify the relevant XML element and missing or invalid parts where possible
- return a short fix suggestion that Codex can act on directly

This tool is critical because raw XSD-style failures are often mechanically correct but not stable enough for iterative repair by a model.

## Knowledge Base Design

The knowledge base should be organized into three layers.

### Raw Source Layer

This layer stores the original inputs:

- specification documents
- schema files
- validator interface notes

It is the authority of record and should always be traceable from structured records.

### Structured Specification Layer

This layer should decompose the OpenSCENARIO material into per-element records.

Each record should include, when known:

- element name
- description
- valid parent contexts
- required attributes
- optional attributes
- allowed children
- child ordering
- multiplicity constraints
- enum or value restrictions
- source path or section reference

The first pass should prioritize high-frequency elements rather than attempting full standard coverage immediately.

### Diagnostic Knowledge Layer

This layer should map validation patterns to repair advice.

Representative categories include:

- `missing_required_child`
- `missing_required_attribute`
- `unexpected_element`
- `invalid_attribute`
- `wrong_child_order`
- `invalid_enum_value`
- `namespace_or_root_issue`

These mappings should be version-aware if the project later supports multiple OpenSCENARIO versions.

## Codex Workflow Design

The OpenSCENARIO skill should follow a fixed generation loop.

### Step 1: Parse User Intent

Codex converts the natural-language request into a structured intermediate representation before drafting XML.

The representation should capture at least:

- entities
- initial state
- environment or map assumptions
- event sequence
- triggers and conditions
- actions
- stop conditions
- parameters and unresolved assumptions

The intermediate representation does not need to be an external API. It only needs to be stable enough for the skill's internal reasoning.

### Step 2: Plan XML Blocks

Codex should draft the XML in bounded sections rather than producing the full document in one shot.

Recommended block boundaries:

- root and file metadata
- parameter declarations
- entities
- storyboard initialization
- story and act hierarchy
- maneuver and event structure
- triggers and conditions

This reduces repair scope when validation fails.

### Step 3: Query for Constraints

Before writing a block, Codex queries the MCP server for only the relevant schema rules.

Examples:

- before writing `ManeuverGroup`, query required children and order
- before writing conditions, query allowed trigger structure and value constraints

The workflow should prefer targeted lookups over broad retrieval.

### Step 4: Draft Conservative XML

The skill should bias toward the smallest spec-compliant structure that still expresses the intended scenario.

It should avoid:

- inventing tags
- inventing attributes not present in retrieved schema
- assuming enum values without confirmation
- omitting required scaffolding because the scene description did not mention it explicitly

### Step 5: Validate and Repair

After the draft is assembled, Codex calls `validate_xml`.

If validation fails, the workflow becomes:

1. call `explain_validation_errors`
2. decide whether more schema retrieval is needed
3. repair only the affected XML region
4. validate again

The repair loop should be bounded to a small retry budget such as three to five iterations.

### Step 6: Return Result or Bounded Failure

If validation passes, Codex returns the XML and a short note about any assumptions that were made.

If validation still fails after the retry budget:

- return the current XML draft
- return the outstanding diagnostics
- identify which blockers were due to schema uncertainty versus modeling ambiguity

## Quality Bar

The system should optimize for two separate success criteria:

- `schema-valid`: the XML passes the available validator
- `intent-consistent`: the XML still represents the scenario the user asked for

Validation alone is not sufficient. The workflow should preserve semantic intent while repairing structure.

## Testing Strategy

The system should include three test layers.

### MCP Tool Tests

Verify that each tool returns stable, machine-usable outputs for representative requests.

This includes:

- retrieval shape and source linking
- element schema completeness for covered elements
- validator result normalization
- diagnostic classification behavior

### Diagnostic Tests

Build a set of intentionally invalid XML samples and assert that diagnostics categorize them correctly and produce actionable fix hints.

### End-to-End Scenario Tests

Create a small benchmark set of natural-language scenarios and verify that the Codex workflow can produce validator-passing XML for them.

Because there is no existing example corpus, the initial benchmark set should be authored manually and kept small.

Recommended first benchmark scenarios:

- minimal single-vehicle scenario
- two-vehicle follow scenario
- trigger-based deceleration scenario
- trigger-based lane-change scenario
- scenario with initialization and a complete storyboard skeleton

## MVP Scope

The MVP should deliberately support only a narrow but useful slice of OpenSCENARIO.

Suggested MVP scope:

- one OpenSCENARIO 1.x target version
- one validator integration path
- coverage for the high-frequency structural elements needed for simple road scenarios
- one Codex skill that drives the retrieval and repair loop
- a compact benchmark suite for regression testing

The MVP should not attempt:

- full OpenSCENARIO surface-area coverage
- automatic semantic correction of poorly specified user intent
- simulator-specific runtime guarantees beyond schema validation
- multi-version abstraction until one version works reliably

## Deliverables

The design should lead to these concrete artifacts:

- an MCP server package exposing the four tools
- a structured knowledge base derived from the user's documents and schema
- a Codex skill for OpenSCENARIO generation and repair
- a small set of benchmark prompts and invalid XML fixtures
- automated tests for tool responses and validation diagnostics

## Risks and Constraints

The design depends on the quality of the source documentation and validator behavior.

Key risks:

- the validator may return messages too weak to classify without additional parsing rules
- documentation may describe concepts in prose without enough structural detail for deterministic extraction
- schema validity may still allow semantically poor scenarios
- a missing example corpus will slow prompt and workflow calibration

The design addresses these risks by:

- keeping generation logic outside MCP
- forcing targeted schema retrieval before drafting
- using a bounded repair loop
- starting with a high-frequency subset rather than full coverage

## Recommended Implementation Order

1. Normalize the user's documentation, schema, and validator entry points into a source inventory.
2. Build the structured specification records for the MVP element subset.
3. Implement `validate_xml` and `explain_validation_errors` first because they define the repair loop.
4. Implement `retrieve_spec` and `get_element_schema`.
5. Create the Codex OpenSCENARIO skill that uses the fixed intermediate-representation and repair workflow.
6. Build the benchmark scenarios and invalid XML fixtures.
7. Run end-to-end tests and tighten the schema subset until the loop is stable.

## Non-Goals

This design does not include:

- a tool that directly generates XML inside the MCP server
- a custom DSL compiler replacing OpenSCENARIO
- a promise that validator-passing XML will be simulator-perfect on the first version
- support for every OpenSCENARIO construct before the MVP loop is proven
