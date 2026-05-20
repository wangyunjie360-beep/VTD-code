from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from openscenario_mcp.knowledge.vtd_loader import (
    build_vtd_knowledge_snapshot,
    load_vtd_semantic_snapshot,
    load_vtd_snapshot,
    write_vtd_snapshot,
)
from openscenario_mcp.knowledge.vtd_snapshot import build_extractor_manifest
from openscenario_mcp.models import VtdAssetRecord, VtdNameRule

FIXTURE_RELEASE_ROOT = Path("tests/fixtures/vtd_runtime")
EXPECTED_RUNTIME_ROOT = "D:/wyj/VTD-2020-install/VTD.2020/Runtime"
EXPECTED_RELEASE_NAME = "RodDistro_6980_Rod4.6.1"
EXPECTED_RELEASE_PREFIX = f"Tools/{EXPECTED_RELEASE_NAME}"
EXPECTED_RELEASE_ROOT = (
    f"{EXPECTED_RUNTIME_ROOT}/Tools/{EXPECTED_RELEASE_NAME}"
)


def test_load_vtd_snapshot_reads_assets_and_rules(tmp_path: Path) -> None:
    snapshot_root = tmp_path / "knowledge" / "structured" / "vtd"
    signal = _make_asset(
        asset_id="signal:CN:CN_Sg101_Gefahrenstelle01",
        asset_kind="signal",
        canonical_name="CN_Sg101_Gefahrenstelle01",
        filename="CN_Sg101_Gefahrenstelle01.flt",
        relative_path=(
            f"{EXPECTED_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryCN/Signals/"
            "CN_Sg101_Gefahrenstelle01.flt"
        ),
        source_path=(
            f"{EXPECTED_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryCN/SetupFiles/"
            "TT_SIGNALS_ADD_COUNTRYCN.DAT#L4"
        ),
        country_codes=["CN"],
        aliases=["Sg101Gefahrstelle01.flt"],
        group_path="CN-Signs-S",
        runtime_family="signal",
    )
    alias_rule = _make_rule(
        name="alias-runtime-asset-signal-cn-sg101-01",
        rule_kind="alias",
        canonical_target=signal.canonical_name,
        source_path=signal.source_path,
        asset_kind="signal",
        country_code="CN",
        metadata={"alias": "Sg101Gefahrstelle01.flt"},
    )

    write_vtd_snapshot(
        snapshot_root=snapshot_root,
        assets=[signal],
        rules=[alias_rule],
        runtime_root=EXPECTED_RUNTIME_ROOT,
        release_root=EXPECTED_RELEASE_ROOT,
        manifest=build_extractor_manifest(),
    )

    snapshot = load_vtd_snapshot(snapshot_root)

    assert "CN_Sg101_Gefahrenstelle01" in snapshot.assets_by_canonical_name
    assert snapshot.assets_by_id[signal.asset_id].relative_path == signal.relative_path
    assert snapshot.assets_by_canonical_name["CN_Sg101_Gefahrenstelle01"][0].asset_id == signal.asset_id
    assert alias_rule.name in snapshot.rules_by_name
    assert snapshot.runtime_root == EXPECTED_RUNTIME_ROOT
    assert snapshot.metadata["summary"]["asset_counts"]["signals"] == 1
    assert snapshot.metadata["summary"]["rule_counts"]["aliases"] == 1
    assert snapshot.metadata["summary"]["release_name"] == EXPECTED_RELEASE_NAME
    assert snapshot.sources[0].id == "vtd-runtime"
    assert snapshot.sources[0].kind == "runtime"
    assert snapshot.sources[0].path == "knowledge/structured/vtd"


