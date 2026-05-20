from __future__ import annotations

from openscenario_mcp.models import SourceEntry, VtdAssetRecord, VtdKnowledgeBase, VtdNameRule
from openscenario_mcp.tools.resolve_vtd_name import build_resolve_vtd_name_tool


_CN_SIGNAL_SOURCE_PATH = (
    "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Models/AddOns/CountryCN/SetupFiles/"
    "TT_SIGNALS_ADD_COUNTRYCN.DAT#L3"
)


def test_resolve_vtd_name_returns_high_for_exact_runtime_asset_collision(
    sample_vtd_knowledge_base,
) -> None:
    tool = build_resolve_vtd_name_tool(sample_vtd_knowledge_base)

    result = tool(
        name="CN_Sg101_Gefahrenstelle01",
        namespace="runtime_asset",
        asset_kind="signal",
        country_code="CN",
    )

    assert result["normalized_name"] == "CN_Sg101_Gefahrenstelle01"
    assert result["severity"] == "high"
    assert result["rule_kind"] == "canonical_name"
    assert result["hard_constraint"] is True
    assert result["canonical_target"] == "CN_Sg101_Gefahrenstelle01"
    assert result["alternatives"] == ["CN_Sg101_Gefahrenstelle01"]
    assert result["source_paths"] == [_CN_SIGNAL_SOURCE_PATH]
    assert "safe_name" not in result
    assert "override_mapping" not in result


def test_resolve_vtd_name_returns_safe_name_for_soft_namespace_exact_collision(
) -> None:
    knowledge_base = _build_soft_rule_knowledge_base()
    tool = build_resolve_vtd_name_tool(knowledge_base)

    result = tool(
        name="SharedSignal01",
        namespace="scenario_object",
        asset_kind="signal",
        country_code="CN",
    )

    assert result["severity"] == "warning"
    assert result["rule_kind"] == "reserved_name"
    assert result["hard_constraint"] is False
    assert result["canonical_target"] == "SharedSignal01"
    assert result["safe_name"] != "SharedSignal01"
    assert result["safe_name"].endswith("_scenario_object")
    assert result["reason"] == "Avoid existing scenario object names from the VTD snapshot."
    assert result["alternatives"] == ["SharedSignal01_scenario_object", "SharedSignal01"]
    assert result["source_paths"] == [_CN_SHARED_SOURCE_PATH]
    assert "override_mapping" not in result


def test_resolve_vtd_name_preserves_override_mapping_for_soft_namespace(
) -> None:
    knowledge_base = _build_soft_rule_knowledge_base()
    tool = build_resolve_vtd_name_tool(knowledge_base)

    result = tool(
        name="SharedSignal01",
        namespace="variable",
        asset_kind="signal",
        country_code="CN",
        user_override=True,
    )

    assert result["severity"] == "warning"
    assert result["hard_constraint"] is False
    assert result["safe_name"].endswith("_variable")
    assert result["override_mapping"]["requested_name"] == "SharedSignal01"
    assert result["override_mapping"]["safe_name"] == result["safe_name"]
    assert result["canonical_target"] == "SharedSignal01"
    assert result["reason"] == "Keep variable names distinct from VTD snapshot identifiers."


def test_resolve_vtd_name_ignores_override_for_hard_runtime_asset_constraint(
    sample_vtd_knowledge_base,
) -> None:
    tool = build_resolve_vtd_name_tool(sample_vtd_knowledge_base)

    result = tool(
        name="Sg101Gefahrstelle01.flt",
        namespace="runtime_asset",
        asset_kind="signal",
        country_code="CN",
        user_override=True,
    )

    assert result["severity"] == "info"
    assert result["rule_kind"] == "alias"
    assert result["hard_constraint"] is True
    assert result["canonical_target"] == "CN_Sg101_Gefahrenstelle01"
    assert result["reason"]
    assert result["source_paths"] == [_CN_SIGNAL_SOURCE_PATH]
    assert "override_mapping" not in result


def test_resolve_vtd_name_returns_warning_for_soft_namespace_approximate_collision(
) -> None:
    tool = build_resolve_vtd_name_tool(_build_approximate_asset_kind_knowledge_base())

    result = tool(
        name="SharedRoad",
        namespace="external_object",
        asset_kind="style",
    )

    assert result["normalized_name"] == "SharedRoad"
    assert result["severity"] == "warning"
    assert result["rule_kind"] == "approximate_match"
    assert result["hard_constraint"] is False
    assert result["canonical_target"] == "SharedRoadStyle"
    assert result["alternatives"] == ["SharedRoadStyle"]
    assert result["reason"]
    assert "safe_name" not in result
    assert "override_mapping" not in result


