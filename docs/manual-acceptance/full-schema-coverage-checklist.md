# Full Schema Coverage Checklist

Use this checklist after the automated suite is green.

- Confirm `knowledge/structured/schema_scope.json` exists and reports `mode: full`.
- Confirm `knowledge/structured/coverage_report.json` reports zero `missing_elements`.
- Confirm the five domain manifest files exist under `knowledge/structured/manifests/`.
- Run `py -3.14 scripts/report_schema_coverage.py` and verify it exits cleanly.
- Run the full targeted pytest suite for full-schema coverage.
- Confirm `retrieve_spec` still returns source-linked hits for elements, attributes, and errors.
- Confirm `get_element_schema` still returns the extended metadata fields:
  `content_model_kind`, `child_groups`, `semantic_constraints`, `contextual_variants`.
- Confirm `validate_xml` and `explain_validation_errors` still work on the existing integration fixtures.
- Confirm benchmark asset tests and benchmark result tests still pass.
- Spot-check one record from each manifest domain for reasonable descriptions and source anchors.