def test_load_vtd_snapshot_reads_country_taxonomy_and_name_policies(
    tmp_path: Path,
) -> None:
    snapshot_root = tmp_path / "knowledge" / "structured" / "vtd"
    signal = _make_asset(
        asset_id="signal:USA:SharedSignal01",
        asset_kind="signal",
        canonical_name="SharedSignal01",
        filename="SharedSignal01.flt",
        relative_path=(
            f"{EXPECTED_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryUS/Signals/"
            "SharedSignal01.flt"
        ),
        source_path=(
            f"{EXPECTED_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryUS/SetupFiles/"
            "TT_SIGNALS_ADD_COUNTRYUS.DAT#L1"
        ),
        country_codes=["USA"],
        aliases=["SharedSignalAliasUS"],
        group_path="US-Signs",
        runtime_family="signal",
    )
    soft_rule = _make_rule(
        name="reserved-scenario-object-sharedsignal01-us",
        rule_kind="reserved_name",
        canonical_target=signal.canonical_name,
        source_path=signal.source_path,
        asset_kind="signal",
        country_code="USA",
        namespace="scenario_object",
        metadata={"match_name": "SharedSignal01"},
    )

    write_vtd_snapshot(
        snapshot_root=snapshot_root,
        assets=[signal],
        rules=[soft_rule],
        runtime_root=EXPECTED_RUNTIME_ROOT,
        release_root=EXPECTED_RELEASE_ROOT,
        manifest=build_extractor_manifest(),
    )

    snapshot = load_vtd_snapshot(snapshot_root)

    assert snapshot.metadata["country_taxonomy"]["alias_to_country"]["usa"] == "US"
    assert any(
        policy["namespace"] == "scenario_object"
        and policy["match_name"] == "SharedSignal01"
        and policy["country_scope"] == "US"
        for policy in snapshot.metadata["name_policies"]
    )
    assert snapshot.metadata["summary"]["semantic_counts"]["name-policies"] >= 1


def test_load_vtd_semantic_snapshot_reads_written_family_variant_and_provenance(
    tmp_path: Path,
) -> None:
    snapshot_root = tmp_path / "knowledge" / "structured" / "vtd"
    cn_signal = _make_asset(
        asset_id="signal:CN:SharedSignal01",
        asset_kind="signal",
        canonical_name="SharedSignal01",
        filename="SharedSignal01.flt",
        relative_path=(
            f"{EXPECTED_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryCN/Signals/"
            "SharedSignal01.flt"
        ),
        source_path=(
            f"{EXPECTED_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryCN/SetupFiles/"
            "TT_SIGNALS_ADD_COUNTRYCN.DAT#L1"
        ),
        country_codes=["CN"],
        aliases=["SharedSignalAliasCN"],
        group_path="CN-Signs",
        runtime_family="signal",
    )
    de_signal = _make_asset(
        asset_id="signal:DE:SharedSignal01",
        asset_kind="signal",
        canonical_name="SharedSignal01",
        filename="SharedSignal01.flt",
        relative_path=(
            f"{EXPECTED_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryDE/Signals/"
            "SharedSignal01.flt"
        ),
        source_path=(
            f"{EXPECTED_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryDE/SetupFiles/"
            "TT_SIGNALS_ADD_COUNTRYDE.DAT#L1"
        ),
        country_codes=["DE"],
        aliases=["SharedSignalAliasDE"],
        group_path="DE-Signs",
        runtime_family="signal",
    )
    alias_rule = _make_rule(
        name="alias-runtime-asset-signal-cn-sharedsignal01",
        rule_kind="alias",
        canonical_target=cn_signal.canonical_name,
        source_path=cn_signal.source_path,
        asset_kind="signal",
        country_code="CN",
        metadata={"alias": "SharedSignalAliasCN"},
    )
    soft_rule = _make_rule(
        name="reserved-scenario-object-sharedsignal01-cn",
        rule_kind="reserved_name",
        canonical_target=cn_signal.canonical_name,
        source_path=cn_signal.source_path,
        asset_kind="signal",
        country_code="CN",
        namespace="scenario_object",
        metadata={"match_name": "SharedSignal01"},
    )

    write_vtd_snapshot(
        snapshot_root=snapshot_root,
        assets=[cn_signal, de_signal],
        rules=[alias_rule, soft_rule],
        runtime_root=EXPECTED_RUNTIME_ROOT,
        release_root=EXPECTED_RELEASE_ROOT,
        manifest=build_extractor_manifest(),
    )

    semantic_snapshot = load_vtd_semantic_snapshot(snapshot_root)
    family = semantic_snapshot.families_by_id["signal-family:sharedsignal01"]

    assert len(family.variant_ids) == 2
    assert family.preferred_variant_id in family.variant_ids
    assert semantic_snapshot.variants_by_id[family.variant_ids[0]].referencable_as
    assert semantic_snapshot.name_policies_by_id
    assert semantic_snapshot.metadata["source_provenance"]


