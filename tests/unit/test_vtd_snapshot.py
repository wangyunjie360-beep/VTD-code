from __future__ import annotations

import json
from pathlib import Path

from openscenario_mcp.knowledge.vtd_snapshot import (
    build_asset_buckets,
    build_asset_records,
    build_country_taxonomy,
    build_extractor_manifest,
    build_name_policies,
    build_name_rules,
    build_reserved_name_candidates,
)
from openscenario_mcp.models import VtdAssetRecord

FIXTURE_ROOT = Path("tests/fixtures/vtd_runtime")
EXTRACTOR_MANIFEST_PATH = Path("knowledge/structured/vtd/extractor_manifest.json")


def test_build_asset_records_merges_dat_xml_and_directory_scanned_assets() -> None:
    assets = build_asset_records(FIXTURE_ROOT)
    signal = _find_asset(
        assets,
        asset_kind="signal",
        canonical_name="CN_Sg101_Gefahrenstelle01",
        country_code="CN",
    )
    assert signal.relative_path == (
        "VisualLib/Models/AddOns/CountryCN/Signals/CN_Sg101_Gefahrenstelle01.flt"
    )
    assert signal.source_path == (
        "VisualLib/Models/AddOns/CountryCN/SetupFiles/TT_SIGNALS_ADD_COUNTRYCN.DAT#L4"
    )
    assert signal.aliases == ["Sg101Gefahrstelle01.flt"]
    assert signal.country_codes == ["CN"]

    decal = _find_asset(
        assets,
        asset_kind="decal",
        canonical_name="RdMiscRoadDamagePatch01",
    )
    assert decal.relative_path == (
        "DefaultProject/Config/decalScatterConfig01.xml"
    )
    assert decal.metadata["targettexture"] == "standard"

    addon = _find_asset(assets, asset_kind="addon", canonical_name="odrGateway")
    assert addon.relative_path == "AddOns/OdrGateway/odrGateway.xml"
    assert addon.metadata["top_level_elements"] == ["RDB", "Config", "Debug"]

    style = _find_asset(assets, asset_kind="style", canonical_name="TxRoadStandard")
    assert style.relative_path == (
        "VisualLib/Styles/VTL/Full/TexturePool/TxRoadStandard.rgb"
    )


def test_build_asset_records_prefers_real_models_pbr_path_for_pbr_object_mapping(
    tmp_path: Path,
) -> None:
    runtime_root = tmp_path / "runtime"
    _write_runtime_file(
        runtime_root,
        "Tools/pbr_objects.xml",
        (
            "<PBRObjects>\n"
            '  <PBRObject pbr="Bld_Ind_Storage_Reg05_08a_PBR" />\n'
            "</PBRObjects>\n"
        ),
    )
    _write_runtime_file(
        runtime_root,
        "VisualLib/ModelsPBR/Props/Bld_Ind_Storage_Reg05_08a_PBR.osgb",
        "",
    )

    assets = build_asset_records(runtime_root)
    pbr_model = _find_asset(
        assets,
        asset_kind="model",
        canonical_name="Bld_Ind_Storage_Reg05_08a_PBR",
    )
    assert pbr_model.relative_path == (
        "VisualLib/ModelsPBR/Props/Bld_Ind_Storage_Reg05_08a_PBR.osgb"
    )
    assert pbr_model.source_path == "Tools/pbr_objects.xml"


def test_build_asset_records_merges_pbr_usa_code_into_countryus_scan_path(
    tmp_path: Path,
) -> None:
    runtime_root = tmp_path / "runtime"
    _write_runtime_file(
        runtime_root,
        "Tools/pbr_objects.xml",
        (
            "<PBRObjects>\n"
            '  <PBRObject pbr="US_TestPbrAsset" cc="USA" />\n'
            "</PBRObjects>\n"
        ),
    )
    _write_runtime_file(
        runtime_root,
        "VisualLib/ModelsPBR/AddOns/CountryUS/Props/US_TestPbrAsset.osgb",
        "",
    )

    assets = build_asset_records(runtime_root)
    matching_models = [
        asset
        for asset in assets
        if asset.asset_kind == "model" and asset.canonical_name == "US_TestPbrAsset"
    ]
    assert len(matching_models) == 1
    pbr_model = matching_models[0]

    assert pbr_model.relative_path == (
        "VisualLib/ModelsPBR/AddOns/CountryUS/Props/US_TestPbrAsset.osgb"
    )
    assert pbr_model.source_path == "Tools/pbr_objects.xml"
    assert pbr_model.country_codes == ["US"]


