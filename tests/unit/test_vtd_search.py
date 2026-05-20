from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from openscenario_mcp.knowledge.vtd_search import search_vtd_assets, search_vtd_rules
from openscenario_mcp.models import VtdAssetRecord, VtdKnowledgeBase, VtdNameRule
from openscenario_mcp.runtime import _build_runtime


def test_runtime_loads_vtd_knowledge_base(sample_project_root: Path) -> None:
    runtime = _build_runtime(project_root=sample_project_root)
    shared_signal_assets = runtime.vtd_knowledge_base.assets_by_canonical_name[
        "SharedSignal01"
    ]

    assert "Storyboard" in runtime.knowledge_base.records_by_element
    assert runtime.vtd_knowledge_base.assets_by_canonical_name
    assert "SharedSignal01" in runtime.vtd_knowledge_base.assets_by_canonical_name
    assert isinstance(shared_signal_assets, list)
    assert len(shared_signal_assets) >= 2
    assert {asset.asset_id for asset in shared_signal_assets} >= {
        "signal:CN:SharedSignal01",
        "signal:DE:SharedSignal01",
    }
    assert runtime.vtd_knowledge_base.rules_by_name


def test_search_vtd_assets_ranks_canonical_name_matches_above_alias_matches(
    sample_vtd_knowledge_base,
) -> None:
    hits = search_vtd_assets("SharedSignal01", sample_vtd_knowledge_base, top_k=3)

    assert [hit.asset.asset_id for hit in hits] == [
        "signal:CN:SharedSignal01",
        "signal:DE:SharedSignal01",
        "signal:CN:DifferentSignal01",
    ]
    assert [hit.match_field for hit in hits] == [
        "canonical_name",
        "canonical_name",
        "alias",
    ]


def test_search_vtd_assets_matches_alias_and_country_filter(
    sample_vtd_knowledge_base,
) -> None:
    alias_hits = search_vtd_assets(
        "Sg101Gefahrstelle01.flt",
        sample_vtd_knowledge_base,
        country_code="CN",
    )
    country_hits = search_vtd_assets(
        "SharedSignal01",
        sample_vtd_knowledge_base,
        country_code="DE",
    )

    assert [hit.asset.asset_id for hit in alias_hits] == [
        "signal:CN:CN_Sg101_Gefahrenstelle01",
    ]
    assert alias_hits[0].match_field == "alias"
    assert [hit.asset.asset_id for hit in country_hits] == [
        "signal:DE:SharedSignal01",
    ]


def test_search_vtd_rules_respects_namespace_and_country_filters(
    sample_vtd_knowledge_base,
) -> None:
    runtime_hits = search_vtd_rules(
        "SharedSignal01",
        sample_vtd_knowledge_base,
        namespace="runtime_asset",
        country_code="DE",
    )
    scenario_hits = search_vtd_rules(
        "SharedSignal01",
        sample_vtd_knowledge_base,
        namespace="scenario_object",
        country_code="CN",
    )

    assert [hit.rule.name for hit in runtime_hits] == [
        "country-preference-runtime-asset-sharedsignal01-de",
    ]
    assert runtime_hits[0].rule.scope["namespace"] == "runtime_asset"
    assert [hit.rule.name for hit in scenario_hits] == [
        "reserved-scenario-object-sharedsignal01-cn",
    ]
    assert scenario_hits[0].rule.scope["namespace"] == "scenario_object"


def test_search_vtd_rules_keeps_global_scope_rules_under_country_filter() -> None:
    knowledge_base = _build_rule_search_knowledge_base()

    unfiltered_hits = search_vtd_rules(
        "SharedRoadStyle01",
        knowledge_base,
        namespace="runtime_asset",
        asset_kind="style",
        top_k=10,
    )
    country_hits = search_vtd_rules(
        "SharedRoadStyle01",
        knowledge_base,
        namespace="runtime_asset",
        asset_kind="style",
        country_code="CN",
        top_k=10,
    )

    assert [hit.rule.name for hit in unfiltered_hits] == [
        "reserved-runtime-asset-sharedroadstyle01-global",
    ]
    assert [hit.rule.name for hit in country_hits] == [
        "reserved-runtime-asset-sharedroadstyle01-global",
    ]