def test_write_vtd_snapshot_emits_deterministic_jsonl_and_summary(
    tmp_path: Path,
) -> None:
    snapshot_root = tmp_path / "knowledge" / "structured" / "vtd"
    late_signal = _make_asset(
        asset_id="signal:US:ZetaSignal",
        asset_kind="signal",
        canonical_name="ZetaSignal",
        filename="ZetaSignal.flt",
        relative_path=(
            f"{EXPECTED_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryUS/Signals/"
            "ZetaSignal.flt"
        ),
        source_path=(
            f"{EXPECTED_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryUS/SetupFiles/"
            "TT_SIGNALS_ADD_COUNTRYUS.DAT#L7"
        ),
        country_codes=["US"],
        group_path="US-Signs",
        runtime_family="signal",
    )
    early_signal = _make_asset(
        asset_id="signal:CN:AlphaSignal",
        asset_kind="signal",
        canonical_name="AlphaSignal",
        filename="AlphaSignal.flt",
        relative_path=(
            f"{EXPECTED_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryCN/Signals/"
            "AlphaSignal.flt"
        ),
        source_path=(
            f"{EXPECTED_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryCN/SetupFiles/"
            "TT_SIGNALS_ADD_COUNTRYCN.DAT#L3"
        ),
        country_codes=["CN"],
        group_path="CN-Signs",
        runtime_family="signal",
    )
    late_alias = _make_rule(
        name="alias-runtime-asset-signal-us-zetasignal",
        rule_kind="alias",
        canonical_target=late_signal.canonical_name,
        source_path=late_signal.source_path,
        asset_kind="signal",
        country_code="US",
    )
    early_alias = _make_rule(
        name="alias-runtime-asset-signal-cn-alphasignal",
        rule_kind="alias",
        canonical_target=early_signal.canonical_name,
        source_path=early_signal.source_path,
        asset_kind="signal",
        country_code="CN",
    )

    summary = write_vtd_snapshot(
        snapshot_root=snapshot_root,
        assets=[late_signal, early_signal],
        rules=[late_alias, early_alias],
        runtime_root=EXPECTED_RUNTIME_ROOT,
        release_root=EXPECTED_RELEASE_ROOT,
        manifest=build_extractor_manifest(),
    )

    signal_lines = (
        snapshot_root / "assets" / "signals.jsonl"
    ).read_text(encoding="utf-8").splitlines()
    alias_lines = (
        snapshot_root / "rules" / "aliases.jsonl"
    ).read_text(encoding="utf-8").splitlines()

    assert [json.loads(line)["canonical_name"] for line in signal_lines] == [
        "AlphaSignal",
        "ZetaSignal",
    ]
    assert [json.loads(line)["name"] for line in alias_lines] == [
        "alias-runtime-asset-signal-cn-alphasignal",
        "alias-runtime-asset-signal-us-zetasignal",
    ]
    assert summary["asset_counts"]["signals"] == 2
    assert summary["rule_counts"]["aliases"] == 2
    assert summary["sources"] == [
        {
            "id": "vtd-runtime",
            "kind": "runtime",
            "path": "knowledge/structured/vtd",
        }
    ]


def test_load_vtd_snapshot_keeps_all_assets_for_shared_canonical_name(
    tmp_path: Path,
) -> None:
    snapshot_root = tmp_path / "knowledge" / "structured" / "vtd"
    cn_signal = _make_asset(
        asset_id="signal:CN:SharedSignal01",
        asset_kind="signal",
        canonical_name="SharedSignal01",
        filename="SharedSignal01.flt",
        relative_path=(
            f"{EXPECTED_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryCN/Signals/"
            "SharedSignal01.flt"
        ),
        source_path=(
            f"{EXPECTED_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryCN/SetupFiles/"
            "TT_SIGNALS_ADD_COUNTRYCN.DAT#L1"
        ),
        country_codes=["CN"],
        group_path="CN-Signs",
        runtime_family="signal",
    )
    de_signal = _make_asset(
        asset_id="signal:DE:SharedSignal01",
        asset_kind="signal",
        canonical_name="SharedSignal01",
        filename="SharedSignal01.flt",
        relative_path=(
            f"{EXPECTED_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryDE/Signals/"
            "SharedSignal01.flt"
        ),
        source_path=(
            f"{EXPECTED_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryDE/SetupFiles/"
            "TT_SIGNALS_ADD_COUNTRYDE.DAT#L1"
        ),
        country_codes=["DE"],
        group_path="DE-Signs",
        runtime_family="signal",
    )

    write_vtd_snapshot(
        snapshot_root=snapshot_root,
        assets=[cn_signal, de_signal],
        rules=[],
        runtime_root=EXPECTED_RUNTIME_ROOT,
        release_root=EXPECTED_RELEASE_ROOT,
        manifest=build_extractor_manifest(),
    )

    snapshot = load_vtd_snapshot(snapshot_root)

    assert [asset.asset_id for asset in snapshot.assets_by_canonical_name["SharedSignal01"]] == [
        "signal:CN:SharedSignal01",
        "signal:DE:SharedSignal01",
    ]
    assert snapshot.metadata["canonical_collisions"]["SharedSignal01"] == [
        "signal:CN:SharedSignal01",
        "signal:DE:SharedSignal01",
    ]