def test_build_asset_records_keeps_same_canonical_from_different_countries_separate(
    tmp_path: Path,
) -> None:
    runtime_root = tmp_path / "runtime"
    _write_runtime_file(
        runtime_root,
        "VisualLib/Models/AddOns/CountryCN/SetupFiles/TT_SIGNALS_ADD_COUNTRYCN.DAT",
        (
            "SIGDEF SharedSignalAliasCN.flt\tSharedSignal01\tSharedSignal01.flt\t0.30"
            "\t0.62\tSTATIC\tSTATIC\t101\t-1\t-1\tVisualLib/Models/AddOns/"
            "CountryCN/Icons/SharedSignal01.xpm\tCN-Signs-S\t-1\t-1.00\t0\t"
            "none\t0.85\n"
        ),
    )
    _write_runtime_file(
        runtime_root,
        "VisualLib/Models/AddOns/CountryDE/SetupFiles/TT_SIGNALS_ADD_COUNTRYDE.DAT",
        (
            "SIGDEF SharedSignalAliasDE.flt\tSharedSignal01\tSharedSignal01.flt\t0.30"
            "\t0.62\tSTATIC\tSTATIC\t101\t-1\t-1\tVisualLib/Models/AddOns/"
            "CountryDE/Icons/SharedSignal01.xpm\tDE-Signs-S\t-1\t-1.00\t0\t"
            "none\t0.85\n"
        ),
    )
    _write_runtime_file(
        runtime_root,
        "VisualLib/Models/AddOns/CountryCN/Signals/SharedSignal01.flt",
        "",
    )
    _write_runtime_file(
        runtime_root,
        "VisualLib/Models/AddOns/CountryDE/Signals/SharedSignal01.flt",
        "",
    )

    assets = build_asset_records(runtime_root)
    matching_assets = [
        asset
        for asset in assets
        if asset.asset_kind == "signal" and asset.canonical_name == "SharedSignal01"
    ]

    assert len(matching_assets) == 2
    cn_asset = _find_asset(
        matching_assets,
        asset_kind="signal",
        canonical_name="SharedSignal01",
        country_code="CN",
    )
    de_asset = _find_asset(
        matching_assets,
        asset_kind="signal",
        canonical_name="SharedSignal01",
        country_code="DE",
    )
    assert cn_asset.asset_id != de_asset.asset_id
    assert cn_asset.relative_path == (
        "VisualLib/Models/AddOns/CountryCN/Signals/SharedSignal01.flt"
    )
    assert de_asset.relative_path == (
        "VisualLib/Models/AddOns/CountryDE/Signals/SharedSignal01.flt"
    )
    assert cn_asset.source_path == (
        "VisualLib/Models/AddOns/CountryCN/SetupFiles/TT_SIGNALS_ADD_COUNTRYCN.DAT#L1"
    )
    assert de_asset.source_path == (
        "VisualLib/Models/AddOns/CountryDE/SetupFiles/TT_SIGNALS_ADD_COUNTRYDE.DAT#L1"
    )


