from __future__ import annotations

from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

from openscenario_mcp.models import (
    OscVtdBindingRule,
    SourceEntry,
    VtdAssetFamily,
    VtdAssetRecord,
    VtdAssetVariant,
    VtdKnowledgeBase,
    VtdNamePolicy,
    VtdNameRule,
)


def test_vtd_asset_record_contract() -> None:
    record = VtdAssetRecord(
        asset_id="signal:CN_Sg101_Gefahrenstelle01",
        asset_kind="signal",
        canonical_name="CN_Sg101_Gefahrenstelle01",
        display_name="CN danger sign 101 small",
        aliases=["Sg101Gefahrstelle01.flt"],
        filename="CN_Sg101_Gefahrenstelle01.flt",
        relative_path="VisualLib/Models/AddOns/CountryCN/Signals/CN_Sg101_Gefahrenstelle01.flt",
        source_path="tests/fixtures/vtd_runtime/VisualLib/Models/AddOns/CountryCN/SetupFiles/TT_SIGNALS_ADD_COUNTRYCN.DAT#L1",
        country_codes=["CN"],
        variant_tags=[],
        group_path="CN-Signs-S",
        runtime_family="signal",
        metadata={"unit": "none"},
    )

    assert record.canonical_name == "CN_Sg101_Gefahrenstelle01"
    assert record.aliases == ["Sg101Gefahrstelle01.flt"]
    assert record.metadata["unit"] == "none"


def test_vtd_name_rule_contract() -> None:
    rule = VtdNameRule(
        name="countrycn-signal-alias",
        rule_kind="alias",
        severity="info",
        canonical_target="CN_Sg101_Gefahrenstelle01",
        asset_kind="signal",
        reason="CountryCN signal setup files use FLT filenames as aliases.",
        scope={
            "namespace": "runtime_asset",
            "asset_kind": "signal",
            "country_code": "CN",
        },
        source_path="tests/fixtures/vtd_runtime/VisualLib/Models/AddOns/CountryCN/SetupFiles/TT_SIGNALS_ADD_COUNTRYCN.DAT#L1",
        metadata={"runtime_family": "signal", "country_code": "CN"},
    )

    assert rule.name == "countrycn-signal-alias"
    assert rule.rule_kind == "alias"
    assert rule.canonical_target == "CN_Sg101_Gefahrenstelle01"
    assert rule.scope == {
        "namespace": "runtime_asset",
        "asset_kind": "signal",
        "country_code": "CN",
    }


def test_vtd_knowledge_base_contract() -> None:
    asset_hints = get_type_hints(VtdAssetRecord)
    assert get_origin(asset_hints["aliases"]) is list
    assert get_origin(asset_hints["metadata"]) is dict
    _, metadata_value_hint = get_args(asset_hints["metadata"])
    assert metadata_value_hint is Any

    rule = VtdNameRule(
        name="countrycn-signal-alias",
        rule_kind="alias",
        severity="info",
        canonical_target="CN_Sg101_Gefahrenstelle01",
        asset_kind="signal",
        reason="CountryCN signal setup files use FLT filenames as aliases.",
        scope={
            "namespace": "runtime_asset",
            "asset_kind": "signal",
            "country_code": "CN",
        },
        source_path="tests/fixtures/vtd_runtime/VisualLib/Models/AddOns/CountryCN/SetupFiles/TT_SIGNALS_ADD_COUNTRYCN.DAT#L1",
    )
    record = VtdAssetRecord(
        asset_id="signal:CN_Sg101_Gefahrenstelle01",
        asset_kind="signal",
        canonical_name="CN_Sg101_Gefahrenstelle01",
        display_name="CN danger sign 101 small",
        aliases=["Sg101Gefahrstelle01.flt"],
        filename="CN_Sg101_Gefahrenstelle01.flt",
        relative_path="VisualLib/Models/AddOns/CountryCN/Signals/CN_Sg101_Gefahrenstelle01.flt",
        source_path="tests/fixtures/vtd_runtime/VisualLib/Models/AddOns/CountryCN/SetupFiles/TT_SIGNALS_ADD_COUNTRYCN.DAT#L1",
        country_codes=["CN"],
        variant_tags=[],
        group_path="CN-Signs-S",
        runtime_family="signal",
        metadata={"unit": "none"},
    )
    source = SourceEntry(
        id="vtd-runtime",
        kind="runtime",
        path="knowledge/structured/vtd",
    )
    knowledge_base = VtdKnowledgeBase(
        runtime_root="tests/fixtures/vtd_runtime",
        assets_by_id={record.asset_id: record},
        assets_by_canonical_name={record.canonical_name: [record]},
        rules_by_name={rule.name: rule},
        sources=[source],
        metadata={"source_id": "vtd-runtime"},
    )

    knowledge_hints = get_type_hints(VtdKnowledgeBase)
    _, asset_hint = get_args(knowledge_hints["assets_by_id"])
    assert asset_hint is VtdAssetRecord
    _, canonical_asset_list_hint = get_args(knowledge_hints["assets_by_canonical_name"])
    assert get_origin(canonical_asset_list_hint) is list
    (canonical_asset_hint,) = get_args(canonical_asset_list_hint)
    assert canonical_asset_hint is VtdAssetRecord
    _, rule_hint = get_args(knowledge_hints["rules_by_name"])
    assert rule_hint is VtdNameRule
    (source_hint,) = get_args(knowledge_hints["sources"])
    assert source_hint is SourceEntry
    rule_hints = get_type_hints(VtdNameRule)
    assert get_origin(rule_hints["scope"]) is dict
    scope_key_hint, scope_value_hint = get_args(rule_hints["scope"])
    assert scope_key_hint is str
    assert scope_value_hint is str
    assert knowledge_base.assets_by_id[record.asset_id].runtime_family == "signal"
    assert (
        knowledge_base.assets_by_canonical_name[record.canonical_name][0].asset_id
        == record.asset_id
    )
    assert knowledge_base.rules_by_name[rule.name].canonical_target == record.canonical_name
    assert knowledge_base.rules_by_name[rule.name].scope["namespace"] == "runtime_asset"
    assert knowledge_base.sources[0].path == "knowledge/structured/vtd"
    assert knowledge_base.metadata["source_id"] == "vtd-runtime"