def test_build_vtd_knowledge_snapshot_invalid_runtime_layout_boundary(
    tmp_path: Path,
) -> None:
    runtime_root = tmp_path / "Runtime"
    runtime_root.mkdir(parents=True)

    with pytest.raises(ValueError, match="VTD\\.2020"):
        build_vtd_knowledge_snapshot(runtime_root, snapshot_root=tmp_path / "snapshot")


def test_build_vtd_knowledge_snapshot_invalid_release_boundary(
    tmp_path: Path,
) -> None:
    runtime_root = tmp_path / "VTD.2020" / "Runtime"
    (runtime_root / "Tools" / "RodDistro_1111_Rod4.6.1").mkdir(parents=True)

    with pytest.raises(ValueError, match=EXPECTED_RELEASE_NAME):
        build_vtd_knowledge_snapshot(runtime_root, snapshot_root=tmp_path / "snapshot")


def test_write_vtd_snapshot_invalid_manifest_allowlist_boundary(
    tmp_path: Path,
) -> None:
    snapshot_root = tmp_path / "knowledge" / "structured" / "vtd"
    invalid_manifest = build_extractor_manifest()
    invalid_manifest["allowlist"].append(
        {
            "match": "../outside.txt",
            "match_type": "file",
            "collector": "escape",
        }
    )

    with pytest.raises(ValueError, match=r"\.\./outside\.txt"):
        write_vtd_snapshot(
            snapshot_root=snapshot_root,
            assets=[],
            rules=[],
            runtime_root=EXPECTED_RUNTIME_ROOT,
            release_root=EXPECTED_RELEASE_ROOT,
            manifest=invalid_manifest,
        )


def test_write_vtd_snapshot_invalid_out_of_scope_source_path_boundary(
    tmp_path: Path,
) -> None:
    snapshot_root = tmp_path / "knowledge" / "structured" / "vtd"
    invalid_asset = _make_asset(
        asset_id="model:OutOfScopePbrStyle",
        asset_kind="model",
        canonical_name="OutOfScopePbrStyle",
        filename="OutOfScopePbrStyle.osgb",
        relative_path="VisualLib/Models/Props/OutOfScopePbrStyle.osgb",
        source_path="Tools/pbr_styles.xml",
        group_path="VisualLib/Models/Props",
        runtime_family="model",
    )

    with pytest.raises(ValueError, match="Tools/pbr_styles\\.xml"):
        write_vtd_snapshot(
            snapshot_root=snapshot_root,
            assets=[invalid_asset],
            rules=[],
            runtime_root=EXPECTED_RUNTIME_ROOT,
            release_root=EXPECTED_RELEASE_ROOT,
            manifest=build_extractor_manifest(),
        )


def test_build_vtd_knowledge_snapshot_boundary_ignores_in_tree_out_of_scope_files(
    tmp_path: Path,
) -> None:
    runtime_root = _copy_fixture_into_expected_runtime_layout(tmp_path)
    release_root = runtime_root / "Tools" / EXPECTED_RELEASE_NAME
    _write_text(
        release_root / "Tools" / "pbr_styles.xml",
        "<PBRObjects><PBRObject pbr=\"IgnoredByBoundary\" /></PBRObjects>\n",
    )
    _write_text(
        release_root / "DefaultProject" / "Config" / "RocoConfigGermany.xml",
        "<Config />\n",
    )

    summary = build_vtd_knowledge_snapshot(
        runtime_root,
        snapshot_root=tmp_path / "knowledge" / "structured" / "vtd",
    )
    snapshot = load_vtd_snapshot(tmp_path / "knowledge" / "structured" / "vtd")

    source_paths = {asset.source_path for asset in snapshot.assets_by_id.values()}

    assert f"{EXPECTED_RELEASE_PREFIX}/Tools/pbr_styles.xml" not in source_paths
    assert (
        f"{EXPECTED_RELEASE_PREFIX}/DefaultProject/Config/RocoConfigGermany.xml"
        not in source_paths
    )
    assert summary["asset_counts"]["signals"] >= 1
    assert summary["asset_counts"]["models"] >= 1