def test_build_asset_records_does_not_fallback_to_wrong_country_scan_path(
    tmp_path: Path,
) -> None:
    runtime_root = tmp_path / "runtime"
    _write_runtime_file(
        runtime_root,
        "VisualLib/Models/AddOns/CountryFR/SetupFiles/TT_SIGNALS_ADD_COUNTRYFR.DAT",
        (
            "SIGDEF SharedSignalAliasFR.flt\tSharedSignal01\tSharedSignal01.flt\t0.30"
            "\t0.62\tSTATIC\tSTATIC\t101\t-1\t-1\tVisualLib/Models/AddOns/"
            "CountryFR/Icons/SharedSignal01.xpm\tFR-Signs-S\t-1\t-1.00\t0\t"
            "none\t0.85\n"
        ),
    )
    _write_runtime_file(
        runtime_root,
        "VisualLib/Models/AddOns/CountryDE/Signals/SharedSignal01.flt",
        "",
    )

    assets = build_asset_records(runtime_root)
    fr_asset = _find_asset(
        assets,
        asset_kind="signal",
        canonical_name="SharedSignal01",
        country_code="FR",
    )

    assert fr_asset.relative_path == ""
    assert fr_asset.source_path == (
        "VisualLib/Models/AddOns/CountryFR/SetupFiles/TT_SIGNALS_ADD_COUNTRYFR.DAT#L1"
    )


def test_build_asset_records_merges_external_dat_with_extmisc_scan_and_consumes_model(
    tmp_path: Path,
) -> None:
    runtime_root = tmp_path / "runtime"
    _write_runtime_file(
        runtime_root,
        "VisualLib/Models/AddOns/CountryCN/SetupFiles/TT_EXTERNALS_ADD_COUNTRYCN.DAT",
        (
            "EXTDEF MiscSpeaker01\t0.16\t0.32\tMiscSpeaker01.flt\t"
            "VisualLib/Models/AddOns/CountryCN/Icons/MiscSpeaker01.xpm\t0.00\t0.00\t"
            "0.03\tCN/Roadside/Audio\t0.17\tobstacle\n"
        ),
    )
    _write_runtime_file(
        runtime_root,
        "VisualLib/Models/AddOns/CountryCN/ExtMisc/MiscSpeaker01.flt",
        "",
    )

    assets = build_asset_records(runtime_root)
    external_asset = _find_asset(
        assets,
        asset_kind="external",
        canonical_name="MiscSpeaker01",
        country_code="CN",
    )

    assert external_asset.relative_path == (
        "VisualLib/Models/AddOns/CountryCN/ExtMisc/MiscSpeaker01.flt"
    )
    assert external_asset.source_path == (
        "VisualLib/Models/AddOns/CountryCN/SetupFiles/TT_EXTERNALS_ADD_COUNTRYCN.DAT#L1"
    )
    assert not any(
        asset.asset_kind == "model" and asset.canonical_name == "MiscSpeaker01"
        for asset in assets
    )


def test_build_asset_records_external_merge_suppresses_remaining_model_overlap(
    tmp_path: Path,
) -> None:
    runtime_root = tmp_path / "runtime"
    _write_runtime_file(
        runtime_root,
        "VisualLib/Models/AddOns/Legacy2018/SetupFiles/TT_EXTERNALS_ADD_LEGACY2018.DAT",
        (
            "EXTDEF BldTower01\t0.16\t0.32\tBldTower01.flt\t"
            "VisualLib/Models/AddOns/Legacy2018/Icons/BldTower01.xpm\t0.00\t0.00\t"
            "0.03\tLegacy/Buildings\t0.17\tobstacle\n"
        ),
    )
    _write_runtime_file(
        runtime_root,
        "VisualLib/Models/AddOns/Legacy2018/ExtBld/BldTower01.flt",
        "",
    )
    _write_runtime_file(
        runtime_root,
        "VisualLib/Models/AddOns/Legacy2018/BldTower01.flt",
        "",
    )

    assets = build_asset_records(runtime_root)
    external_asset = _find_asset_any_country(
        assets,
        asset_kind="external",
        canonical_name="BldTower01",
    )

    assert external_asset.relative_path in {
        "VisualLib/Models/AddOns/Legacy2018/ExtBld/BldTower01.flt",
        "VisualLib/Models/AddOns/Legacy2018/BldTower01.flt",
    }
    assert not any(
        asset.asset_kind == "model" and asset.canonical_name == "BldTower01"
        for asset in assets
    )


def test_build_name_rule_marks_exact_same_namespace_collision_as_high() -> None:
    rules = build_name_rules(
        assets=[_make_asset(canonical_name="CN_Sg101_Gefahrenstelle01")],
        candidate_names=[("CN_Sg101_Gefahrenstelle01", "runtime_asset", "signal", "CN")],
    )

    assert rules[0].severity == "high"
    assert rules[0].scope == {
        "namespace": "runtime_asset",
        "asset_kind": "signal",
        "country_code": "CN",
    }


