from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

import pytest
from _pytest import tmpdir as pytest_tmpdir

from openscenario_mcp.knowledge.vtd_loader import load_vtd_snapshot, write_vtd_snapshot
from openscenario_mcp.knowledge.vtd_snapshot import build_extractor_manifest
from openscenario_mcp.models import (
    ElementRecord,
    KnowledgeBase,
    VtdAssetRecord,
    VtdKnowledgeBase,
    VtdNameRule,
)

# Pytest creates temp roots/children with a restrictive mode on this Windows sandbox.
# That ACL blocks later file writes inside tmp_path, so create both levels explicitly.
_PYTEST_BASETEMP = Path(r"C:\Users\EDY\.codex\memories") / f"pytest-{uuid4().hex}"
_ORIGINAL_GETBASETEMP = pytest_tmpdir.TempPathFactory.getbasetemp
_SAMPLE_VTD_RUNTIME_ROOT = "D:/wyj/VTD-2020-install/VTD.2020/Runtime"
_SAMPLE_VTD_RELEASE_NAME = "RodDistro_6980_Rod4.6.1"
_SAMPLE_VTD_RELEASE_PREFIX = f"Tools/{_SAMPLE_VTD_RELEASE_NAME}"
_SAMPLE_VTD_RELEASE_ROOT = (
    f"{_SAMPLE_VTD_RUNTIME_ROOT}/Tools/{_SAMPLE_VTD_RELEASE_NAME}"
)


def _safe_getbasetemp(self: pytest_tmpdir.TempPathFactory) -> Path:
    if self._basetemp is not None:
        return self._basetemp

    if self._given_basetemp is None:
        return _ORIGINAL_GETBASETEMP(self)

    basetemp = Path(self._given_basetemp)
    if basetemp.exists():
        shutil.rmtree(basetemp, ignore_errors=True)
    basetemp.mkdir(parents=True, exist_ok=True)
    self._basetemp = basetemp.resolve()
    return self._basetemp


def _safe_mktemp(
    self: pytest_tmpdir.TempPathFactory,
    basename: str,
    numbered: bool = True,
) -> Path:
    basename = self._ensure_relative_to_basetemp(basename)
    if not numbered:
        path = self.getbasetemp() / basename
        path.mkdir()
        return path

    path = self.getbasetemp() / f"{basename}-{uuid4().hex}"
    path.mkdir()
    return path


def pytest_configure(config: pytest.Config) -> None:
    config.option.basetemp = str(_PYTEST_BASETEMP)
    pytest_tmpdir.TempPathFactory.getbasetemp = _safe_getbasetemp
    pytest_tmpdir.TempPathFactory.mktemp = _safe_mktemp


@pytest.fixture
def sample_knowledge_base() -> KnowledgeBase:
    record = ElementRecord(
        element="Storyboard",
        description="Coordinates the scenario flow.",
        parent_contexts=["OpenScenario"],
        required_attributes=[{"name": "name", "type": "string"}],
        optional_attributes=[{"name": "maximumExecutionCount", "type": "unsignedInt"}],
        allowed_children=[
            {"name": "Init", "cardinality": "0..1"},
            {"name": "Story", "cardinality": "1..*"},
        ],
        child_order=["Init", "Story"],
        multiplicity={"Story": "1..*"},
        enum_constraints={},
        source_path="knowledge/raw/docs/storyboard.md",
    )

    return KnowledgeBase(records_by_element={"Storyboard": record})