def test_build_vtd_knowledge_snapshot_reads_runtime_root_addons_outside_release_tree(
    tmp_path: Path,
) -> None:
    runtime_root = _copy_fixture_into_expected_runtime_layout(tmp_path)
    release_root = runtime_root / "Tools" / EXPECTED_RELEASE_NAME
    shutil.rmtree(release_root / "AddOns")
    _write_text(
        runtime_root / "AddOns" / "OdrGateway" / "odrGateway.xml",
        (
            "<Addon>\n"
            "  <RDB />\n"
            "  <Config />\n"
            "  <Debug />\n"
            "</Addon>\n"
        ),
    )

    summary = build_vtd_knowledge_snapshot(
        runtime_root,
        snapshot_root=tmp_path / "knowledge" / "structured" / "vtd",
    )
    snapshot = load_vtd_snapshot(tmp_path / "knowledge" / "structured" / "vtd")

    addon_paths = {
        asset.relative_path
        for asset in snapshot.assets_by_id.values()
        if asset.asset_kind == "addon"
    }

    assert summary["asset_counts"]["addons"] == 1
    assert addon_paths == {"AddOns/OdrGateway/odrGateway.xml"}
    assert snapshot.runtime_root == runtime_root.as_posix()


def test_build_vtd_knowledge_snapshot_uses_runtime_root_relative_paths(
    tmp_path: Path,
) -> None:
    runtime_root = _copy_fixture_into_expected_runtime_layout(tmp_path)

    build_vtd_knowledge_snapshot(
        runtime_root,
        snapshot_root=tmp_path / "knowledge" / "structured" / "vtd",
    )
    snapshot = load_vtd_snapshot(tmp_path / "knowledge" / "structured" / "vtd")
    signal = snapshot.assets_by_canonical_name["CN_Sg101_Gefahrenstelle01"][0]
    addon = snapshot.assets_by_canonical_name["odrGateway"][0]

    assert snapshot.runtime_root == runtime_root.as_posix()
    assert signal.relative_path.startswith(
        f"{EXPECTED_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryCN/Signals/"
    )
    assert signal.source_path.startswith(
        f"{EXPECTED_RELEASE_PREFIX}/VisualLib/Models/AddOns/CountryCN/SetupFiles/"
    )
    assert addon.relative_path == "AddOns/OdrGateway/odrGateway.xml"
    assert addon.source_path == "AddOns/OdrGateway/odrGateway.xml"
    assert (Path(snapshot.runtime_root) / signal.relative_path).is_file()
    assert (Path(snapshot.runtime_root) / addon.relative_path).is_file()


def test_build_vtd_knowledge_snapshot_materializes_reserved_name_rules_and_semantics(
    tmp_path: Path,
) -> None:
    runtime_root = _copy_fixture_into_expected_runtime_layout(tmp_path)
    snapshot_root = tmp_path / "knowledge" / "structured" / "vtd"

    summary = build_vtd_knowledge_snapshot(
        runtime_root,
        snapshot_root=snapshot_root,
    )
    snapshot = load_vtd_snapshot(snapshot_root)

    assert summary["rule_counts"]["reserved-names"] > 0
    assert summary["semantic_counts"]["name-policies"] > 0
    assert (snapshot_root / "semantic" / "country-taxonomy.json").is_file()
    assert (snapshot_root / "semantic" / "name-policies.jsonl").is_file()
    assert (snapshot_root / "semantic" / "asset-families.jsonl").is_file()
    assert (snapshot_root / "semantic" / "asset-variants.jsonl").is_file()
    assert (snapshot_root / "semantic" / "source-provenance.jsonl").is_file()
    assert snapshot.metadata["name_policies"]
    assert snapshot.metadata["country_taxonomy"]["countries"]


def _copy_fixture_into_expected_runtime_layout(tmp_path: Path) -> Path:
    runtime_root = tmp_path / "VTD.2020" / "Runtime"
    release_root = runtime_root / "Tools" / EXPECTED_RELEASE_NAME
    shutil.copytree(FIXTURE_RELEASE_ROOT, release_root, dirs_exist_ok=True)
    shutil.copytree(
        FIXTURE_RELEASE_ROOT / "AddOns",
        runtime_root / "AddOns",
        dirs_exist_ok=True,
    )
    return runtime_root


def _make_asset(
    *,
    asset_id: str,
    asset_kind: str,
    canonical_name: str,
    filename: str,
    relative_path: str,
    source_path: str,
    group_path: str,
    runtime_family: str,
    aliases: list[str] | None = None,
    country_codes: list[str] | None = None,
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
        aliases=[] if aliases is None else aliases,
        country_codes=[] if country_codes is None else country_codes,
        variant_tags=[],
        metadata={},
    )


def _make_rule(
    *,
    name: str,
    rule_kind: str,
    canonical_target: str,
    source_path: str,
    asset_kind: str,
    country_code: str,
    namespace: str = "runtime_asset",
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


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