def test_build_name_rules_marks_cross_country_collision_as_warning() -> None:
    rules = build_name_rules(
        assets=[_make_asset(canonical_name="CN_Sg101_Gefahrenstelle01")],
        candidate_names=[("CN_Sg101_Gefahrenstelle01", "runtime_asset", "signal", "DE")],
    )

    assert rules[0].severity == "warning"
    assert rules[0].rule_kind == "reserved_name"


def test_build_name_rules_emits_info_alias_and_country_preference_rules() -> None:
    rules = build_name_rules(
        assets=[
            _make_asset(
                canonical_name="CN_Sg101_Gefahrenstelle01",
                aliases=["Sg101Gefahrstelle01.flt"],
            )
        ],
        candidate_names=[],
    )

    alias_rule = next(rule for rule in rules if rule.rule_kind == "alias")
    preference_rule = next(
        rule for rule in rules if rule.rule_kind == "country_preference"
    )

    assert alias_rule.severity == "info"
    assert alias_rule.canonical_target == "CN_Sg101_Gefahrenstelle01"
    assert alias_rule.scope == {
        "namespace": "runtime_asset",
        "asset_kind": "signal",
        "country_code": "CN",
    }
    assert preference_rule.severity == "info"
    assert preference_rule.scope["country_code"] == "CN"


def test_build_name_rules_emits_reserved_names_for_runtime_and_soft_namespaces() -> None:
    rules = build_name_rules(
        assets=[_make_asset(canonical_name="CN_Sg101_Gefahrenstelle01")],
        candidate_names=[
            ("CN_Sg101_Gefahrenstelle01", "runtime_asset", "signal", "CN"),
            ("CN_Sg101_Gefahrenstelle01", "scenario_object", "signal", "CN"),
            ("CN_Sg101_Gefahrenstelle01", "variable", "signal", "CN"),
            ("CN_Sg101_Gefahrenstelle01", "external_object", "signal", "CN"),
        ],
    )

    reserved_rules = [rule for rule in rules if rule.rule_kind == "reserved_name"]
    reserved_by_namespace = {
        rule.scope["namespace"]: rule for rule in reserved_rules
    }

    assert set(reserved_by_namespace) == {
        "runtime_asset",
        "scenario_object",
        "variable",
        "external_object",
    }
    assert reserved_by_namespace["runtime_asset"].severity == "high"
    assert reserved_by_namespace["scenario_object"].severity == "warning"
    assert reserved_by_namespace["variable"].severity == "warning"
    assert reserved_by_namespace["external_object"].severity == "warning"
    assert reserved_by_namespace["runtime_asset"].scope != (
        reserved_by_namespace["scenario_object"].scope
    )


def test_build_name_rules_keeps_rule_names_unique_when_alias_matches_other_canonical() -> None:
    rules = build_name_rules(
        assets=[
            _make_asset(canonical_name="AssetA", aliases=["AssetB"]),
            _make_asset(canonical_name="AssetB"),
        ],
        candidate_names=[("AssetB", "runtime_asset", "signal", "CN")],
    )

    rule_names = [rule.name for rule in rules]
    reserved_rules = [rule for rule in rules if rule.rule_kind == "reserved_name"]

    assert len(reserved_rules) == 2
    assert len(rule_names) == len(set(rule_names))


def test_build_name_rules_matches_canonical_collision_case_insensitively() -> None:
    rules = build_name_rules(
        assets=[_make_asset(canonical_name="Foo")],
        candidate_names=[("foo", "runtime_asset", "signal", "CN")],
    )

    reserved_rules = [rule for rule in rules if rule.rule_kind == "reserved_name"]

    assert len(reserved_rules) == 1
    assert reserved_rules[0].canonical_target == "Foo"