def test_resolve_vtd_name_ignores_exact_rule_match_when_asset_kind_scope_differs() -> None:
    tool = build_resolve_vtd_name_tool(_build_mismatched_rule_scope_knowledge_base())

    result = tool(
        name="ScopedSharedName",
        namespace="scenario_object",
        asset_kind="vehicle",
        country_code="CN",
    )

    assert result["severity"] == "info"
    assert result["rule_kind"] == "no_match"
    assert result["hard_constraint"] is False
    assert result["canonical_target"] == "ScopedSharedName"
    assert result["alternatives"] == []
    assert result["source_paths"] == []


def test_resolve_vtd_name_prefers_materialized_name_policy_before_fallback() -> None:
    tool = build_resolve_vtd_name_tool(_build_materialized_policy_knowledge_base())

    result = tool(
        name="SharedSignalAliasCN",
        namespace="scenario_object",
        asset_kind="signal",
        country_code="PRC",
    )

    assert result["severity"] == "warning"
    assert result["rule_kind"] == "reserved_name"
    assert result["hard_constraint"] is False
    assert result["canonical_target"] == "SharedSignal01"
    assert result["safe_name"] == "SharedSignalAliasCN_scenario_object"
    assert result["reason"] == "Materialized scenario object policy."
    assert result["source_paths"] == [
        "knowledge/structured/vtd/semantic/name-policies.jsonl#policy-sharedsignalaliascn-cn"
    ]


def test_resolve_vtd_name_matches_materialized_policy_for_usa_alias_country_query(
) -> None:
    tool = build_resolve_vtd_name_tool(
        _build_materialized_policy_knowledge_base(
            canonical_country="US",
            country_aliases=["us", "usa"],
            requested_name="SharedSignalAliasUS",
            country_query="USA",
        )
    )

    result = tool(
        name="SharedSignalAliasUS",
        namespace="scenario_object",
        asset_kind="signal",
        country_code="USA",
    )

    assert result["severity"] == "warning"
    assert result["rule_kind"] == "reserved_name"
    assert result["hard_constraint"] is False
    assert result["canonical_target"] == "SharedSignal01"
    assert result["safe_name"] == "SharedSignalAliasUS_scenario_object"
    assert result["reason"] == "Materialized scenario object policy."
    assert result["source_paths"] == [
        "knowledge/structured/vtd/semantic/name-policies.jsonl#policy-sharedsignalaliasus-us"
    ]


_CN_SHARED_SOURCE_PATH = (
    "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Models/AddOns/CountryCN/SetupFiles/"
    "TT_SIGNALS_ADD_COUNTRYCN.DAT#L1"
)
_VARIABLE_RULE_SOURCE_PATH = (
    "Tools/RodDistro_6980_Rod4.6.1/VisualLib/Models/AddOns/CountryCN/SetupFiles/"
    "TT_SIGNALS_ADD_COUNTRYCN.DAT#L9"
)


def _build_soft_rule_knowledge_base() -> VtdKnowledgeBase:
    shared_signal = _make_asset(
        asset_id="signal:CN:SharedSignal01",
        asset_kind="signal",
        canonical_name="SharedSignal01",
        source_path=_CN_SHARED_SOURCE_PATH,
        country_codes=["CN"],
    )
    scenario_rule = _make_rule(
        name="reserved-scenario-object-sharedsignal01-cn",
        canonical_target="SharedSignal01",
        asset_kind="signal",
        namespace="scenario_object",
        country_code="CN",
        severity="warning",
        reason="Avoid existing scenario object names from the VTD snapshot.",
        source_path=_CN_SHARED_SOURCE_PATH,
    )
    variable_rule = _make_rule(
        name="reserved-variable-sharedsignal01-cn",
        canonical_target="SharedSignal01",
        asset_kind="signal",
        namespace="variable",
        country_code="CN",
        severity="warning",
        reason="Keep variable names distinct from VTD snapshot identifiers.",
        source_path=_VARIABLE_RULE_SOURCE_PATH,
    )
    return _build_knowledge_base(
        assets=[shared_signal],
        rules=[scenario_rule, variable_rule],
    )


def _build_mismatched_rule_scope_knowledge_base() -> VtdKnowledgeBase:
    rule = _make_rule(
        name="reserved-scenario-object-scopedsharedname-cn",
        canonical_target="ScopedSharedName",
        asset_kind="signal",
        namespace="scenario_object",
        country_code="CN",
        severity="warning",
        reason="signal-only scope",
        source_path=_CN_SHARED_SOURCE_PATH,
    )
    return _build_knowledge_base(assets=[], rules=[rule])


