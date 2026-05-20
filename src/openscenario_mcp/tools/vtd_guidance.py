from __future__ import annotations

from typing import Any

from openscenario_mcp.models import VtdKnowledgeBase
from openscenario_mcp.tools.resolve_vtd_name import build_resolve_vtd_name_tool
from openscenario_mcp.tools.retrieve_vtd_asset import build_retrieve_vtd_asset_tool


def build_vtd_guidance_tool(knowledge_base: VtdKnowledgeBase):
    retrieve_vtd_asset = build_retrieve_vtd_asset_tool(knowledge_base)
    resolve_vtd_name = build_resolve_vtd_name_tool(knowledge_base)

    def build_vtd_guidance(
        query: str,
        name: str,
        namespace: str,
        asset_kind: str,
        country_code: str | None = None,
        user_override: bool = False,
        top_k: int = 5,
    ) -> dict[str, Any]:
        asset_lookup = retrieve_vtd_asset(
            query=query,
            asset_kind=asset_kind,
            country_code=country_code,
            top_k=top_k,
        )
        name_resolution = resolve_vtd_name(
            name=name,
            namespace=namespace,
            asset_kind=asset_kind,
            country_code=country_code,
            user_override=user_override,
        )

        return {
            "query": query,
            "name": name,
            "namespace": namespace,
            "asset_kind": asset_kind,
            "country_code": country_code,
            "user_override": user_override,
            "asset_lookup": asset_lookup,
            "name_resolution": name_resolution,
        }

    return build_vtd_guidance


__all__ = ["build_vtd_guidance_tool"]