def test_build_name_rules_matches_alias_collision_case_insensitively() -> None:
    rules = build_name_rules(
        assets=[_make_asset(canonical_name="Foo", aliases=["Bar"])],
        candidate_names=[("bar", "runtime_asset", "signal", "CN")],
    )

    reserved_rules = [rule for rule in rules if rule.rule_kind == "reserved_name"]

    assert len(reserved_rules) == 1
    assert reserved_rules[0].canonical_target == "Foo"


def test_build_name_rules_keeps_all_rule_names_unique_for_shared_aliases() -> None:
    rules = build_name_rules(
        assets=[
            _make_asset(canonical_name="AssetA", aliases=["SharedAlias"]),
            _make_asset(canonical_name="AssetB", aliases=["SharedAlias"]),
        ],
        candidate_names=[("SharedAlias", "runtime_asset", "signal", "CN")],
    )

    rule_names = [rule.name for rule in rules]

    assert len(rule_names) == len(set(rule_names))


def test_build_name_rules_keeps_names_unique_when_canonical_slugs_collide() -> None:
    rules = build_name_rules(
        assets=[
            _make_asset(canonical_name="Slug/Collision", country_code="US"),
            _make_asset(canonical_name="Slug-Collision", country_code="US"),
        ],
        candidate_names=[],
    )

    country_preference_names = [
        rule.name for rule in rules if rule.rule_kind == "country_preference"
    ]

    assert len(country_preference_names) == 2
    assert len(country_preference_names) == len(set(country_preference_names))


def test_build_reserved_name_candidates_emits_runtime_and_soft_namespace_matches() -> None:
    asset = _make_asset(
        canonical_name="SharedSignal01",
        aliases=["SharedSignalAliasCN"],
    )

    candidates = build_reserved_name_candidates([asset])

    assert ("SharedSignal01", "runtime_asset", "signal", "CN") in candidates
    assert ("SharedSignalAliasCN", "scenario_object", "signal", "CN") in candidates
    assert ("SharedSignalAliasCN", "variable", "signal", "CN") in candidates
    assert ("SharedSignalAliasCN", "external_object", "signal", "CN") in candidates


def test_build_country_taxonomy_normalizes_country_aliases() -> None:
    taxonomy = build_country_taxonomy(
        assets=[
            _make_asset(canonical_name="LampPostUSA01", country_code="USA"),
            _make_asset(canonical_name="LampPostChina01", country_code="China"),
        ],
    )

    assert taxonomy["countries"]["US"]["observed_values"] == ["USA"]
    assert taxonomy["countries"]["CN"]["observed_values"] == ["China"]
    assert taxonomy["alias_to_country"]["usa"] == "US"
    assert taxonomy["alias_to_country"]["china"] == "CN"


def test_build_name_policies_materializes_runtime_and_soft_namespace_policies() -> None:
    asset = _make_asset(
        canonical_name="SharedSignal01",
        aliases=["SharedSignalAliasCN"],
    )
    rules = build_name_rules(
        assets=[asset],
        candidate_names=build_reserved_name_candidates([asset]),
    )
    policies = build_name_policies(
        rules=rules,
        country_taxonomy=build_country_taxonomy([asset], rules),
    )
    policy_by_scope = {
        (
            policy["namespace"],
            policy["match_name"],
            policy["country_scope"],
        ): policy
        for policy in policies
    }

    runtime_policy = policy_by_scope[("runtime_asset", "SharedSignal01", "CN")]
    soft_policy = policy_by_scope[("scenario_object", "SharedSignalAliasCN", "CN")]

    assert runtime_policy["canonical_target"] == "SharedSignal01"
    assert runtime_policy["safe_name_strategy"] == "hard_constraint"
    assert soft_policy["canonical_target"] == "SharedSignal01"
    assert soft_policy["safe_name_strategy"] == "append_namespace"
    assert soft_policy["rule_kind"] == "reserved_name"