def test_search_vtd_assets_prefers_exact_country_asset_over_global_fallback() -> None:
    knowledge_base = _build_asset_search_knowledge_base()

    hits = search_vtd_assets(
        "SharedRoadStyle01",
        knowledge_base,
        asset_kind="style",
        country_code="US",
        top_k=2,
    )

    assert [hit.asset.asset_id for hit in hits] == [
        "style:US:SharedRoadStyle01",
        "style:global:SharedRoadStyle01",
    ]


def test_search_vtd_assets_matches_country_aliases_and_prefers_usa_over_global() -> None:
    knowledge_base = _build_country_alias_asset_search_knowledge_base()

    cn_hits = search_vtd_assets(
        "SgCN_Rd_TrafficLight_Left_01",
        knowledge_base,
        asset_kind="model",
        country_code="CN",
        top_k=5,
    )
    us_hits = search_vtd_assets(
        "SharedLampPost01",
        knowledge_base,
        asset_kind="model",
        country_code="US",
        top_k=2,
    )

    assert [hit.asset.asset_id for hit in cn_hits] == [
        "model:China:SgCN_Rd_TrafficLight_Left_01",
    ]
    assert [hit.asset.asset_id for hit in us_hits] == [
        "model:USA:SharedLampPost01",
        "model:global:SharedLampPost01",
    ]


def test_search_vtd_rules_match_country_aliases_for_cn_and_us() -> None:
    knowledge_base = _build_country_alias_rule_search_knowledge_base()

    cn_hits = search_vtd_rules(
        "SgCN_Rd_TrafficLight_Left_01",
        knowledge_base,
        namespace="runtime_asset",
        asset_kind="model",
        country_code="CN",
        top_k=5,
    )
    us_hits = search_vtd_rules(
        "SharedLampPost01",
        knowledge_base,
        namespace="runtime_asset",
        asset_kind="model",
        country_code="US",
        top_k=5,
    )

    assert [hit.rule.name for hit in cn_hits] == [
        "reserved-runtime-asset-sgcn-rd-trafficlight-left-01-china",
    ]
    assert [hit.rule.name for hit in us_hits] == [
        "reserved-runtime-asset-sharedlamppost01-usa",
    ]


def test_search_vtd_assets_uses_loaded_country_taxonomy_aliases() -> None:
    taxonomy = _build_country_taxonomy_metadata({"CN": ["cn", "prc"]})
    asset = VtdAssetRecord(
        asset_id="signal:CN:SharedSignal01",
        asset_kind="signal",
        canonical_name="SharedSignal01",
        display_name="SharedSignal01",
        filename="SharedSignal01.flt",
        relative_path=(
            "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Models/AddOns/CountryCN/"
            "Signals/SharedSignal01.flt"
        ),
        source_path=(
            "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Models/AddOns/CountryCN/"
            "SetupFiles/TT_SIGNALS_ADD_COUNTRYCN.DAT#L1"
        ),
        group_path="VisualLib/Models/AddOns/CountryCN/Signals",
        runtime_family="signal",
        aliases=[],
        country_codes=["CN"],
        variant_tags=[],
        metadata={},
    )
    knowledge_base = VtdKnowledgeBase(
        assets_by_id={asset.asset_id: asset},
        assets_by_canonical_name={asset.canonical_name: [asset]},
        metadata={"country_taxonomy": taxonomy},
    )

    hits = search_vtd_assets(
        "SharedSignal01",
        knowledge_base,
        asset_kind="signal",
        country_code="PRC",
        top_k=5,
    )

    assert [hit.asset.asset_id for hit in hits] == ["signal:CN:SharedSignal01"]


