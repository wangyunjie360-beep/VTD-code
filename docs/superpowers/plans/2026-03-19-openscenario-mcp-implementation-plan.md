# OpenSCENARIO MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python MCP server plus a project-local Codex skill that use the user's OpenSCENARIO docs, schema, and validator to support spec retrieval, XML validation, and repair-oriented diagnostics for XML generation.

**Architecture:** Keep deterministic capabilities inside a small Python package named `openscenario_mcp`. Back it with a staged knowledge base under `knowledge/` and expose four MCP tools: `retrieve_spec`, `get_element_schema`, `validate_xml`, and `explain_validation_errors`. Add a project-local skill under `.superpowers/skills/` that tells Codex how to use those tools in a fixed parse-draft-validate-repair loop.

**Tech Stack:** Python 3.12+ virtual environment, `pytest`, the Python MCP SDK (`mcp[cli]` pinned to `v1.x`), JSON knowledge records, markdown source notes, project-local superpowers skill files

---

## Planned File Structure

### Project bootstrap

- `pyproject.toml`: project metadata, dependencies, pytest config, console entry point
- `.gitignore`: Python, virtualenv, cache, and generated artifact ignores
- `README.md`: setup, local data placement, test, and MCP launch instructions

### Package code

- `src/openscenario_mcp/__init__.py`: package version export
- `src/openscenario_mcp/__main__.py`: `python -m openscenario_mcp` launcher
- `src/openscenario_mcp/config.py`: paths and runtime configuration
- `src/openscenario_mcp/runtime.py`: server-local composition of knowledge, diagnostics, and validator state
- `src/openscenario_mcp/server.py`: MCP server assembly and tool registration
- `src/openscenario_mcp/models.py`: shared dataclasses or typed models for sources, schema records, knowledge base, validator errors, diagnostics, and machine-readable scenario intent

### Knowledge handling

- `src/openscenario_mcp/knowledge/source_inventory.py`: raw source manifest loading and validation
- `src/openscenario_mcp/knowledge/loader.py`: structured record loading from `knowledge/structured/`
- `src/openscenario_mcp/knowledge/search.py`: keyword-based retrieval for `retrieve_spec`
- `knowledge/raw/docs/`: user-supplied OpenSCENARIO prose sources
- `knowledge/raw/schema/`: user-supplied XSD or equivalent schema files
- `knowledge/raw/validator/`: user-supplied validator notes or wrapper inputs
- `knowledge/source_inventory.json`: manifest of raw source locations and metadata
- `knowledge/structured/mvp_scope.json`: pinned OpenSCENARIO target version plus the exact initial MVP element list
- `knowledge/structured/elements/*.json`: structured per-element schema records
- `knowledge/diagnostics/patterns.json`: validation error pattern to diagnostic mapping

### Tool and validator code

- `src/openscenario_mcp/tools/retrieve_spec.py`: `retrieve_spec` implementation
- `src/openscenario_mcp/tools/schema.py`: `get_element_schema` implementation
- `src/openscenario_mcp/tools/validate.py`: `validate_xml` implementation
- `src/openscenario_mcp/tools/diagnostics.py`: `explain_validation_errors` implementation
- `src/openscenario_mcp/validator/adapter.py`: adapter around the real Python validator
- `src/openscenario_mcp/validator/classifier.py`: raw validation error classification helpers
- `src/openscenario_mcp/validator/real_validator.py`: project-local wrapper that adapts the user's validator assets into an importable `validate(xml, schema_version)` function

### Skill and benchmark assets

