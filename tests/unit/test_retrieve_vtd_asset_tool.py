from __future__ import annotations

from openscenario_mcp.tools.retrieve_vtd_asset import build_retrieve_vtd_asset_tool


def test_retrieve_vtd_asset_returns_snapshot_backed_canonical_and_alias_hits(
    sample_vtd_knowledge_base,
) -> None:
    tool = build_retrieve_vtd_asset_tool(sample_vtd_knowledge_base)

    result = tool(query="SharedSignal01", asset_kind="signal", top_k=3)

    assert result["query"] == "SharedSignal01"
    assert result["asset_kind"] == "signal"
    assert result["country_code"] is None
    assert [hit["asset_id"] for hit in result["hits"]] == [
        "signal:CN:SharedSignal01",
        "signal:DE:SharedSignal01",
        "signal:CN:DifferentSignal01",
    ]
    assert result["hits"][0]["canonical_name"] == "SharedSignal01"
    assert result["hits"][0]["aliases"] == ["SharedSignalAliasCN"]
    assert result["hits"][0]["source_path"].endswith("TT_SIGNALS_ADD_COUNTRYCN.DAT#L1")
    assert result["hits"][2]["canonical_name"] == "DifferentSignal01"
    assert result["hits"][2]["match_field"] == "alias"
    assert result["hits"][2]["matched_value"] == "SharedSignal01"


def test_retrieve_vtd_asset_matches_alias_from_snapshot_with_country_filter(
    sample_vtd_knowledge_base,
) -> None:
    tool = build_retrieve_vtd_asset_tool(sample_vtd_knowledge_base)

    result = tool(
        query="Sg101Gefahrstelle01.flt",
        asset_kind="signal",
        country_code="CN",
        top_k=2,
    )

    assert result["query"] == "Sg101Gefahrstelle01.flt"
    assert result["country_code"] == "CN"
    assert [hit["asset_id"] for hit in result["hits"]] == [
        "signal:CN:CN_Sg101_Gefahrenstelle01",
    ]
    assert result["hits"][0]["match_field"] == "alias"
    assert result["hits"][0]["matched_value"] == "Sg101Gefahrstelle01.flt"
    assert result["hits"][0]["canonical_name"] == "CN_Sg101_Gefahrenstelle01"
    assert result["hits"][0]["country_codes"] == ["CN"]
