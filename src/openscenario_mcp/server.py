from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from openscenario_mcp.tools.build_generation_packet import (
    build_generation_packet_tool,
)
from openscenario_mcp.config import DEFAULT_SCHEMA_VERSION
from openscenario_mcp.runtime import Runtime
from openscenario_mcp.tools.check_xml_intent_consistency import (
    build_check_xml_intent_consistency_tool,
)
from openscenario_mcp.tools.diagnostics import build_explain_validation_errors_tool
from openscenario_mcp.tools.normalize_scenario_intent import (
    build_normalize_scenario_intent_tool,
)
from openscenario_mcp.tools.recommend_vtd_candidates import (
    build_recommend_vtd_candidates_tool,
)
from openscenario_mcp.tools.resolve_vtd_name import build_resolve_vtd_name_tool
from openscenario_mcp.tools.retrieve_schema_subgraph import (
    build_retrieve_schema_subgraph_tool,
)
from openscenario_mcp.tools.retrieve_vtd_asset import build_retrieve_vtd_asset_tool
from openscenario_mcp.tools.retrieve_spec import build_retrieve_spec_tool
from openscenario_mcp.tools.schema import build_get_element_schema_tool
from openscenario_mcp.tools.summarize_validation_repairs import (
    build_summarize_validation_repairs_tool,
)
from openscenario_mcp.tools.validate import build_validate_xml_tool
from openscenario_mcp.tools.vtd_guidance import build_vtd_guidance_tool