@pytest.fixture
def fake_validator_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    module_name = f"fake_validator_module_{uuid4().hex}"
    module_path = tmp_path / f"{module_name}.py"
    module_path.write_text(
        "VALIDATION_ERRORS = [\n"
        "    {\n"
        "        'severity': 'error',\n"
        "        'line': 7,\n"
        "        'column': 4,\n"
        "        'message': \"Element 'ManeuverGroup': Missing child element(s). Expected is ( Actors ).\",\n"
        "        'rule_hint': 'Actors',\n"
        "    }\n"
        "]\n\n"
        "def validate(xml: str, schema_version: str):\n"
        "    _ = (xml, schema_version)\n"
        "    return [error.copy() for error in VALIDATION_ERRORS]\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    return module_name


@pytest.fixture
def write_sample_element_record_json(tmp_path: Path) -> Callable[..., Path]:
    def _write(
        *,
        directory: Path | None = None,
        filename: str = "element_record.json",
    ) -> Path:
        target_dir = directory or tmp_path
        target_dir.mkdir(parents=True, exist_ok=True)

        payload = {
            "element": "Storyboard",
            "description": "Coordinates the scenario flow.",
            "parent_contexts": ["OpenScenario"],
            "required_attributes": [{"name": "name", "type": "string"}],
            "optional_attributes": [
                {"name": "maximumExecutionCount", "type": "unsignedInt"}
            ],
            "allowed_children": [
                {"name": "Init", "cardinality": "0..1"},
                {"name": "Story", "cardinality": "1..*"},
            ],
            "child_order": ["Init", "Story"],
            "multiplicity": {"Story": "1..*"},
            "enum_constraints": {},
            "source_path": "knowledge/raw/docs/storyboard.md",
        }

        record_path = target_dir / filename
        record_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return record_path

    return _write


@pytest.fixture
def sample_project_root(
    tmp_path: Path,
    write_sample_element_record_json: Callable[..., Path],
) -> Path:
    elements_dir = tmp_path / "knowledge" / "structured" / "elements"
    write_sample_element_record_json(directory=elements_dir, filename="Storyboard.json")
    _write_sample_vtd_snapshot(tmp_path / "knowledge" / "structured" / "vtd")
    return tmp_path


@pytest.fixture
def sample_vtd_knowledge_base(tmp_path: Path) -> VtdKnowledgeBase:
    snapshot_root = tmp_path / "knowledge" / "structured" / "vtd"
    _write_sample_vtd_snapshot(snapshot_root)
    return load_vtd_snapshot(snapshot_root)


def _write_sample_vtd_snapshot(snapshot_root: Path) -> None:
    shared_cn = _make_vtd_asset(
        asset_id="signal:CN:SharedSignal01",
        asset_kind="signal",
        canonical_name="SharedSignal01",
        filename="SharedSignal01.flt",
        relative_path=(
            f"{_SAMPLE_VTD_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryCN/Signals/"
            "SharedSignal01.flt"
        ),
        source_path=(
            f"{_SAMPLE_VTD_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryCN/SetupFiles/"
            "TT_SIGNALS_ADD_COUNTRYCN.DAT#L1"
        ),
        aliases=["SharedSignalAliasCN"],
        country_codes=["CN"],
        group_path="CN-Signs",
        runtime_family="signal",
    )
    shared_de = _make_vtd_asset(
        asset_id="signal:DE:SharedSignal01",
        asset_kind="signal",
        canonical_name="SharedSignal01",
        filename="SharedSignal01.flt",
        relative_path=(
            f"{_SAMPLE_VTD_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryDE/Signals/"
            "SharedSignal01.flt"
        ),
        source_path=(
            f"{_SAMPLE_VTD_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryDE/SetupFiles/"
            "TT_SIGNALS_ADD_COUNTRYDE.DAT#L1"
        ),
        aliases=["SharedSignalAliasDE"],
        country_codes=["DE"],
        group_path="DE-Signs",
        runtime_family="signal",
    )
    alias_only = _make_vtd_asset(
        asset_id="signal:CN:DifferentSignal01",
        asset_kind="signal",
        canonical_name="DifferentSignal01",
        filename="DifferentSignal01.flt",
        relative_path=(
            f"{_SAMPLE_VTD_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryCN/Signals/"
            "DifferentSignal01.flt"
        ),
        source_path=(
            f"{_SAMPLE_VTD_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryCN/SetupFiles/"
            "TT_SIGNALS_ADD_COUNTRYCN.DAT#L2"
        ),
        aliases=["SharedSignal01"],
        country_codes=["CN"],
        group_path="CN-Signs",
        runtime_family="signal",
    )
    canonical_with_alias = _make_vtd_asset(
        asset_id="signal:CN:CN_Sg101_Gefahrenstelle01",
        asset_kind="signal",
        canonical_name="CN_Sg101_Gefahrenstelle01",
        filename="CN_Sg101_Gefahrenstelle01.flt",
        relative_path=(
            f"{_SAMPLE_VTD_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryCN/Signals/"
            "CN_Sg101_Gefahrenstelle01.flt"
        ),
        source_path=(
            f"{_SAMPLE_VTD_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryCN/SetupFiles/"
            "TT_SIGNALS_ADD_COUNTRYCN.DAT#L3"
        ),
        aliases=["Sg101Gefahrstelle01.flt"],
        country_codes=["CN"],
        group_path="CN-Signs",
        runtime_family="signal",
    )

    write_vtd_snapshot(
        snapshot_root=snapshot_root,
        assets=[shared_cn, shared_de, alias_only, canonical_with_alias],
        rules=[
            _make_vtd_rule(
                name="country-preference-runtime-asset-sharedsignal01-cn",
                rule_kind="country_preference",
                canonical_target="SharedSignal01",
                source_path=shared_cn.source_path,
                asset_kind="signal",
                namespace="runtime_asset",
                country_code="CN",
            ),
            _make_vtd_rule(
                name="country-preference-runtime-asset-sharedsignal01-de",
                rule_kind="country_preference",
                canonical_target="SharedSignal01",
                source_path=shared_de.source_path,
                asset_kind="signal",
                namespace="runtime_asset",
                country_code="DE",
            ),
            _make_vtd_rule(
                name="reserved-scenario-object-sharedsignal01-cn",
                rule_kind="reserved_name",
                canonical_target="SharedSignal01",
                source_path=shared_cn.source_path,
                asset_kind="signal",
                namespace="scenario_object",
                country_code="CN",
            ),
            _make_vtd_rule(
                name="alias-runtime-asset-sg101-cn",
                rule_kind="alias",
                canonical_target="CN_Sg101_Gefahrenstelle01",
                source_path=canonical_with_alias.source_path,
                asset_kind="signal",
                namespace="runtime_asset",
                country_code="CN",
                metadata={"alias": "Sg101Gefahrstelle01.flt"},
            ),
        ],
        runtime_root=_SAMPLE_VTD_RUNTIME_ROOT,
        release_root=_SAMPLE_VTD_RELEASE_ROOT,
        manifest=build_extractor_manifest(),
    )


def _make_vtd_asset(
    *,
    asset_id: str,
    asset_kind: str,
    canonical_name: str,
    filename: str,
    relative_path: str,
    source_path: str,
    aliases: list[str],
    country_codes: list[str],
    group_path: str,
    runtime_family: str,
) -> VtdAssetRecord:
    return VtdAssetRecord(
        asset_id=asset_id,
        asset_kind=asset_kind,
        canonical_name=canonical_name,
        display_name=canonical_name,
        filename=filename,
        relative_path=relative_path,
        source_path=source_path,
        group_path=group_path,
        runtime_family=runtime_family,
        aliases=aliases,
        country_codes=country_codes,
        variant_tags=[],
        metadata={},
    )


def _make_vtd_rule(
    *,
    name: str,
    rule_kind: str,
    canonical_target: str,
    source_path: str,
    asset_kind: str,
    namespace: str,
    country_code: str,
    metadata: dict[str, object] | None = None,
) -> VtdNameRule:
    return VtdNameRule(
        name=name,
        rule_kind=rule_kind,
        severity="info",
        canonical_target=canonical_target,
        asset_kind=asset_kind,
        reason="test rule",
        source_path=source_path,
        scope={
            "namespace": namespace,
            "asset_kind": asset_kind,
            "country_code": country_code,
        },
        metadata={} if metadata is None else metadata,
    )