def test_search_vtd_rules_uses_loaded_country_taxonomy_aliases() -> None:
    taxonomy = _build_country_taxonomy_metadata({"CN": ["cn", "prc"]})
    rule = VtdNameRule(
        name="reserved-runtime-asset-sharedsignal01-cn",
        rule_kind="reserved_name",
        severity="info",
        canonical_target="SharedSignal01",
        asset_kind="signal",
        reason="PRC-aware reservation.",
        source_path=(
            "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Models/AddOns/CountryCN/"
            "SetupFiles/TT_SIGNALS_ADD_COUNTRYCN.DAT#L1"
        ),
        scope={
            "namespace": "runtime_asset",
            "asset_kind": "signal",
            "country_code": "CN",
        },
        metadata={"match_name": "SharedSignal01"},
    )
    knowledge_base = VtdKnowledgeBase(
        rules_by_name={rule.name: rule},
        metadata={"country_taxonomy": taxonomy},
    )

    hits = search_vtd_rules(
        "SharedSignal01",
        knowledge_base,
        namespace="runtime_asset",
        asset_kind="signal",
        country_code="PRC",
        top_k=5,
    )

    assert [hit.rule.name for hit in hits] == [
        "reserved-runtime-asset-sharedsignal01-cn",
    ]


def test_build_runtime_raises_clear_error_when_vtd_snapshot_is_missing(
    tmp_path: Path,
    write_sample_element_record_json: Callable[..., Path],
) -> None:
    elements_dir = tmp_path / "knowledge" / "structured" / "elements"
    write_sample_element_record_json(directory=elements_dir, filename="Storyboard.json")

    with pytest.raises(
        FileNotFoundError,
        match=r"Structured VTD snapshot directory not found at .+knowledge.+structured.+vtd",
    ):
        _build_runtime(project_root=tmp_path)


def test_build_runtime_raises_clear_error_when_vtd_snapshot_is_incomplete(
    tmp_path: Path,
    write_sample_element_record_json: Callable[..., Path],
) -> None:
    elements_dir = tmp_path / "knowledge" / "structured" / "elements"
    write_sample_element_record_json(directory=elements_dir, filename="Storyboard.json")
    vtd_dir = tmp_path / "knowledge" / "structured" / "vtd"
    (vtd_dir / "assets").mkdir(parents=True)
    (vtd_dir / "rules").mkdir(parents=True)
    (vtd_dir / "assets" / "signals.jsonl").write_text("", encoding="utf-8")

    with pytest.raises(
        FileNotFoundError,
        match=r"Structured VTD snapshot is incomplete under .+knowledge.+structured.+vtd",
    ):
        _build_runtime(project_root=tmp_path)


