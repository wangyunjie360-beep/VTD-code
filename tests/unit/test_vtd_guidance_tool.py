from __future__ import annotations

import openscenario_mcp.tools.vtd_guidance as vtd_guidance_module
from openscenario_mcp.models import VtdKnowledgeBase
from openscenario_mcp.tools.vtd_guidance import build_vtd_guidance_tool


def test_build_vtd_guidance_only_composes_retrieve_and_resolve(
    monkeypatch,
) -> None:
    knowledge_base = VtdKnowledgeBase()
    calls: list[tuple[str, dict[str, object]]] = []
    retrieve_payload = {
        "query": "cn signal",
        "hits": [{"canonical_name": "CN_Sg101_Gefahrenstelle01"}],
    }
    resolve_payload = {
        "normalized_name": "signal_1",
        "severity": "high",
        "hard_constraint": False,
    }

    def fake_build_retrieve_vtd_asset_tool(_knowledge_base: VtdKnowledgeBase):
        assert _knowledge_base is knowledge_base

        def _tool(
            *,
            query: str,
            asset_kind: str | None = None,
            country_code: str | None = None,
            top_k: int = 5,
        ) -> dict[str, object]:
            calls.append(
                (
                    "retrieve",
                    {
                        "query": query,
                        "asset_kind": asset_kind,
                        "country_code": country_code,
                        "top_k": top_k,
                    },
                )
            )
            return retrieve_payload

        return _tool

    def fake_build_resolve_vtd_name_tool(_knowledge_base: VtdKnowledgeBase):
        assert _knowledge_base is knowledge_base

        def _tool(
            *,
            name: str,
            namespace: str,
            asset_kind: str,
            country_code: str | None = None,
            user_override: bool = False,
        ) -> dict[str, object]:
            calls.append(
                (
                    "resolve",
                    {
                        "name": name,
                        "namespace": namespace,
                        "asset_kind": asset_kind,
                        "country_code": country_code,
                        "user_override": user_override,
                    },
                )
            )
            return resolve_payload

        return _tool

    monkeypatch.setattr(
        vtd_guidance_module,
        "build_retrieve_vtd_asset_tool",
        fake_build_retrieve_vtd_asset_tool,
    )
    monkeypatch.setattr(
        vtd_guidance_module,
        "build_resolve_vtd_name_tool",
        fake_build_resolve_vtd_name_tool,
    )

    tool = build_vtd_guidance_tool(knowledge_base)
    result = tool(
        query="cn signal",
        name="signal_1",
        namespace="scenario_object",
        asset_kind="vehicle",
        country_code="CN",
        user_override=True,
        top_k=2,
    )

    assert calls == [
        (
            "retrieve",
            {
                "query": "cn signal",
                "asset_kind": "vehicle",
                "country_code": "CN",
                "top_k": 2,
            },
        ),
        (
            "resolve",
            {
                "name": "signal_1",
                "namespace": "scenario_object",
                "asset_kind": "vehicle",
                "country_code": "CN",
                "user_override": True,
            },
        ),
    ]
    assert result == {
        "query": "cn signal",
        "name": "signal_1",
        "namespace": "scenario_object",
        "asset_kind": "vehicle",
        "country_code": "CN",
        "user_override": True,
        "asset_lookup": retrieve_payload,
        "name_resolution": resolve_payload,
    }