def test_vtd_knowledge_base_canonical_index_supports_multiple_assets_per_name() -> None:
    cn_record = VtdAssetRecord(
        asset_id="signal:CN:SharedSignal01",
        asset_kind="signal",
        canonical_name="SharedSignal01",
        display_name="CN SharedSignal01",
        aliases=[],
        filename="SharedSignal01.flt",
        relative_path=(
            "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Models/AddOns/CountryCN/"
            "Signals/SharedSignal01.flt"
        ),
        source_path=(
            "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Models/AddOns/CountryCN/"
            "SetupFiles/TT_SIGNALS_ADD_COUNTRYCN.DAT#L1"
        ),
        country_codes=["CN"],
        variant_tags=[],
        group_path="CN-Signs-S",
        runtime_family="signal",
        metadata={},
    )
    de_record = VtdAssetRecord(
        asset_id="signal:DE:SharedSignal01",
        asset_kind="signal",
        canonical_name="SharedSignal01",
        display_name="DE SharedSignal01",
        aliases=[],
        filename="SharedSignal01.flt",
        relative_path=(
            "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Models/AddOns/CountryDE/"
            "Signals/SharedSignal01.flt"
        ),
        source_path=(
            "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Models/AddOns/CountryDE/"
            "SetupFiles/TT_SIGNALS_ADD_COUNTRYDE.DAT#L1"
        ),
        country_codes=["DE"],
        variant_tags=[],
        group_path="DE-Signs-S",
        runtime_family="signal",
        metadata={},
    )

    knowledge_base = VtdKnowledgeBase(
        runtime_root="tests/fixtures/vtd_runtime",
        assets_by_id={
            cn_record.asset_id: cn_record,
            de_record.asset_id: de_record,
        },
        assets_by_canonical_name={
            "SharedSignal01": [cn_record, de_record],
        },
        rules_by_name={},
        sources=[],
        metadata={},
    )

    assert [record.asset_id for record in knowledge_base.assets_by_canonical_name["SharedSignal01"]] == [
        "signal:CN:SharedSignal01",
        "signal:DE:SharedSignal01",
    ]


def test_vtd_runtime_fixture_tree_contains_expected_inputs() -> None:
    runtime_root = Path("tests/fixtures/vtd_runtime")
    expected_paths = [
        runtime_root / "README.md",
        runtime_root / "Tools" / "resourceDirs.txt",
        runtime_root / "Tools" / "pbr_objects.xml",
        runtime_root / "DefaultProject" / "Config" / "decalScatterConfig01.xml",
        runtime_root / "DefaultProject" / "Config" / "Macros" / "Town_500m.rmcr",
        runtime_root / "Samples" / "sample01.tdo",
        runtime_root / "VisualLib" / "Styles" / "VTL" / "Full" / "TexturePool" / "TxRoadStandard.rgb",
        runtime_root / "VisualLib" / "TileLib" / "Standard" / "TileRoad01.attr",
        runtime_root / "AddOns" / "OdrGateway" / "odrGateway.xml",
        runtime_root
        / "VisualLib"
        / "Models"
        / "AddOns"
        / "CountryCN"
        / "Externals"
        / "CN_GantryPole01.flt",
        runtime_root
        / "VisualLib"
        / "Models"
        / "AddOns"
        / "CountryCN"
        / "Signals"
        / "CN_Sg101_Gefahrenstelle01.flt",
        runtime_root
        / "VisualLib"
        / "Models"
        / "AddOns"
        / "CountryCN"
        / "SetupFiles"
        / "TT_EXTERNALS_ADD_COUNTRYCN.DAT",
        runtime_root
        / "VisualLib"
        / "Models"
        / "AddOns"
        / "CountryCN"
        / "SetupFiles"
        / "TT_SIGNALS_ADD_COUNTRYCN.DAT",
    ]

    for expected_path in expected_paths:
        assert expected_path.is_file(), f"Missing VTD fixture: {expected_path}"