def _build_approximate_asset_kind_knowledge_base() -> VtdKnowledgeBase:
    signal_asset = _make_asset(
        asset_id="signal:global:SharedRoadSignal",
        asset_kind="signal",
        canonical_name="SharedRoadSignal",
        source_path="Tools/RodDistro_6980_Rod4.6.1/signals/SharedRoadSignal.flt#L1",
    )
    style_asset = _make_asset(
        asset_id="style:global:SharedRoadStyle",
        asset_kind="style",
        canonical_name="SharedRoadStyle",
        source_path="Tools/RodDistro_6980_Rod4.6.1/styles/SharedRoadStyle.attr#L1",
    )
    return _build_knowledge_base(assets=[signal_asset, style_asset], rules=[])


def _build_materialized_policy_knowledge_base(
    *,
    canonical_country: str = "CN",
    country_aliases: list[str] | None = None,
    requested_name: str = "SharedSignalAliasCN",
    country_query: str | None = None,
) -> VtdKnowledgeBase:
    asset = _make_asset(
        asset_id=f"signal:{canonical_country}:SharedSignal01",
        asset_kind="signal",
        canonical_name="SharedSignal01",
        source_path=_CN_SHARED_SOURCE_PATH,
        country_codes=[canonical_country],
    )
    asset.aliases = [requested_name]
    normalized_alias_set = {canonical_country.casefold()}
    for alias in country_aliases or []:
        normalized_alias_set.add(alias.casefold())
    if country_query:
        normalized_alias_set.add(country_query.casefold())
    normalized_aliases = sorted(normalized_alias_set)
    policy_id_suffix = canonical_country.casefold()
    policy_id = f"policy-{requested_name.casefold()}-{policy_id_suffix}"
    metadata = {
        "country_taxonomy": {
            "version": 1,
            "countries": {
                canonical_country: {
                    "canonical_code": canonical_country,
                    "observed_values": [canonical_country],
                    "aliases": normalized_aliases,
                }
            },
            "alias_to_country": {
                alias: canonical_country for alias in normalized_aliases
            },
        },
        "name_policies": [
            {
                "policy_id": policy_id,
                "namespace": "scenario_object",
                "asset_kind": "signal",
                "country_scope": canonical_country,
                "rule_kind": "reserved_name",
                "severity": "warning",
                "match_mode": "exact",
                "match_name": requested_name,
                "canonical_target": "SharedSignal01",
                "safe_name_strategy": "append_namespace",
                "reason": "Materialized scenario object policy.",
                "source_paths": [
                    f"knowledge/structured/vtd/semantic/name-policies.jsonl#{policy_id}"
                ],
            }
        ],
    }
    return _build_knowledge_base(assets=[asset], rules=[], metadata=metadata)


def _build_knowledge_base(
    *,
    assets: list[VtdAssetRecord],
    rules: list[VtdNameRule],
    metadata: dict[str, object] | None = None,
) -> VtdKnowledgeBase:
    return VtdKnowledgeBase(
        runtime_root="tests/runtime",
        assets_by_id={asset.asset_id: asset for asset in assets},
        assets_by_canonical_name=_group_assets_by_canonical_name(assets),
        rules_by_name={rule.name: rule for rule in rules},
        sources=[SourceEntry(id="vtd-runtime", kind="runtime", path="knowledge/structured/vtd")],
        metadata={"source_id": "vtd-runtime", **({} if metadata is None else metadata)},
    )


def _group_assets_by_canonical_name(
    assets: list[VtdAssetRecord],
) -> dict[str, list[VtdAssetRecord]]:
    grouped: dict[str, list[VtdAssetRecord]] = {}
    for asset in assets:
        grouped.setdefault(asset.canonical_name, []).append(asset)
    return grouped


def _make_asset(
    *,
    asset_id: str,
    asset_kind: str,
    canonical_name: str,
    source_path: str,
    country_codes: list[str] | None = None,
) -> VtdAssetRecord:
    return VtdAssetRecord(
        asset_id=asset_id,
        asset_kind=asset_kind,
        canonical_name=canonical_name,
        display_name=canonical_name,
        filename=f"{canonical_name}.flt",
        relative_path=f"Tools/RodDistro_6980_Rod4.6.1/{canonical_name}.flt",
        source_path=source_path,
        group_path="test-group",
        runtime_family=asset_kind,
        aliases=[],
        country_codes=[] if country_codes is None else country_codes,
        variant_tags=[],
        metadata={},
    )


def _make_rule(
    *,
    name: str,
    canonical_target: str,
    asset_kind: str,
    namespace: str,
    country_code: str,
    severity: str,
    reason: str,
    source_path: str,
) -> VtdNameRule:
    return VtdNameRule(
        name=name,
        rule_kind="reserved_name",
        severity=severity,
        canonical_target=canonical_target,
        asset_kind=asset_kind,
        reason=reason,
        source_path=source_path,
        scope={
            "namespace": namespace,
            "asset_kind": asset_kind,
            "country_code": country_code,
        },
        metadata={},
    )
