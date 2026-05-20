from __future__ import annotations

from typing import Any

from openscenario_mcp.knowledge.vtd_search import search_vtd_assets
from openscenario_mcp.models import VtdAssetRecord, VtdKnowledgeBase


def build_retrieve_vtd_asset_tool(knowledge_base: VtdKnowledgeBase):
    def retrieve_vtd_asset(
        query: str,
        asset_kind: str | None = None,
        country_code: str | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        hits = search_vtd_assets(
            query,
            knowledge_base,
            asset_kind=asset_kind,
            country_code=country_code,
            top_k=top_k,
        )

        return {
            "query": query,
            "asset_kind": asset_kind,
            "country_code": country_code,
            "top_k": top_k,
            "hits": [
                {
                    **_serialize_asset(hit.asset),
                    "score": hit.score,
                    "match_field": hit.match_field,
                    "matched_value": hit.matched_value,
                }
                for hit in hits
            ],
        }

    return retrieve_vtd_asset


def _serialize_asset(asset: VtdAssetRecord) -> dict[str, Any]:
    return {
        "asset_id": asset.asset_id,
        "asset_kind": asset.asset_kind,
        "canonical_name": asset.canonical_name,
        "display_name": asset.display_name,
        "filename": asset.filename,
        "relative_path": asset.relative_path,
        "source_path": asset.source_path,
        "group_path": asset.group_path,
        "runtime_family": asset.runtime_family,
        "aliases": list(asset.aliases),
        "country_codes": list(asset.country_codes),
        "variant_tags": list(asset.variant_tags),
        "metadata": dict(asset.metadata),
    }


__all__ = ["build_retrieve_vtd_asset_tool"]