def test_build_extractor_manifest_matches_phase1_allowlist_shape() -> None:
    manifest = json.loads(EXTRACTOR_MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest == build_extractor_manifest()
    assert manifest["version"] == 1
    assert manifest["phase"] == "phase1"
    assert manifest["buckets"] == {
        "addons": "addons.jsonl",
        "decals": "decals.jsonl",
        "externals": "externals.jsonl",
        "macros": "macros.jsonl",
        "models": "models.jsonl",
        "samples": "samples.jsonl",
        "signals": "signals.jsonl",
        "styles": "styles.jsonl",
        "tiles": "tiles.jsonl",
    }
    assert manifest["allowlist"] == [
        {
            "match": "Tools/resourceDirs.txt",
            "match_type": "file",
            "collector": "resource_dirs",
        },
        {
            "match": "VisualLib/Models",
            "match_type": "directory",
            "collector": "model_scan",
            "bucket": "models.jsonl",
        },
        {
            "match": "VisualLib/ModelsPBR",
            "match_type": "directory",
            "collector": "model_scan",
            "bucket": "models.jsonl",
        },
        {
            "match": "VisualLib/Styles",
            "match_type": "directory",
            "collector": "style_scan",
            "bucket": "styles.jsonl",
        },
        {
            "match": "VisualLib/TileLib",
            "match_type": "directory",
            "collector": "tile_scan",
            "bucket": "tiles.jsonl",
        },
        {
            "match": "VisualLib/Models/**/SetupFiles/*.DAT",
            "match_type": "glob",
            "collector": "dat_definitions",
        },
        {
            "match": "Tools/pbr_*.xml",
            "match_type": "glob",
            "collector": "pbr_objects",
            "bucket": "models.jsonl",
        },
        {
            "match": "DefaultProject/Config/*.xml",
            "match_type": "glob",
            "collector": "config_xml",
            "bucket": "decals.jsonl",
        },
        {
            "match": "DefaultProject/Config/Macros/*.rmcr",
            "match_type": "glob",
            "collector": "macro_scan",
            "bucket": "macros.jsonl",
        },
        {
            "match": "Samples/*.tdo",
            "match_type": "glob",
            "collector": "sample_scan",
            "bucket": "samples.jsonl",
        },
        {
            "match": "AddOns/**/*.xml",
            "match_type": "glob",
            "collector": "addon_xml_descriptor",
            "bucket": "addons.jsonl",
        },
    ]


def test_build_asset_buckets_routes_directory_scanned_assets_to_expected_outputs() -> None:
    buckets = build_asset_buckets(FIXTURE_ROOT)

    assert [asset.relative_path for asset in buckets["styles.jsonl"]] == [
        "VisualLib/Styles/VTL/Full/TexturePool/TxRoadStandard.rgb"
    ]
    assert [asset.relative_path for asset in buckets["tiles.jsonl"]] == [
        "VisualLib/TileLib/Standard/TileRoad01.attr"
    ]
    assert [asset.relative_path for asset in buckets["addons.jsonl"]] == [
        "AddOns/OdrGateway/odrGateway.xml"
    ]
    assert [asset.relative_path for asset in buckets["macros.jsonl"]] == [
        "DefaultProject/Config/Macros/Town_500m.rmcr"
    ]
    assert [asset.relative_path for asset in buckets["samples.jsonl"]] == [
        "Samples/sample01.tdo"
    ]


def test_build_asset_records_only_routes_pbr_objects_xml_into_object_mapping(
    tmp_path: Path,
) -> None:
    runtime_root = tmp_path / "runtime"
    _write_runtime_file(
        runtime_root,
        "Tools/pbr_objects.xml",
        (
            "<PBRObjects>\n"
            '  <PBRObject pbr="KeptByRouter_PBR" />\n'
            "</PBRObjects>\n"
        ),
    )
    _write_runtime_file(
        runtime_root,
        "Tools/pbr_styles.xml",
        (
            "<PBRObjects>\n"
            '  <PBRObject pbr="IgnoredSibling_PBR" />\n'
            "</PBRObjects>\n"
        ),
    )
    _write_runtime_file(
        runtime_root,
        "VisualLib/ModelsPBR/Props/KeptByRouter_PBR.osgb",
        "",
    )

    assets = build_asset_records(runtime_root)
    asset_ids = {asset.asset_id for asset in assets}

    assert "model:KeptByRouter_PBR" in asset_ids
    assert "model:IgnoredSibling_PBR" not in asset_ids


def test_build_asset_records_normalizes_source_paths_for_relative_and_absolute_runtime_roots() -> None:
    relative_assets = build_asset_records(FIXTURE_ROOT)
    absolute_assets = build_asset_records(FIXTURE_ROOT.resolve())

    relative_sources = {
        _asset_signature(asset): asset.source_path for asset in relative_assets
    }
    absolute_sources = {
        _asset_signature(asset): asset.source_path for asset in absolute_assets
    }

    assert relative_sources == absolute_sources
    assert relative_sources[
        (
            "signal",
            "CN_Sg101_Gefahrenstelle01",
            ("CN",),
            "VisualLib/Models/AddOns/CountryCN/Signals/CN_Sg101_Gefahrenstelle01.flt",
        )
    ] == "VisualLib/Models/AddOns/CountryCN/SetupFiles/TT_SIGNALS_ADD_COUNTRYCN.DAT#L4"


def test_build_asset_records_does_not_infer_fake_country_code_from_arbitrary_prefix(
    tmp_path: Path,
) -> None:
    runtime_root = tmp_path / "runtime"
    _write_runtime_file(
        runtime_root,
        "VisualLib/Models/AddOns/CountryCN/Signals/CN_Signal01.flt",
        "",
    )
    _write_runtime_file(
        runtime_root,
        "VisualLib/Models/AddOns/Legacy/AB_FahrbbTeiler10m-blank.flt",
        "",
    )

    assets = build_asset_records(runtime_root)
    cn_asset = _find_asset(
        assets,
        asset_kind="signal",
        canonical_name="CN_Signal01",
        country_code="CN",
    )
    fake_prefixed_asset = _find_asset_any_country(
        assets,
        asset_kind="model",
        canonical_name="AB_FahrbbTeiler10m-blank",
    )

    assert cn_asset.country_codes == ["CN"]
    assert fake_prefixed_asset.country_codes == []


def _make_asset(
    *,
    canonical_name: str,
    aliases: list[str] | None = None,
    country_code: str = "CN",
) -> VtdAssetRecord:
    return VtdAssetRecord(
        asset_id=f"signal:{country_code}:{canonical_name}",
        asset_kind="signal",
        canonical_name=canonical_name,
        display_name=canonical_name,
        aliases=[] if aliases is None else aliases,
        filename=f"{canonical_name}.flt",
        relative_path=(
            f"VisualLib/Models/AddOns/Country{country_code}/Signals/{canonical_name}.flt"
        ),
        source_path=(
            f"VisualLib/Models/AddOns/Country{country_code}/SetupFiles/"
            f"TT_SIGNALS_ADD_COUNTRY{country_code}.DAT#L4"
        ),
        country_codes=[country_code],
        variant_tags=[],
        group_path=f"{country_code}-Signs-S",
        runtime_family="signal",
        metadata={},
    )


def _write_runtime_file(runtime_root: Path, relative_path: str, content: str) -> Path:
    target_path = runtime_root / Path(relative_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding="utf-8")
    return target_path


def _find_asset(
    assets: list[VtdAssetRecord],
    *,
    asset_kind: str,
    canonical_name: str,
    country_code: str = "",
) -> VtdAssetRecord:
    for asset in assets:
        if asset.asset_kind != asset_kind:
            continue
        if asset.canonical_name != canonical_name:
            continue
        if country_code and country_code not in asset.country_codes:
            continue
        if not country_code and asset.country_codes:
            continue
        return asset
    raise AssertionError(
        f"Missing asset kind={asset_kind} canonical={canonical_name} country={country_code}"
    )


def _asset_signature(asset: VtdAssetRecord) -> tuple[str, str, tuple[str, ...], str]:
    return (
        asset.asset_kind,
        asset.canonical_name,
        tuple(asset.country_codes),
        asset.relative_path,
    )


def _find_asset_any_country(
    assets: list[VtdAssetRecord],
    *,
    asset_kind: str,
    canonical_name: str,
) -> VtdAssetRecord:
    for asset in assets:
        if asset.asset_kind == asset_kind and asset.canonical_name == canonical_name:
            return asset
    raise AssertionError(
        f"Missing asset kind={asset_kind} canonical={canonical_name}"
    )
