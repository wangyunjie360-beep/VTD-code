from __future__ import annotations

from pathlib import Path

from openscenario_mcp.tools.validate import build_validate_xml_tool
from openscenario_mcp.validator.adapter import ValidatorAdapter

_VALID_MINIMAL_XML = """\
<OpenScenario>
  <FileHeader
    author="validator-smoke"
    date="2026-03-19T00:00:00"
    description="schema smoke test"
    revMajor="1"
    revMinor="4"
  />
  <CatalogLocations />
  <RoadNetwork />
  <Entities />
  <Storyboard>
    <Init>
      <Actions />
    </Init>
  </Storyboard>
</OpenScenario>
"""

_INVALID_MINIMAL_XML = """\
<OpenSCENARIO>
  <FileHeader
    date="2026-03-19T00:00:00"
    description="schema smoke test"
    revMajor="1"
    revMinor="4"
  />
  <CatalogLocations />
  <RoadNetwork />
  <Entities />
  <Storyboard>
    <Init>
      <Actions />
    </Init>
  </Storyboard>
</OpenSCENARIO>
"""

_INVALID_MISSING_FILE_HEADER_XML = """\
<OpenScenario>
  <CatalogLocations />
  <RoadNetwork />
  <Entities />
  <Storyboard>
    <Init>
      <Actions />
    </Init>
  </Storyboard>
</OpenScenario>
"""


def test_validate_xml_normalizes_adapter_errors(monkeypatch) -> None:
    monkeypatch.syspath_prepend(str(Path("tests/fixtures/validator").resolve()))
    tool = build_validate_xml_tool(
        adapter=ValidatorAdapter(module_name="fake_validator")
    )

    result = tool("<OpenSCENARIO />", schema_version="1.x")

    assert result == {
        "ok": False,
        "errors": [
            {
                "line": 7,
                "column": None,
                "message": "fixture validator rejected schema 1.x",
                "rule_hint": None,
            }
        ],
    }


def test_validate_xml_normalizes_missing_validator_module() -> None:
    tool = build_validate_xml_tool(
        adapter=ValidatorAdapter(
            module_name="definitely_missing_validator_module_for_test"
        )
    )

    result = tool("<OpenSCENARIO />", schema_version="1.x")

    assert result["ok"] is False
    assert result["errors"] == [
        {
            "line": None,
            "column": None,
            "message": "No module named 'definitely_missing_validator_module_for_test'",
            "rule_hint": None,
        }
    ]


def test_validate_xml_accepts_minimal_schema_valid_document() -> None:
    tool = build_validate_xml_tool()

    result = tool(_VALID_MINIMAL_XML)

    assert result == {"ok": True, "errors": []}


def test_validate_xml_reports_normalized_errors_for_invalid_document() -> None:
    tool = build_validate_xml_tool()

    result = tool(_INVALID_MINIMAL_XML, schema_version="1.x")

    assert result["ok"] is False
    assert result["errors"]
    assert all(
        set(error) == {"line", "column", "message", "rule_hint"}
        for error in result["errors"]
    )
    assert any(error["message"] for error in result["errors"])


def test_validate_xml_prefers_expected_element_in_rule_hint() -> None:
    tool = build_validate_xml_tool()

    result = tool(_INVALID_MISSING_FILE_HEADER_XML, schema_version="1.x")

    assert result["ok"] is False
    assert result["errors"] == [
        {
            "line": 2,
            "column": 0,
            "message": "Element 'CatalogLocations': This element is not expected. Expected is ( FileHeader ).",
            "rule_hint": "FileHeader",
        }
    ]
