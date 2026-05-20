from __future__ import annotations

from openscenario_mcp.tools.recommend_vtd_candidates import (
    build_recommend_vtd_candidates_tool,
)


def test_recommend_vtd_candidates_prefers_exact_country_and_policy_match(
    sample_vtd_knowledge_base,
) -> None:
    tool = build_recommend_vtd_candidates_tool(sample_vtd_knowledge_base)

    result = tool(
        query="Sg101Gefahrstelle01",
        asset_kind="signal",
        namespace="runtime_asset",
        country_code="CN",
        requested_name="Sg101Gefahrstelle01.flt",
        top_k=5,
    )

    assert result["recommended"][0]["canonical_name"] == "CN_Sg101_Gefahrenstelle01"
    assert result["name_resolution"]["canonical_target"] == "CN_Sg101_Gefahrenstelle01"
    assert result["ranking_reasons"]