- `skills/openscenario-xml-generator/SKILL.md`: version-controlled source for the Codex generation skill
- `scripts/install_codex_skill.py`: copies the version-controlled skill into `C:\Users\EDY\.codex\skills\openscenario-xml-generator\`
- `benchmarks/prompts/*.md`: benchmark natural-language scenario prompts
- `benchmarks/intent-schema.json`: shared machine-readable contract for parsed intent and benchmark result sidecars
- `benchmarks/invalid_xml/*.xml`: intentionally invalid XML fixtures for diagnostics tests
- `benchmarks/results/*.xml`: XML outputs captured from manual skill benchmark runs
- `benchmarks/results/*.intent.json`: per-prompt machine-readable intent and benchmark-evaluation sidecars
- `benchmarks/results/*.md`: optional human-readable benchmark notes
- `benchmarks/results/run-log.md`: per-prompt benchmark outcome log
- `scripts/validate_benchmark_output.py`: validates saved benchmark outputs against the real or fake validator
- `scripts/start_mcp_server.cmd`: stable local launch entry point for Codex MCP registration
- `docs/codex-mcp-setup.md`: exact Codex MCP registration steps for this project

### Tests

- `tests/unit/test_package_import.py`: package bootstrap smoke test
- `tests/conftest.py`: shared fixtures for sample knowledge bases, fake validator modules, and structured record factories
- `tests/unit/test_source_inventory.py`: manifest validation tests
- `tests/unit/test_loader.py`: structured record loading tests
- `tests/unit/test_validate_tool.py`: validator normalization tests
- `tests/unit/test_diagnostics_tool.py`: diagnostic mapping tests
- `tests/unit/test_schema_tool.py`: `get_element_schema` tests
- `tests/unit/test_retrieve_spec_tool.py`: `retrieve_spec` tests
- `tests/unit/test_benchmark_assets.py`: benchmark asset existence and shape tests
- `tests/integration/test_server_registration.py`: MCP server tool registration test
- `tests/integration/test_tool_loop.py`: validation plus diagnostics loop test using fixtures
- `tests/fixtures/validator/fake_validator.py`: fake validator for deterministic tests
- `tests/fixtures/knowledge/*.json`: sample structured schema records for unit tests

## Task 1: Bootstrap The Python Project

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `src/openscenario_mcp/__init__.py`
- Create: `tests/unit/test_package_import.py`

- [ ] **Step 1: Write the failing package smoke test**

```python
from openscenario_mcp import __version__


def test_package_exposes_version() -> None:
    assert __version__ == "0.1.0"
```

- [ ] **Step 2: Run the smoke test to confirm the package does not exist yet**

Run: `python -m pytest tests/unit/test_package_import.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'openscenario_mcp'`

- [ ] **Step 3: Add project metadata and dependency declarations**

```toml
[project]
name = "openscenario-mcp"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["mcp[cli]<2", "pytest"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 4: Add the minimal package and ignore rules**

```python
__version__ = "0.1.0"
```

```gitignore
.venv/
__pycache__/
.pytest_cache/
*.pyc
```

- [ ] **Step 5: Re-run the smoke test**

Run: `python -m pytest tests/unit/test_package_import.py -v`
Expected: PASS

- [ ] **Step 6: Initialize git if the repository is still missing, then commit the bootstrap**

Run: `git rev-parse --is-inside-work-tree`
Expected: either `true` or a failure indicating no repository

Run if needed: `git init`
Expected: `Initialized empty Git repository`

Run: `git add pyproject.toml .gitignore README.md src/openscenario_mcp/__init__.py tests/unit/test_package_import.py`

Run: `git commit -m "chore: bootstrap openscenario mcp project"`

## Task 2: Stage Raw Materials, Core Models, And Shared Test Fixtures

**Files:**
- Create: `knowledge/raw/docs/.gitkeep`
- Create: `knowledge/raw/schema/.gitkeep`
- Create: `knowledge/raw/validator/.gitkeep`
- Create: `knowledge/source_inventory.json`
- Create: `src/openscenario_mcp/models.py`
- Create: `src/openscenario_mcp/knowledge/source_inventory.py`
- Create: `tests/conftest.py`
- Create: `tests/unit/test_source_inventory.py`

- [ ] **Step 1: Write failing tests for manifest parsing and validation**

```python
import json
from pathlib import Path

from openscenario_mcp.knowledge.source_inventory import load_source_inventory


def test_load_source_inventory_reads_entries(tmp_path: Path) -> None:
    manifest = tmp_path / "source_inventory.json"
    manifest.write_text(
        '{"sources":[{"id":"spec-doc","kind":"doc","path":"knowledge/raw/docs/spec.md"}]}',
        encoding="utf-8",
    )

    inventory = load_source_inventory(manifest)

    assert inventory[0].id == "spec-doc"
    assert inventory[0].kind == "doc"
```

- [ ] **Step 2: Run the source inventory test to confirm the loader is missing**

Run: `python -m pytest tests/unit/test_source_inventory.py -v`
Expected: FAIL with `ModuleNotFoundError` or missing attribute errors

- [ ] **Step 3: Define the source models and loader**

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceEntry:
    id: str
    kind: str
    path: str


@dataclass(frozen=True)
class ElementRecord:
    element: str
    description: str
    parent_contexts: list[str]
    required_attributes: list[dict]
    optional_attributes: list[dict]
    allowed_children: list[dict]
    child_order: list[str]
    multiplicity: dict[str, str]
    enum_constraints: dict[str, list[str]]
    source_path: str


@dataclass(frozen=True)
class ValidationError:
    line: int | None
    column: int | None
    message: str
    rule_hint: str | None = None


@dataclass
class KnowledgeBase:
    records_by_element: dict[str, ElementRecord]

    def search(self, query: str, kind: str, top_k: int) -> list[dict]:
        ...


@dataclass(frozen=True)
class ScenarioIntent:
    parameters: list[dict]
    entities: list[dict]
    environment: dict
    map_context: dict
    init_actions: list[dict]
    story_actions: list[dict]
    triggers: list[dict]
    stop_conditions: list[dict]
    assumptions: list[str]


def load_source_inventory(path: Path) -> list[SourceEntry]:
    ...
```

- [ ] **Step 4: Create the live source manifest and staging directories**

```json
{
  "sources": [
    {"id": "osc-docs", "kind": "doc", "path": "knowledge/raw/docs"},
    {"id": "osc-schema", "kind": "schema", "path": "knowledge/raw/schema"},
    {"id": "osc-validator", "kind": "validator", "path": "knowledge/raw/validator"}
  ]
}
```

Also place the user's real materials into these exact directories before starting Task 3.

- [ ] **Step 5: Add shared fixtures for downstream tests**

Create `tests/conftest.py` with:
- `sample_knowledge_base`
- `fake_validator_module`
- `sample_diagnostic_patterns`
- a helper that writes sample `ElementRecord` JSON to a temporary directory

`fake_validator_module` should be an import-path string fixture, not a module object.

Use minimal fixtures now so later tasks fail for the intended reasons instead of missing pytest fixtures.

- [ ] **Step 6: Re-run the inventory test**

Run: `python -m pytest tests/unit/test_source_inventory.py -v`
Expected: PASS

- [ ] **Step 7: Commit the staged-source foundation**

Run: `git add knowledge/source_inventory.json knowledge/raw src/openscenario_mcp/models.py src/openscenario_mcp/knowledge/source_inventory.py tests/conftest.py tests/unit/test_source_inventory.py`

Run: `git commit -m "feat: add source inventory and raw material staging"`

## Task 3: Pin The MVP Scope And Build Structured Schema Records

**Files:**
- Create: `knowledge/structured/mvp_scope.json`
- Create: `knowledge/structured/elements/OpenSCENARIO.json`
- Create: `knowledge/structured/elements/FileHeader.json`
- Create: `knowledge/structured/elements/ParameterDeclarations.json`
- Create: `knowledge/structured/elements/LogicFile.json`
- Create: `knowledge/structured/elements/RoadNetwork.json`
- Create: `knowledge/structured/elements/Entities.json`
- Create: `knowledge/structured/elements/ScenarioObject.json`
- Create: `knowledge/structured/elements/Vehicle.json`
- Create: `knowledge/structured/elements/BoundingBox.json`
- Create: `knowledge/structured/elements/Center.json`
- Create: `knowledge/structured/elements/Dimensions.json`
- Create: `knowledge/structured/elements/Performance.json`
- Create: `knowledge/structured/elements/Axles.json`
- Create: `knowledge/structured/elements/FrontAxle.json`
- Create: `knowledge/structured/elements/RearAxle.json`
- Create: `knowledge/structured/elements/Storyboard.json`
- Create: `knowledge/structured/elements/Init.json`
- Create: `knowledge/structured/elements/Actions.json`
- Create: `knowledge/structured/elements/Private.json`
- Create: `knowledge/structured/elements/PrivateAction.json`
- Create: `knowledge/structured/elements/LongitudinalAction.json`
- Create: `knowledge/structured/elements/SpeedAction.json`
- Create: `knowledge/structured/elements/SpeedActionDynamics.json`
- Create: `knowledge/structured/elements/SpeedActionTarget.json`
- Create: `knowledge/structured/elements/AbsoluteTargetSpeed.json`
- Create: `knowledge/structured/elements/LateralAction.json`
- Create: `knowledge/structured/elements/LaneChangeAction.json`
- Create: `knowledge/structured/elements/LaneChangeActionDynamics.json`
- Create: `knowledge/structured/elements/LaneChangeTarget.json`
- Create: `knowledge/structured/elements/RelativeTargetLane.json`
- Create: `knowledge/structured/elements/Story.json`
- Create: `knowledge/structured/elements/Act.json`
- Create: `knowledge/structured/elements/ManeuverGroup.json`
- Create: `knowledge/structured/elements/Actors.json`
- Create: `knowledge/structured/elements/EntityRef.json`
- Create: `knowledge/structured/elements/Maneuver.json`
- Create: `knowledge/structured/elements/Event.json`
- Create: `knowledge/structured/elements/Action.json`
- Create: `knowledge/structured/elements/StartTrigger.json`
- Create: `knowledge/structured/elements/ConditionGroup.json`
- Create: `knowledge/structured/elements/Condition.json`
- Create: `knowledge/structured/elements/TriggeringEntities.json`
- Create: `knowledge/structured/elements/ByEntityCondition.json`
- Create: `knowledge/structured/elements/EntityCondition.json`
- Create: `knowledge/structured/elements/RelativeDistanceCondition.json`
- Create: `knowledge/structured/elements/ByValueCondition.json`
- Create: `knowledge/structured/elements/SimulationTimeCondition.json`
- Create: `knowledge/structured/elements/StopTrigger.json`
- Create: `src/openscenario_mcp/knowledge/loader.py`
- Create: `src/openscenario_mcp/tools/schema.py`
- Create: `tests/fixtures/knowledge/file_header.json`
- Create: `tests/unit/test_loader.py`
- Create: `tests/unit/test_schema_tool.py`

- [ ] **Step 1: Write a failing loader test for one structured element record**

```python
from pathlib import Path

from openscenario_mcp.knowledge.loader import load_element_record


def test_load_element_record_returns_children_and_attributes(tmp_path: Path) -> None:
    record = tmp_path / "FileHeader.json"
    record.write_text(
        '{"element":"FileHeader","description":"Header","parent_contexts":["OpenSCENARIO"],"required_attributes":[{"name":"revMajor"}],"optional_attributes":[],"allowed_children":[],"child_order":[],"multiplicity":{},"enum_constraints":{},"source_path":"knowledge/raw/docs/osc-spec.md#FileHeader"}',
        encoding="utf-8",
    )

    element = load_element_record(record)

    assert element.element == "FileHeader"
    assert element.required_attributes[0]["name"] == "revMajor"
```

- [ ] **Step 2: Write a failing tool test for `get_element_schema`**

```python
from openscenario_mcp.tools.schema import build_get_element_schema_tool


def test_get_element_schema_returns_named_record(sample_knowledge_base) -> None:
    tool = build_get_element_schema_tool(sample_knowledge_base)
    result = tool("FileHeader")

    assert result["element"] == "FileHeader"
    assert result["required_attributes"][0]["name"] == "revMajor"
```

- [ ] **Step 3: Run the loader and schema tests**

Run: `python -m pytest tests/unit/test_loader.py tests/unit/test_schema_tool.py -v`
Expected: FAIL because the loader and tool do not exist yet

- [ ] **Step 4: Record the exact MVP scope before authoring records**

Create `knowledge/structured/mvp_scope.json` with:
- the exact OpenSCENARIO version read from the provided XSD or validator docs
- the initial benchmark-driven element list

Start with this element set for the four planned prompts:
- `OpenSCENARIO`
- `FileHeader`
- `ParameterDeclarations`
- `LogicFile`
- `RoadNetwork`
- `Entities`
- `ScenarioObject`
- `Vehicle`
- `BoundingBox`
- `Center`
- `Dimensions`
- `Performance`
- `Axles`
- `FrontAxle`
- `RearAxle`
- `Storyboard`
- `Init`
- `Actions`
- `Private`
- `PrivateAction`
- `LongitudinalAction`
- `SpeedAction`
- `SpeedActionDynamics`
- `SpeedActionTarget`
- `AbsoluteTargetSpeed`
- `LateralAction`
- `LaneChangeAction`
- `LaneChangeActionDynamics`
- `LaneChangeTarget`
- `RelativeTargetLane`
- `Story`
- `Act`
- `ManeuverGroup`
- `Actors`
- `EntityRef`
- `Maneuver`
- `Event`
- `Action`
- `StartTrigger`
- `ConditionGroup`
- `Condition`
- `TriggeringEntities`
- `ByEntityCondition`
- `EntityCondition`
- `RelativeDistanceCondition`
- `ByValueCondition`
- `SimulationTimeCondition`
- `StopTrigger`

- [ ] **Step 5: Implement the structured record loader and schema tool**

```python
def load_element_record(path: Path) -> ElementRecord:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ElementRecord(**payload)


def build_get_element_schema_tool(knowledge_base: KnowledgeBase):
    def get_element_schema(element: str) -> dict:
        record = knowledge_base.records_by_element[element]
        return asdict(record)

    return get_element_schema
```

- [ ] **Step 6: Seed the MVP with hand-authored records for the exact scope file**

Use the user's docs and schema as the source of truth, and include these fields in every record:
- `element`
- `description`
- `parent_contexts`
- `required_attributes`
- `optional_attributes`
- `allowed_children`
- `child_order`
- `multiplicity`
- `enum_constraints`
- `source_path`

`source_path` must point to the raw authority source and section anchor, for example:
- `knowledge/raw/docs/osc-spec.md#FileHeader`
- `knowledge/raw/schema/OpenSCENARIO.xsd#FileHeader`

- [ ] **Step 7: Re-run the loader and schema tests**

Run: `python -m pytest tests/unit/test_loader.py tests/unit/test_schema_tool.py -v`
Expected: PASS

- [ ] **Step 8: Commit the structured schema foundation**

Run: `git add knowledge/structured/mvp_scope.json knowledge/structured/elements src/openscenario_mcp/knowledge/loader.py src/openscenario_mcp/tools/schema.py tests/fixtures/knowledge tests/unit/test_loader.py tests/unit/test_schema_tool.py`

Run: `git commit -m "feat: add structured schema records and schema lookup tool"`

## Task 4: Wrap The Real Validator And Normalize `validate_xml`

**Files:**
- Create: `src/openscenario_mcp/config.py`
- Create: `src/openscenario_mcp/validator/adapter.py`
- Create: `src/openscenario_mcp/validator/real_validator.py`
- Create: `src/openscenario_mcp/tools/validate.py`
- Create: `tests/fixtures/validator/fake_validator.py`
- Create: `tests/unit/test_validate_tool.py`

- [ ] **Step 1: Write a failing test for normalized validator output**

```python
from openscenario_mcp.tools.validate import build_validate_xml_tool
from openscenario_mcp.validator.adapter import ValidatorAdapter


def test_validate_xml_returns_normalized_errors(fake_validator_module) -> None:
    tool = build_validate_xml_tool(ValidatorAdapter(fake_validator_module))
    xml = "<OpenSCENARIO><Broken /></OpenSCENARIO>"

    result = tool(xml=xml, schema_version="1.0")

    assert result["ok"] is False
    assert result["errors"][0]["line"] == 1
    assert "message" in result["errors"][0]
```

- [ ] **Step 2: Run the validator test to confirm the adapter is missing**

Run: `python -m pytest tests/unit/test_validate_tool.py -v`
Expected: FAIL because `validate_xml` is not implemented

- [ ] **Step 3: Implement the validator adapter as a thin wrapper**

```python
class ValidatorAdapter:
    def __init__(self, validator_module: str = "openscenario_mcp.validator.real_validator") -> None:
        self._module = import_module(validator_module)

    def validate(self, xml: str, schema_version: str) -> list[dict]:
        return self._module.validate(xml, schema_version)
```

- [ ] **Step 4: Normalize raw errors behind a public-tool factory**

```python
def build_validate_xml_tool(adapter: ValidatorAdapter):
    def validate_xml(xml: str, schema_version: str) -> dict:
        errors = adapter.validate(xml, schema_version)
        return {"ok": len(errors) == 0, "errors": errors}

    return validate_xml
```

- [ ] **Step 5: Swap the fake validator for the real validator once the wrapper passes**

Create `src/openscenario_mcp/validator/real_validator.py` as the only project-local wrapper over the user's validator assets in `knowledge/raw/validator/`.

Document this contract in `README.md`:
- raw validator files live under `knowledge/raw/validator/`
- `real_validator.py` is responsible for adapting them
- `ValidatorAdapter` only imports an importable module path
- every validator module must expose `validate(xml, schema_version)`
- every validator error must normalize to the expected payload keys

- [ ] **Step 6: Re-run the validator test**

Run: `python -m pytest tests/unit/test_validate_tool.py -v`
Expected: PASS

- [ ] **Step 7: Commit the validator integration layer**

Run: `git add README.md src/openscenario_mcp/config.py src/openscenario_mcp/validator/adapter.py src/openscenario_mcp/validator/real_validator.py src/openscenario_mcp/tools/validate.py tests/fixtures/validator/fake_validator.py tests/unit/test_validate_tool.py`

Run: `git commit -m "feat: add xml validation adapter and tool"`

## Task 5: Add Diagnostic Classification And `explain_validation_errors`

**Files:**
- Create: `knowledge/diagnostics/patterns.json`
- Create: `src/openscenario_mcp/validator/classifier.py`
- Create: `src/openscenario_mcp/tools/diagnostics.py`
- Create: `tests/unit/test_diagnostics_tool.py`

- [ ] **Step 1: Write a failing diagnostic test for a missing-child error**

```python
from openscenario_mcp.tools.diagnostics import build_explain_validation_errors_tool
from openscenario_mcp.validator.classifier import load_patterns


def test_explain_validation_errors_classifies_missing_child() -> None:
    errors = [
        {
            "line": 12,
            "column": 8,
            "message": "Element 'ManeuverGroup': Missing child element(s). Expected is ( Actors ).",
        }
    ]

    explain_validation_errors = build_explain_validation_errors_tool(load_patterns())
    result = explain_validation_errors(errors)

    assert result["diagnostics"][0]["category"] == "missing_required_child"
    assert result["diagnostics"][0]["missing"] == ["Actors"]
```

- [ ] **Step 2: Run the diagnostic test to confirm the classifier is missing**

Run: `python -m pytest tests/unit/test_diagnostics_tool.py -v`
Expected: FAIL because `explain_validation_errors` is not implemented

- [ ] **Step 3: Encode the first diagnostic patterns**

```json
[
  {
    "contains": "Missing child element",
    "category": "missing_required_child",
    "template": "Add the required child elements listed in the validator message."
  }
]
```

- [ ] **Step 4: Implement the classifier and tool**

```python
def build_explain_validation_errors_tool(patterns: list[dict]):
    def explain_validation_errors(errors: list[dict]) -> dict:
        diagnostics = []
        for error in errors:
            diagnostics.append(classify_error(error["message"], patterns))
        return {"diagnostics": diagnostics}

    return explain_validation_errors
```

- [ ] **Step 5: Extend coverage for the remaining MVP categories**

Add patterns for:
- `missing_required_attribute`
- `unexpected_element`
- `invalid_attribute`
- `wrong_child_order`
- `invalid_enum_value`
- `namespace_or_root_issue`

- [ ] **Step 6: Re-run the diagnostic test**

Run: `python -m pytest tests/unit/test_diagnostics_tool.py -v`
Expected: PASS

- [ ] **Step 7: Commit the diagnostic layer**

Run: `git add knowledge/diagnostics/patterns.json src/openscenario_mcp/validator/classifier.py src/openscenario_mcp/tools/diagnostics.py tests/unit/test_diagnostics_tool.py`

Run: `git commit -m "feat: add validation diagnostics tool"`

## Task 6: Implement `retrieve_spec` With Source-Linked Results

**Files:**
- Create: `src/openscenario_mcp/knowledge/search.py`
- Create: `src/openscenario_mcp/tools/retrieve_spec.py`
- Create: `tests/unit/test_retrieve_spec_tool.py`

- [ ] **Step 1: Write failing retrieval tests for element, attribute, and error-topic queries**

```python
from openscenario_mcp.tools.retrieve_spec import build_retrieve_spec_tool


def test_retrieve_spec_returns_source_linked_hits(sample_knowledge_base) -> None:
    tool = build_retrieve_spec_tool(sample_knowledge_base, sample_diagnostic_patterns)
    result = tool(query="Storyboard", kind="element", top_k=3)

    assert result["hits"][0]["title"] == "Storyboard"
    assert result["hits"][0]["source_path"].startswith("knowledge/raw/")


def test_retrieve_spec_supports_attribute_error_and_concept_queries(sample_knowledge_base, sample_diagnostic_patterns) -> None:
    tool = build_retrieve_spec_tool(sample_knowledge_base, sample_diagnostic_patterns)

    attribute_result = tool(query="revMajor", kind="attribute", top_k=1)
    error_result = tool(query="missing_required_child", kind="error", top_k=1)
    concept_result = tool(query="story start", kind="concept", top_k=1)

    assert attribute_result["hits"][0]["source_path"].startswith("knowledge/raw/")
    assert error_result["hits"][0]["title"] == "missing_required_child"
    assert concept_result["hits"][0]["source_path"].startswith("knowledge/raw/")
```

- [ ] **Step 2: Run the retrieval test to confirm the search layer is missing**

Run: `python -m pytest tests/unit/test_retrieve_spec_tool.py -v`
Expected: FAIL because `retrieve_spec` is not implemented

- [ ] **Step 3: Implement a minimal keyword scorer before considering anything more complex**

```python
def score_hit(query: str, text: str) -> int:
    lowered_query = query.lower()
    lowered_text = text.lower()
    return lowered_text.count(lowered_query)
```

- [ ] **Step 4: Implement `retrieve_spec` over structured records plus diagnostic patterns**

```python
def build_retrieve_spec_tool(knowledge_base: KnowledgeBase, diagnostic_patterns: list[dict]):
    def retrieve_spec(query: str, kind: str, top_k: int = 5) -> dict:
        hits = search_structured_records(
            knowledge_base=knowledge_base,
            diagnostic_patterns=diagnostic_patterns,
            query=query,
            kind=kind,
            top_k=top_k,
        )
        return {"hits": hits}

    return retrieve_spec
```

MVP coverage for `retrieve_spec` must include:
- element-name queries
- attribute-name queries derived from structured records
- error-topic queries derived from diagnostic patterns
- concept queries backed by element descriptions and aliases

Raw-prose full-text retrieval can wait until after the structured layer is stable.

- [ ] **Step 5: Re-run the retrieval test**

Run: `python -m pytest tests/unit/test_retrieve_spec_tool.py -v`
Expected: PASS

- [ ] **Step 6: Commit the retrieval tool**

Run: `git add src/openscenario_mcp/knowledge/search.py src/openscenario_mcp/tools/retrieve_spec.py tests/unit/test_retrieve_spec_tool.py`

Run: `git commit -m "feat: add spec retrieval tool"`

## Task 7: Assemble And Smoke-Test The MCP Server

**Files:**
- Create: `src/openscenario_mcp/__main__.py`
- Create: `src/openscenario_mcp/runtime.py`
- Create: `src/openscenario_mcp/server.py`
- Create: `scripts/start_mcp_server.cmd`
- Create: `docs/codex-mcp-setup.md`
- Create: `tests/integration/test_server_registration.py`
- Modify: `README.md`

- [ ] **Step 1: Write a failing integration test for tool registration**

```python
from openscenario_mcp.runtime import build_runtime_for_tests
from openscenario_mcp.server import build_server


def test_build_server_registers_four_tools() -> None:
    runtime = build_runtime_for_tests()
    server = build_server(runtime)
    tool_names = sorted(tool.name for tool in server.list_tools())

    assert tool_names == [
        "retrieve_spec",
        "get_element_schema",
        "validate_xml",
        "explain_validation_errors",
    ]
```

- [ ] **Step 2: Run the integration test**

Run: `python -m pytest tests/integration/test_server_registration.py -v`
Expected: FAIL because `build_server` is not implemented

- [ ] **Step 3: Add an explicit runtime-composition layer**

Create `src/openscenario_mcp/runtime.py` to load and hold:
- `KnowledgeBase`
- diagnostic patterns
- `ValidatorAdapter`

Keep these as server-local dependencies, not MCP tool arguments.

- [ ] **Step 4: Wire the MCP server around thin public wrappers**

```python
def build_server(runtime: Runtime) -> FastMCP:
    mcp = FastMCP("openscenario-mcp", json_response=True)

    retrieve_spec_impl = build_retrieve_spec_tool(runtime.knowledge_base, runtime.patterns)
    get_element_schema_impl = build_get_element_schema_tool(runtime.knowledge_base)
    validate_xml = build_validate_xml_tool(runtime.validator)
    explain_validation_errors = build_explain_validation_errors_tool(runtime.patterns)

    @mcp.tool()
    def retrieve_spec(query: str, kind: str, top_k: int = 5) -> dict:
        return retrieve_spec_impl(query=query, kind=kind, top_k=top_k)

    @mcp.tool()
    def get_element_schema(element: str) -> dict:
        return get_element_schema_impl(element)

    return mcp
```

- [ ] **Step 5: Add the remaining two tool wrappers and a module entry point**

```python
if __name__ == "__main__":
    runtime = build_runtime_from_config()
    build_server(runtime).run()
```

- [ ] **Step 6: Re-run the integration test**

Run: `python -m pytest tests/integration/test_server_registration.py -v`
Expected: PASS

- [ ] **Step 7: Add a stable local launcher and Codex registration instructions**

Create `scripts/start_mcp_server.cmd` so Codex can launch the same server command every time without depending on an activated shell.

Create `docs/codex-mcp-setup.md` with a snippet for `C:\Users\EDY\.codex\config.toml`:

```toml
[mcp_servers.openscenario]
command = "D:\\wyj\\OPenscenario\\scripts\\start_mcp_server.cmd"
```

Document that the benchmark tasks in Task 10 depend on this registration being present before starting a new Codex session.

- [ ] **Step 8: Add launch instructions to `README.md`**

Run target: `python -m openscenario_mcp`
Document:
- required raw-material directories
- how to point at the validator module
- how to start the server in local development
- how Codex registers the server through `docs/codex-mcp-setup.md`

- [ ] **Step 9: Commit the server assembly**

Run: `git add README.md docs/codex-mcp-setup.md scripts/start_mcp_server.cmd src/openscenario_mcp/__main__.py src/openscenario_mcp/runtime.py src/openscenario_mcp/server.py tests/integration/test_server_registration.py`

Run: `git commit -m "feat: assemble openscenario mcp server"`

## Task 8: Create The Project-Local Codex Skill And Benchmark Assets

**Files:**
- Create: `skills/openscenario-xml-generator/SKILL.md`
- Create: `scripts/install_codex_skill.py`
- Create: `benchmarks/prompts/minimal-single-vehicle.md`
- Create: `benchmarks/intent-schema.json`
- Create: `benchmarks/prompts/two-vehicle-follow.md`
- Create: `benchmarks/prompts/triggered-deceleration.md`
- Create: `benchmarks/prompts/triggered-lane-change.md`
- Create: `benchmarks/invalid_xml/missing-actors.xml`
- Create: `benchmarks/invalid_xml/invalid-enum.xml`
- Create: `benchmarks/results/.gitkeep`
- Create: `benchmarks/results/run-log.md`
- Create: `scripts/validate_benchmark_output.py`
- Create: `tests/unit/test_benchmark_assets.py`

- [ ] **Step 1: Write a failing benchmark asset test**

```python
from pathlib import Path


def test_benchmark_assets_exist() -> None:
    assert Path("benchmarks/prompts/minimal-single-vehicle.md").exists()
    assert Path("benchmarks/invalid_xml/missing-actors.xml").exists()
```

- [ ] **Step 2: Run the benchmark asset test**

Run: `python -m pytest tests/unit/test_benchmark_assets.py -v`
Expected: FAIL because the benchmark files do not exist yet

- [ ] **Step 3: Write the skill using `@superpowers/writing-skills` guidance**

The skill must instruct Codex to:
- parse the user request into intermediate intent first
- serialize that parsed intent using the shared `ScenarioIntent` shape before drafting XML
- query MCP before writing each XML block
- draft conservative XML
- run `validate_xml`
- run `explain_validation_errors` on failure
- repair only the affected region
- compare the repaired XML back to the parsed intent checklist before marking the run successful
- stop after a bounded retry budget

- [ ] **Step 4: Install the skill into Codex's discovered skill directory**

Use `scripts/install_codex_skill.py` to copy:
- from `skills/openscenario-xml-generator/SKILL.md`
- to `C:\Users\EDY\.codex\skills\openscenario-xml-generator\SKILL.md`

Document that benchmark execution requires starting a fresh Codex session after installation so the skill is discoverable.

- [ ] **Step 5: Add benchmark prompts, invalid XML fixtures, and output-capture locations**

Create `benchmarks/intent-schema.json` explicitly. It must define the keys for:
- `parsed_intent`
- `xml_intent_check`
- `schema_valid`
- `intent_consistent`
- `remaining_blockers`

Prompt set:
- minimal single vehicle
- two-vehicle follow
- trigger-based deceleration
- trigger-based lane change

Invalid XML set:
- missing required child
- invalid enum value

Generated-output set:
- one saved result XML per prompt under `benchmarks/results/`
- one machine-readable `*.intent.json` sidecar per prompt under `benchmarks/results/`
- one row or section in `benchmarks/results/run-log.md` recording `pass` or `bounded_failure`

- [ ] **Step 6: Re-run the benchmark asset test**

Run: `python -m pytest tests/unit/test_benchmark_assets.py -v`
Expected: PASS

- [ ] **Step 7: Commit the skill and benchmark assets**

Run: `git add skills/openscenario-xml-generator/SKILL.md scripts/install_codex_skill.py benchmarks tests/unit/test_benchmark_assets.py`

Run: `git commit -m "feat: add openscenario xml generation skill and benchmarks"`

## Task 9: Prove The Validation And Diagnostics Loop End To End

**Files:**
- Create: `tests/integration/test_tool_loop.py`
- Modify: `knowledge/structured/elements/*.json`
- Modify: `knowledge/diagnostics/patterns.json`

- [ ] **Step 1: Write a failing integration test that chains validation and diagnostics**

```python
from openscenario_mcp.tools.diagnostics import build_explain_validation_errors_tool
from openscenario_mcp.tools.validate import build_validate_xml_tool
from openscenario_mcp.validator.adapter import ValidatorAdapter
from openscenario_mcp.validator.classifier import load_patterns


def test_invalid_xml_round_trips_into_structured_diagnostics(fake_validator_module) -> None:
    validate = build_validate_xml_tool(ValidatorAdapter(fake_validator_module))
    explain = build_explain_validation_errors_tool(load_patterns())
    result = validate(xml="<ManeuverGroup />", schema_version="1.0")

    diagnostics = explain(result["errors"])

    assert result["ok"] is False
    assert diagnostics["diagnostics"][0]["category"] == "missing_required_child"
```

- [ ] **Step 2: Run the integration loop test**

Run: `python -m pytest tests/integration/test_tool_loop.py -v`
Expected: FAIL until the tool payloads line up correctly

- [ ] **Step 3: Tighten the payload contracts until the loop passes without ad hoc parsing in the test**

Expected stable fields:
- validator errors: `line`, `column`, `message`, `rule_hint`
- diagnostics: `category`, `element`, `missing`, `fix_advice`

- [ ] **Step 4: Re-run the focused integration tests**

Run: `python -m pytest tests/integration/test_server_registration.py tests/integration/test_tool_loop.py -v`
Expected: PASS

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest -v`
Expected: PASS

- [ ] **Step 6: Commit the verified MVP loop**

Run: `git add knowledge/structured/elements knowledge/diagnostics/patterns.json tests/integration/test_tool_loop.py`

Run: `git commit -m "feat: verify validation and diagnostics loop"`

## Task 10: Capture And Validate Benchmark Outputs From The Codex Skill

**Files:**
- Create: `tests/integration/test_benchmark_results.py`
- Modify: `scripts/validate_benchmark_output.py`
- Modify: `benchmarks/results/run-log.md`
- Modify: `benchmarks/results/*.xml`
- Modify: `benchmarks/results/*.intent.json`
- Modify: `benchmarks/results/*.md`

- [ ] **Step 1: Write a failing benchmark-results integration test**

```python
from pathlib import Path


def test_every_benchmark_prompt_has_a_recorded_result() -> None:
    prompts = sorted(Path("benchmarks/prompts").glob("*.md"))
    for prompt in prompts:
        stem = prompt.stem
        report = json.loads(Path(f"benchmarks/results/{stem}.intent.json").read_text(encoding="utf-8"))

        assert Path(f"benchmarks/results/{stem}.xml").exists()
        assert "parsed_intent" in report
        assert "schema_valid" in report
        assert "intent_consistent" in report
```

- [ ] **Step 2: Add `scripts/validate_benchmark_output.py`**

The script must:
- load each XML file in `benchmarks/results/`
- run the real validator when available, otherwise the fake validator in tests
- verify that each prompt also has a machine-readable sidecar at `benchmarks/results/<prompt-name>.intent.json` with this schema:
  - `parsed_intent`: the original `ScenarioIntent`
  - `xml_intent_check`: `{matched: [], missing: [], extra: []}`
  - `schema_valid`: `true|false`
  - `intent_consistent`: `true|false`
  - `remaining_blockers`: list of strings
- emit `pass` only when the XML is schema-valid and the sidecar report sets `intent_consistent` to `true`
- emit `bounded_failure` for every other outcome, including schema-valid but intent-wrong XML
- update `benchmarks/results/run-log.md`

- [ ] **Step 3: Run each prompt through the project-local skill manually and save the outputs**

For each prompt in `benchmarks/prompts/`:
- invoke the `openscenario-xml-generator` skill in Codex
- save the returned XML to `benchmarks/results/<prompt-name>.xml`
- save a machine-readable sidecar to `benchmarks/results/<prompt-name>.intent.json` using `benchmarks/intent-schema.json`
- ensure the sidecar contains:
  - the parsed `ScenarioIntent`
  - an `xml_intent_check` section listing matched, missing, and extra intent items
  - `schema_valid`
  - `intent_consistent`
  - remaining blockers if the run ended without valid XML
- if the skill cannot produce valid XML within the retry budget, save the last draft and record `bounded_failure` with explicit blockers

- [ ] **Step 4: Run the benchmark validation script**

Run: `python scripts/validate_benchmark_output.py`
Expected: one logged outcome per prompt in `benchmarks/results/run-log.md`, where only schema-valid plus intent-consistent outputs are marked `pass`

- [ ] **Step 5: Re-run the benchmark-results integration test**

Run: `python -m pytest tests/integration/test_benchmark_results.py -v`
Expected: PASS

- [ ] **Step 6: Commit the recorded benchmark outcomes**

Run: `git add benchmarks/results scripts/validate_benchmark_output.py tests/integration/test_benchmark_results.py`

Run: `git commit -m "test: capture and validate benchmark outputs"`

## Task 11: Document Real-Data Onboarding And Manual Acceptance

**Files:**
- Modify: `README.md`
- Create: `docs/manual-acceptance/openscenario-mcp-checklist.md`

- [ ] **Step 1: Write a failing doc test or checklist assertion by creating the acceptance checklist file first**

```markdown
# OpenSCENARIO MCP Manual Acceptance

- [ ] Raw docs copied into `knowledge/raw/docs/`
- [ ] Schema copied into `knowledge/raw/schema/`
- [ ] Real validator wired through `validate(xml, schema_version)`
- [ ] `python -m pytest -v` passes
- [ ] MCP server starts locally
- [ ] One benchmark prompt is exercised through the skill manually
```

- [ ] **Step 2: Expand `README.md` with exact onboarding steps**

Include:
- where to place the user's documents
- how to encode the first MVP element records
- how to point the server at the real validator
- how to run tests
- how to launch the MCP server
- how to register the MCP server in `C:\Users\EDY\.codex\config.toml`
- how to invoke the project-local skill during Codex sessions

- [ ] **Step 3: Perform the documented acceptance commands**

Run: `python -m pytest -v`
Expected: PASS

Restart Codex after adding the local MCP registration snippet.
Expected: the `openscenario` MCP server is available to the session

Run: `python -m openscenario_mcp`
Expected: the server starts and waits for MCP client input without import errors

Run: `python scripts/validate_benchmark_output.py`
Expected: benchmark run log shows one recorded outcome for every prompt

- [ ] **Step 4: Commit the onboarding and acceptance docs**

Run: `git add README.md docs/manual-acceptance/openscenario-mcp-checklist.md`

Run: `git commit -m "docs: add onboarding and acceptance checklist"`

## Sequencing Notes

- Do not start Task 4 until the user's actual validator entry point is available in `knowledge/raw/validator/` and described well enough to wrap.
- Do not broaden element coverage beyond the benchmark-driven MVP subset until Task 9 is passing.
- Keep retrieval keyword-based for the MVP. Do not introduce embeddings or a vector database unless the structured-record search clearly fails.
- Keep `retrieve_spec` MVP-limited to structured element records first. Do not claim attribute-level or error-topic retrieval from raw prose until the structured layer is stable.
- When creating the project-local skill in Task 8, keep it focused on using the MCP tools. Do not embed schema facts directly into the skill body.
- The skill benchmark in Task 10 is intentionally semi-manual because the repo does not yet include a stable Codex automation API. The required artifact per prompt is a saved XML output, a machine-readable `intent.json` sidecar, and a validated run-log entry.