def test_vtd_snapshot_directories_exist() -> None:
    assert Path("knowledge/structured/vtd/assets").is_dir()
    assert Path("knowledge/structured/vtd/rules").is_dir()


def test_vtd_asset_family_contract() -> None:
    family = VtdAssetFamily(
        family_id="signal-family:warning-101",
        canonical_key="warning-101",
        asset_kind="signal",
        preferred_variant_id="signal-variant:cn:warning-101",
        variant_ids=["signal-variant:cn:warning-101"],
        country_scopes=["CN"],
        semantic_tags=["warning_sign"],
        selection_policy="prefer_exact_country",
        notes=[],
    )

    family_hints = get_type_hints(VtdAssetFamily)
    assert get_origin(family_hints["variant_ids"]) is list
    assert get_origin(family_hints["country_scopes"]) is list
    assert get_origin(family_hints["semantic_tags"]) is list
    assert family.asset_kind == "signal"
    assert family.preferred_variant_id in family.variant_ids
    assert family.selection_policy == "prefer_exact_country"


def test_vtd_asset_variant_contract() -> None:
    variant = VtdAssetVariant(
        variant_id="signal-variant:cn:warning-101",
        family_id="signal-family:warning-101",
        asset_id="signal:CN:CN_Sg101_Gefahrenstelle01",
        country_scope="CN",
        variant_tags=["warning_sign", "country_cn"],
        source_type="phase1_asset",
        source_rank=10,
        referencable_as=["CN_Sg101_Gefahrenstelle01", "Sg101Gefahrstelle01.flt"],
        usage_tags=["roadside"],
        quality_flags=[],
    )

    variant_hints = get_type_hints(VtdAssetVariant)
    assert get_origin(variant_hints["variant_tags"]) is list
    assert get_origin(variant_hints["referencable_as"]) is list
    assert get_origin(variant_hints["usage_tags"]) is list
    assert get_origin(variant_hints["quality_flags"]) is list
    assert variant.family_id == "signal-family:warning-101"
    assert variant.source_rank == 10
    assert variant.referencable_as[0] == "CN_Sg101_Gefahrenstelle01"


def test_vtd_name_policy_contract() -> None:
    policy = VtdNamePolicy(
        policy_id="name-policy:signal:cn:warning-101",
        namespace="runtime_asset",
        asset_kind="signal",
        country_scope="CN",
        rule_kind="alias",
        severity="info",
        match_mode="exact_or_alias",
        canonical_target="CN_Sg101_Gefahrenstelle01",
        safe_name_strategy="prefer_canonical_name",
        reason="Prefer the canonical runtime asset name in generated XML.",
        source_paths=[
            "knowledge/structured/vtd/rules/aliases.jsonl#L1",
            "knowledge/structured/vtd/assets/signals.jsonl#L1",
        ],
    )

    policy_hints = get_type_hints(VtdNamePolicy)
    assert get_origin(policy_hints["source_paths"]) is list
    assert policy.namespace == "runtime_asset"
    assert policy.country_scope == "CN"
    assert policy.safe_name_strategy == "prefer_canonical_name"


def test_osc_vtd_binding_rule_contract() -> None:
    rule = OscVtdBindingRule(
        binding_id="osc-vtd-binding:Vehicle:model3d",
        element="Vehicle",
        attribute="model3d",
        parent_context="Entities/ScenarioObject/Vehicle",
        binding_kind="asset_reference",
        namespace="runtime_asset",
        asset_kind="model",
        family_selector={"semantic_tags": ["vehicle_model"]},
        constraint_mode="required",
        selection_recipe={"prefer_country": True, "selection_policy": "prefer_exact_country"},
        fallback_policy={"on_missing": "leave_attribute_empty"},
    )

    rule_hints = get_type_hints(OscVtdBindingRule)
    assert get_origin(rule_hints["family_selector"]) is dict
    assert get_origin(rule_hints["selection_recipe"]) is dict
    assert get_origin(rule_hints["fallback_policy"]) is dict
    assert rule.element == "Vehicle"
    assert rule.attribute == "model3d"
    assert rule.binding_kind == "asset_reference"
