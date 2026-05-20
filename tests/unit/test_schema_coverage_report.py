import shutil
from pathlib import Path

from scripts.report_schema_coverage import build_schema_coverage_report


def test_schema_coverage_report_reports_current_full_baseline() -> None:
    report = build_schema_coverage_report()

    assert report["xsd_element_count"] == 302
    assert "OpenSCENARIO" in report["structured_elements"]
    assert report["structured_element_count"] == 301
    assert report["missing_elements"] == []
    assert report["extra_structured_elements"] == []


def test_schema_coverage_report_reports_dangling_children_and_metadata_gaps(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    schema_dir = project_root / "knowledge/raw/schema"
    elements_dir = project_root / "knowledge/structured/elements"
    schema_dir.mkdir(parents=True)
    elements_dir.mkdir(parents=True)

    shutil.copy(
        "knowledge/raw/schema/OpenSCENARIO.xsd",
        schema_dir / "OpenSCENARIO.xsd",
    )

    (elements_dir / "Broken.json").write_text(
        '{"description":"broken payload"}',
        encoding="utf-8",
    )
    (elements_dir / "OpenSCENARIO.json").write_text(
        """
        {
          "element": "OpenSCENARIO",
          "description": "Root",
          "parent_contexts": [],
          "required_attributes": [],
          "optional_attributes": [],
          "allowed_children": [{"name": "MissingChild", "cardinality": "1..1"}],
          "child_order": ["MissingChild"],
          "multiplicity": {"MissingChild": "1..1"},
          "enum_constraints": {}
        }
        """.strip(),
        encoding="utf-8",
    )

    report = build_schema_coverage_report(project_root)

    assert {"element": "Broken", "issue": "missing_element"} in report[
        "records_missing_required_metadata"
    ]
    assert {"element": "OpenSCENARIO", "issue": "missing_source_path"} in report[
        "records_missing_required_metadata"
    ]
    assert {"element": "OpenSCENARIO", "child": "MissingChild"} in report[
        "dangling_child_references"
    ]


def test_no_xsd_elements_are_missing_from_structured_records() -> None:
    report = build_schema_coverage_report()

    assert report["missing_elements"] == []
    assert report["extra_structured_elements"] == []
    assert report["dangling_child_references"] == []
    assert report["records_missing_required_metadata"] == []
