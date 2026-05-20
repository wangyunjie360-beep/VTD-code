from __future__ import annotations

from pathlib import Path

from openscenario_mcp.models import ElementRecord, KnowledgeBase
from openscenario_mcp.tools.diagnostics import build_explain_validation_errors_tool
from openscenario_mcp.tools.guidance import build_xml_guidance_tool
from openscenario_mcp.tools.resolve_vtd_name import build_resolve_vtd_name_tool
from openscenario_mcp.tools.retrieve_vtd_asset import build_retrieve_vtd_asset_tool
from openscenario_mcp.tools.validate import build_validate_xml_tool
from openscenario_mcp.validator.adapter import ValidatorAdapter
from openscenario_mcp.validator.classifier import load_patterns

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_invalid_xml_round_trips_into_structured_diagnostics(
    fake_validator_module: str,
) -> None:
    validate = build_validate_xml_tool(ValidatorAdapter(fake_validator_module))
    explain = build_explain_validation_errors_tool(load_patterns())

    result = validate(xml="<ManeuverGroup />", schema_version="1.0")
    diagnostics = explain(result["errors"])

    assert result == {
        "ok": False,
        "errors": [
            {
                "line": 7,
                "column": 4,
                "message": (
                    "Element 'ManeuverGroup': Missing child element(s). "
                    "Expected is ( Actors )."
                ),
                "rule_hint": "Actors",
            }
        ],
    }
    assert diagnostics == {
        "diagnostics": [
            {
                "category": "missing_required_child",
                "line": 7,
                "column": 4,
                "message": (
                    "Element 'ManeuverGroup': Missing child element(s). "
                    "Expected is ( Actors )."
                ),
                "rule_hint": "Actors",
                "element": "ManeuverGroup",
                "expected": ["Actors"],
                "expected_text": "Actors",
                "requirement_kind": "all_of",
                "missing": ["Actors"],
                "required_child_description": (
                    "the required child element(s): Actors"
                ),
                "fix_advice": "Add the required child element(s): Actors under ManeuverGroup.",
                "repair_strategy": {
                    "focus_element": "ManeuverGroup",
                    "focus_strategy": {
                        "structure_mode": "sequence",
                        "branch_selection": {"mode": "none", "groups": []},
                        "ordering": {
                            "mode": "sequence",
                            "child_order": ["Actors", "CatalogReference", "Maneuver"],
                        },
                        "required_children": ["Actors"],
                        "variant_resolution": {
                            "selection_required": True,
                            "parent_context": None,
                            "resolved_variant": None,
                            "preferred_variants": [
                                {
                                    "parent_context": "Act",
                                    "type_ref": "ManeuverGroup",
                                    "deprecated": False,
                                }
                            ],
                            "deprecated_variants": [],
                        },
                        "reference_requirements": [],
                        "repair_priority": [
                            "resolve_contextual_variant",
                            "add_required_children",
                            "enforce_sequence_order",
                        ],
                    },
                    "expected_elements": ["Actors"],
                    "recommended_actions": [
                        "add_required_children",
                        "enforce_sequence_order",
                    ],
                },
            }
        ]
    }