def build_server(runtime: Runtime) -> FastMCP:
    mcp = FastMCP("openscenario-mcp", json_response=True)

    retrieve_spec_impl = build_retrieve_spec_tool(runtime.knowledge_base, runtime.patterns)
    retrieve_vtd_asset_impl = build_retrieve_vtd_asset_tool(runtime.vtd_knowledge_base)
    resolve_vtd_name_impl = build_resolve_vtd_name_tool(runtime.vtd_knowledge_base)
    normalize_scenario_intent_impl = build_normalize_scenario_intent_tool()
    check_xml_intent_consistency_impl = build_check_xml_intent_consistency_tool()
    build_generation_packet_impl = build_generation_packet_tool(runtime)
    retrieve_schema_subgraph_impl = build_retrieve_schema_subgraph_tool(
        runtime.knowledge_base
    )
    recommend_vtd_candidates_impl = build_recommend_vtd_candidates_tool(
        runtime.vtd_knowledge_base
    )
    get_element_schema_impl = build_get_element_schema_tool(runtime.knowledge_base)
    summarize_validation_repairs_impl = build_summarize_validation_repairs_tool(
        runtime.patterns
    )
    build_vtd_guidance_impl = build_vtd_guidance_tool(runtime.vtd_knowledge_base)
    validate_xml_impl = build_validate_xml_tool(runtime.validator)
    explain_validation_errors_impl = build_explain_validation_errors_tool(runtime.patterns)
    build_xml_guidance_impl = _load_optional_xml_guidance_tool(runtime)

    @mcp.tool(name="retrieve_spec")
    def retrieve_spec(
        query: str,
        kind: str | None = None,
        top_k: int = 5,
        parent_context: str | None = None,
    ) -> dict[str, Any]:
        return retrieve_spec_impl(
            query=query,
            kind=kind,
            top_k=top_k,
            parent_context=parent_context,
        )

    @mcp.tool(name="retrieve_vtd_asset")
    def retrieve_vtd_asset(
        query: str,
        asset_kind: str | None = None,
        country_code: str | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        return retrieve_vtd_asset_impl(
            query=query,
            asset_kind=asset_kind,
            country_code=country_code,
            top_k=top_k,
        )

    @mcp.tool(name="resolve_vtd_name")
    def resolve_vtd_name(
        name: str,
        namespace: str,
        asset_kind: str,
        country_code: str | None = None,
        user_override: bool = False,
    ) -> dict[str, Any]:
        return resolve_vtd_name_impl(
            name=name,
            namespace=namespace,
            asset_kind=asset_kind,
            country_code=country_code,
            user_override=user_override,
        )

    @mcp.tool(name="normalize_scenario_intent")
    def normalize_scenario_intent(
        request: str,
        locale: str | None = None,
        draft_assumptions: list[str] | None = None,
    ) -> dict[str, Any]:
        return normalize_scenario_intent_impl(
            request=request,
            locale=locale,
            draft_assumptions=draft_assumptions,
        )

    @mcp.tool(name="check_xml_intent_consistency")
    def check_xml_intent_consistency(
        xml: str,
        intent: dict[str, Any],
        checklist: list[str] | None = None,
    ) -> dict[str, Any]:
        return check_xml_intent_consistency_impl(
            xml=xml,
            intent=intent,
            checklist=checklist,
        )

    @mcp.tool(name="build_generation_packet")
    def build_generation_packet(
        request: str,
        country_code: str | None = None,
        stage: str = "draft",
    ) -> dict[str, Any]:
        return build_generation_packet_impl(
            request=request,
            country_code=country_code,
            stage=stage,
        )

    @mcp.tool(name="retrieve_schema_subgraph")
    def retrieve_schema_subgraph(
        query: str,
        intent: dict[str, Any] | None = None,
        roots: list[str] | None = None,
        parent_context: str | None = None,
        depth: int = 2,
    ) -> dict[str, Any]:
        return retrieve_schema_subgraph_impl(
            query=query,
            intent=intent,
            roots=roots,
            parent_context=parent_context,
            depth=depth,
        )

    @mcp.tool(name="recommend_vtd_candidates")
    def recommend_vtd_candidates(
        query: str,
        asset_kind: str,
        namespace: str,
        country_code: str | None = None,
        requested_name: str | None = None,
        draft_names: list[str] | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        return recommend_vtd_candidates_impl(
            query=query,
            asset_kind=asset_kind,
            namespace=namespace,
            country_code=country_code,
            requested_name=requested_name,
            draft_names=draft_names,
            top_k=top_k,
        )

    @mcp.tool(name="build_vtd_guidance")
    def build_vtd_guidance(
        query: str,
        name: str,
        namespace: str,
        asset_kind: str,
        country_code: str | None = None,
        user_override: bool = False,
        top_k: int = 5,
    ) -> dict[str, Any]:
        return build_vtd_guidance_impl(
            query=query,
            name=name,
            namespace=namespace,
            asset_kind=asset_kind,
            country_code=country_code,
            user_override=user_override,
            top_k=top_k,
        )

    if build_xml_guidance_impl is not None:

        @mcp.tool(name="build_xml_guidance")
        def build_xml_guidance(
            query: str,
            element: str,
            parent_context: str | None = None,
            top_k: int = 3,
            errors: list[dict[str, Any]] | None = None,
        ) -> dict[str, Any]:
            return build_xml_guidance_impl(
                query=query,
                element=element,
                parent_context=parent_context,
                top_k=top_k,
                errors=errors,
            )

    @mcp.tool(name="get_element_schema")
    def get_element_schema(
        element: str,
        parent_context: str | None = None,
    ) -> dict[str, Any]:
        return get_element_schema_impl(element=element, parent_context=parent_context)

    @mcp.tool(name="validate_xml")
    def validate_xml(
        xml: str,
        schema_version: str = DEFAULT_SCHEMA_VERSION,
    ) -> dict[str, Any]:
        return validate_xml_impl(xml=xml, schema_version=schema_version)

    @mcp.tool(name="explain_validation_errors")
    def explain_validation_errors(errors: list[dict[str, Any]]) -> dict[str, Any]:
        return explain_validation_errors_impl(errors)

    @mcp.tool(name="summarize_validation_repairs")
    def summarize_validation_repairs(
        errors: list[dict[str, Any]],
        xml: str | None = None,
        intent: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return summarize_validation_repairs_impl(
            errors=errors,
            xml=xml,
            intent=intent,
        )

    return mcp


def _load_optional_xml_guidance_tool(runtime: Runtime):
    try:
        from openscenario_mcp.tools.guidance import build_xml_guidance_tool
    except ImportError:
        return None

    return build_xml_guidance_tool(
        runtime.knowledge_base,
        runtime.patterns,
    )
