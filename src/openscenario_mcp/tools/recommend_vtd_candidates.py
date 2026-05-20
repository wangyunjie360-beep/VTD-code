from __future__ import annotations

from typing import Any

from openscenario_mcp.knowledge.vtd_search import search_vtd_assets
from openscenario_mcp.models import VtdKnowledgeBase
from openscenario_mcp.tools.resolve_vtd_name import build_resolve_vtd_name_tool
from openscenario_mcp.tools.retrieve_vtd_asset import build_retrieve_vtd_asset_tool


def build_recommend_vtd_candidates_tool(knowledge_base: VtdKnowledgeBase):
    retrieve_vtd_asset = build_retrieve_vtd_asset_tool(knowledge_base)
    resolve_vtd_name = build_resolve_vtd_name_tool(knowledge_base)

    def recommend_vtd_candidates(
        query: str,
        asset_kind: str,
        namespace: str,
        country_code: str | None = None,
        requested_name: str | None = None,
        draft_names: list[str] | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        asset_lookup = retrieve_vtd_asset(
            query=query,
            asset_kind=asset_kind,
            country_code=country_code,
            top_k=top_k,
        )
        resolved_name = resolve_vtd_name(
            name=requested_name or query,
            namespace=namespace,
            asset_kind=asset_kind,
            country_code=country_code,
        )

        recommended = asset_lookup["hits"][:1]
        fallbacks = asset_lookup["hits"][1:]
        return {
            "recommended": recommended,
            "fallbacks": fallbacks,
            "rejected": [],
            "name_resolution": resolved_name,
            "ranking_reasons": [
                {
                    "query": query,
                    "requested_name": requested_name or query,
                    "draft_names": list(draft_names or []),
                    "match_fields": [hit["match_field"] for hit in asset_lookup["hits"]],
                    "resolution_reason": resolved_name["reason"],
                }
            ],
            "source_paths": _unique(
                [
                    *(hit["source_path"] for hit in asset_lookup["hits"]),
                    *resolved_name.get("source_paths", []),
                ]
            ),
        }

    return recommend_vtd_candidates


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        text = value.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


__all__ = ["build_recommend_vtd_candidates_tool"]