def test_build_runtime_raises_clear_error_when_vtd_snapshot_bucket_is_missing(
    tmp_path: Path,
    write_sample_element_record_json: Callable[..., Path],
) -> None:
    elements_dir = tmp_path / "knowledge" / "structured" / "elements"
    write_sample_element_record_json(directory=elements_dir, filename="Storyboard.json")
    vtd_dir = tmp_path / "knowledge" / "structured" / "vtd"
    assets_dir = vtd_dir / "assets"
    rules_dir = vtd_dir / "rules"
    assets_dir.mkdir(parents=True)
    rules_dir.mkdir(parents=True)

    summary = {
        "version": 1,
        "phase": "phase-1",
        "runtime_family": "VTD.2020",
        "release_name": "RodDistro_6980_Rod4.6.1",
        "runtime_root": "D:/wyj/VTD-2020-install/VTD.2020/Runtime",
        "release_root": (
            "D:/wyj/VTD-2020-install/VTD.2020/Runtime/Tools/"
            "RodDistro_6980_Rod4.6.1"
        ),
        "source_id": "vtd-runtime",
        "sources": [
            {
                "id": "vtd-runtime",
                "kind": "runtime",
                "path": "knowledge/structured/vtd",
            }
        ],
        "asset_counts": {
            "signals": 0,
            "externals": 0,
            "decals": 0,
            "models": 0,
            "styles": 0,
            "tiles": 0,
            "addons": 0,
            "macros": 0,
            "samples": 0,
        },
        "rule_counts": {
            "reserved-names": 0,
            "aliases": 0,
            "country-preferences": 0,
        },
        "asset_total": 0,
        "rule_total": 0,
    }
    (vtd_dir / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    for filename in (
        "signals.jsonl",
        "externals.jsonl",
        "decals.jsonl",
        "models.jsonl",
        "styles.jsonl",
        "tiles.jsonl",
        "addons.jsonl",
        "macros.jsonl",
        "samples.jsonl",
    ):
        (assets_dir / filename).write_text("", encoding="utf-8")

    for filename in ("reserved-names.jsonl", "country-preferences.jsonl"):
        (rules_dir / filename).write_text("", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=(
            r"Failed to load structured VTD snapshot from .+knowledge.+structured.+vtd"
            r".+aliases"
        ),
    ):
        _build_runtime(project_root=tmp_path)


def _build_rule_search_knowledge_base() -> VtdKnowledgeBase:
    global_rule = VtdNameRule(
        name="reserved-runtime-asset-sharedroadstyle01-global",
        rule_kind="reserved_name",
        severity="info",
        canonical_target="SharedRoadStyle01",
        asset_kind="style",
        reason="Global runtime style reservation.",
        source_path=(
            "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Styles/Standard/"
            "SharedRoadStyle01.rgb"
        ),
        scope={
            "namespace": "runtime_asset",
            "asset_kind": "style",
            "country_code": "",
        },
        metadata={},
    )
    return VtdKnowledgeBase(
        rules_by_name={global_rule.name: global_rule},
    )


def _build_asset_search_knowledge_base() -> VtdKnowledgeBase:
    global_asset = VtdAssetRecord(
        asset_id="style:global:SharedRoadStyle01",
        asset_kind="style",
        canonical_name="SharedRoadStyle01",
        display_name="SharedRoadStyle01",
        filename="SharedRoadStyle01.rgb",
        relative_path=(
            "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Styles/Standard/"
            "SharedRoadStyle01.rgb"
        ),
        source_path=(
            "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Styles/Standard/"
            "SharedRoadStyle01.rgb"
        ),
        group_path="VisualLib/Styles/Standard",
        runtime_family="style",
        aliases=[],
        country_codes=[],
        variant_tags=[],
        metadata={},
    )
    us_asset = VtdAssetRecord(
        asset_id="style:US:SharedRoadStyle01",
        asset_kind="style",
        canonical_name="SharedRoadStyle01",
        display_name="SharedRoadStyle01",
        filename="SharedRoadStyle01.rgb",
        relative_path=(
            "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Styles/CountryUS/"
            "SharedRoadStyle01.rgb"
        ),
        source_path=(
            "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Styles/CountryUS/"
            "SharedRoadStyle01.rgb"
        ),
        group_path="VisualLib/Styles/CountryUS",
        runtime_family="style",
        aliases=[],
        country_codes=["US"],
        variant_tags=[],
        metadata={},
    )
    return VtdKnowledgeBase(
        assets_by_id={
            global_asset.asset_id: global_asset,
            us_asset.asset_id: us_asset,
        },
        assets_by_canonical_name={
            "SharedRoadStyle01": [global_asset, us_asset],
        },
    )


def _build_country_alias_asset_search_knowledge_base() -> VtdKnowledgeBase:
    china_asset = VtdAssetRecord(
        asset_id="model:China:SgCN_Rd_TrafficLight_Left_01",
        asset_kind="model",
        canonical_name="SgCN_Rd_TrafficLight_Left_01",
        display_name="SgCN_Rd_TrafficLight_Left_01",
        filename="SgCN_Rd_TrafficLight_Left_01.osgb",
        relative_path=(
            "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Models/AddOns/CountryCN/"
            "Signals/SgCN_Rd_TrafficLight_Left_01.osgb"
        ),
        source_path=(
            "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Models/AddOns/CountryCN/"
            "Signals/SgCN_Rd_TrafficLight_Left_01.osgb"
        ),
        group_path="VisualLib/Models/AddOns/CountryCN/Signals",
        runtime_family="model",
        aliases=[],
        country_codes=["China"],
        variant_tags=[],
        metadata={},
    )
    global_asset = VtdAssetRecord(
        asset_id="model:global:SharedLampPost01",
        asset_kind="model",
        canonical_name="SharedLampPost01",
        display_name="SharedLampPost01",
        filename="SharedLampPost01.osgb",
        relative_path=(
            "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Models/StreetFurniture/"
            "SharedLampPost01.osgb"
        ),
        source_path=(
            "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Models/StreetFurniture/"
            "SharedLampPost01.osgb"
        ),
        group_path="VisualLib/Models/StreetFurniture",
        runtime_family="model",
        aliases=[],
        country_codes=[],
        variant_tags=[],
        metadata={},
    )
    usa_asset = VtdAssetRecord(
        asset_id="model:USA:SharedLampPost01",
        asset_kind="model",
        canonical_name="SharedLampPost01",
        display_name="SharedLampPost01",
        filename="SharedLampPost01.osgb",
        relative_path=(
            "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Models/AddOns/CountryUS/"
            "StreetFurniture/SharedLampPost01.osgb"
        ),
        source_path=(
            "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Models/AddOns/CountryUS/"
            "StreetFurniture/SharedLampPost01.osgb"
        ),
        group_path="VisualLib/Models/AddOns/CountryUS/StreetFurniture",
        runtime_family="model",
        aliases=[],
        country_codes=["USA"],
        variant_tags=[],
        metadata={},
    )
    return VtdKnowledgeBase(
        assets_by_id={
            china_asset.asset_id: china_asset,
            global_asset.asset_id: global_asset,
            usa_asset.asset_id: usa_asset,
        },
        assets_by_canonical_name={
            "SgCN_Rd_TrafficLight_Left_01": [china_asset],
            "SharedLampPost01": [global_asset, usa_asset],
        },
    )


def _build_country_alias_rule_search_knowledge_base() -> VtdKnowledgeBase:
    china_rule = VtdNameRule(
        name="reserved-runtime-asset-sgcn-rd-trafficlight-left-01-china",
        rule_kind="reserved_name",
        severity="info",
        canonical_target="SgCN_Rd_TrafficLight_Left_01",
        asset_kind="model",
        reason="China traffic light model reservation.",
        source_path=(
            "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Models/AddOns/CountryCN/"
            "Signals/SgCN_Rd_TrafficLight_Left_01.osgb"
        ),
        scope={
            "namespace": "runtime_asset",
            "asset_kind": "model",
            "country_code": "China",
        },
        metadata={},
    )
    usa_rule = VtdNameRule(
        name="reserved-runtime-asset-sharedlamppost01-usa",
        rule_kind="reserved_name",
        severity="info",
        canonical_target="SharedLampPost01",
        asset_kind="model",
        reason="USA lamp post model reservation.",
        source_path=(
            "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Models/AddOns/CountryUS/"
            "StreetFurniture/SharedLampPost01.osgb"
        ),
        scope={
            "namespace": "runtime_asset",
            "asset_kind": "model",
            "country_code": "USA",
        },
        metadata={},
    )
    return VtdKnowledgeBase(
        rules_by_name={
            china_rule.name: china_rule,
            usa_rule.name: usa_rule,
        },
    )


def _build_country_taxonomy_metadata(
    aliases_by_country: dict[str, list[str]],
) -> dict[str, object]:
    alias_to_country: dict[str, str] = {}
    countries: dict[str, dict[str, object]] = {}
    for canonical_code, aliases in aliases_by_country.items():
        normalized_aliases = sorted({canonical_code.casefold(), *(alias.casefold() for alias in aliases)})
        countries[canonical_code] = {
            "canonical_code": canonical_code,
            "observed_values": [canonical_code],
            "aliases": normalized_aliases,
        }
        for alias in normalized_aliases:
            alias_to_country[alias] = canonical_code
    return {
        "version": 1,
        "countries": countries,
        "alias_to_country": alias_to_country,
    }