def test_tool_loop_surfaces_vtd_name_resolution_before_schema_guidance(
    fake_validator_module: str,
    sample_vtd_knowledge_base,
) -> None:
    skill_text = _section_text(
        _repo_text("skills/openscenario-xml-generator/SKILL.md"),
        "## Workflow",
        "## Conservative Drafting Rules",
    )
    _assert_fragments_in_order(
        skill_text,
        [
            "retrieve_vtd_asset",
            "resolve_vtd_name",
            "build_xml_guidance",
            "validate_xml",
        ],
    )
    assert "hard_constraint" in skill_text
    assert "override_mapping" in skill_text

    retrieve_vtd_asset = build_retrieve_vtd_asset_tool(sample_vtd_knowledge_base)
    resolve_vtd_name = build_resolve_vtd_name_tool(sample_vtd_knowledge_base)
    build_xml_guidance = build_xml_guidance_tool(
        _build_tool_loop_knowledge_base(),
        load_patterns(),
    )
    validate = build_validate_xml_tool(ValidatorAdapter(fake_validator_module))
    explain = build_explain_validation_errors_tool(load_patterns())

    asset_lookup = retrieve_vtd_asset(
        query="Sg101Gefahrstelle01.flt",
        asset_kind="signal",
        country_code="CN",
        top_k=3,
    )
    assert asset_lookup["hits"][0]["canonical_name"] == "CN_Sg101_Gefahrenstelle01"

    soft_resolution = resolve_vtd_name(
        name="SharedSignal01",
        namespace="variable",
        asset_kind="signal",
        country_code="CN",
        user_override=True,
    )
    hard_resolution = resolve_vtd_name(
        name="Sg101Gefahrstelle01.flt",
        namespace="runtime_asset",
        asset_kind="signal",
        country_code="CN",
        user_override=True,
    )
    assert soft_resolution["hard_constraint"] is False
    assert soft_resolution["override_mapping"] == {
        "requested_name": "SharedSignal01",
        "safe_name": soft_resolution["safe_name"],
    }
    assert hard_resolution["hard_constraint"] is True
    assert hard_resolution["canonical_target"] == asset_lookup["hits"][0]["canonical_name"]
    assert "override_mapping" not in hard_resolution

    validation = validate(xml="<ManeuverGroup />", schema_version="1.0")
    repair_guidance = build_xml_guidance(
        query="ManeuverGroup",
        element="ManeuverGroup",
        parent_context="Act",
        top_k=1,
        errors=validation["errors"],
    )
    diagnostics = explain(validation["errors"])

    assert repair_guidance["retrieval_hits"]
    assert repair_guidance["element_schema"]["strategy"]["variant_resolution"][
        "resolved_variant"
    ] == {
        "parent_context": "Act",
        "type_ref": "ManeuverGroup",
        "deprecated": False,
    }
    assert repair_guidance["repair_actions"] == [
        "add_required_children",
        "enforce_sequence_order",
    ]
    assert diagnostics["diagnostics"][0]["repair_strategy"]["recommended_actions"] == [
        "add_required_children",
        "enforce_sequence_order",
    ]


def test_operator_docs_cover_vtd_lookup_order_and_snapshot_regeneration() -> None:
    readme_loop = _section_text(
        _repo_text("README.md"),
        "## VTD Naming Loop",
        "## Optional Guidance Packets",
    )
    usage_guide_loop = _section_text(
        _repo_text("docs/usage-guide-zh.md"),
        "### VTD 命名与约束闭环",
        "### 方式 B：先生成 `.guidance.json`，再让 Codex 或外部 agent 生成",
    )

    for document_text in (readme_loop, usage_guide_loop):
        _assert_fragments_in_order(
            document_text,
            [
                "retrieve_vtd_asset",
                "resolve_vtd_name",
                "build_xml_guidance",
                "validate_xml",
            ],
        )
        assert "hard_constraint" in document_text
        assert "override_mapping" in document_text

    readme_text = _repo_text("README.md")
    usage_guide_text = _repo_text("docs/usage-guide-zh.md")
    assert "scripts/build_vtd_knowledge_snapshot.py" in readme_text
    assert "scripts/build_vtd_knowledge_snapshot.py" in usage_guide_text


def _repo_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _assert_fragments_in_order(text: str, fragments: list[str]) -> None:
    positions = [text.index(fragment) for fragment in fragments]
    assert positions == sorted(positions)


def _section_text(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]


def _build_tool_loop_knowledge_base() -> KnowledgeBase:
    maneuver_group = ElementRecord(
        element="ManeuverGroup",
        description="Sequence container for Actors, optional CatalogReference, and Maneuver entries.",
        content_model_kind="sequence",
        contextual_variants=[
            {
                "parent_context": "Act",
                "type_ref": "ManeuverGroup",
                "deprecated": False,
            }
        ],
        parent_contexts=["Act"],
        required_attributes=[],
        optional_attributes=[],
        allowed_children=[
            {"name": "Actors", "cardinality": "1..1"},
            {"name": "CatalogReference", "cardinality": "0..1"},
            {"name": "Maneuver", "cardinality": "1..*"},
        ],
        child_order=["Actors", "CatalogReference", "Maneuver"],
        multiplicity={
            "Actors": "1..1",
            "CatalogReference": "0..1",
            "Maneuver": "1..*",
        },
        enum_constraints={},
        source_path="knowledge/raw/schema/OpenSCENARIO.xsd#L1500",
    )
    return KnowledgeBase(records_by_element={"ManeuverGroup": maneuver_group})
