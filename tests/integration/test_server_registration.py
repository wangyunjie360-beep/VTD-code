import asyncio
import builtins
import importlib
import sys

from openscenario_mcp.runtime import build_runtime_for_tests


def test_build_server_keeps_task5_runtime_and_core_tools_available() -> None:
    runtime = build_runtime_for_tests()
    assert runtime.vtd_knowledge_base.assets_by_canonical_name

    build_server = importlib.import_module("openscenario_mcp.server").build_server
    server = build_server(runtime)
    tool_names = sorted(tool.name for tool in asyncio.run(server.list_tools()))

    assert {
        "build_generation_packet",
        "build_vtd_guidance",
        "recommend_vtd_candidates",
        "retrieve_schema_subgraph",
        "explain_validation_errors",
        "check_xml_intent_consistency",
        "get_element_schema",
        "normalize_scenario_intent",
        "resolve_vtd_name",
        "retrieve_spec",
        "retrieve_vtd_asset",
        "validate_xml",
    }.issubset(tool_names)


def test_build_server_skips_optional_xml_guidance_when_module_is_missing(
    monkeypatch,
) -> None:
    runtime = build_runtime_for_tests()
    original_import = builtins.__import__

    def fail_guidance_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "openscenario_mcp.tools.guidance":
            raise ImportError("guidance module unavailable")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fail_guidance_import)
    sys.modules.pop("openscenario_mcp.server", None)
    sys.modules.pop("openscenario_mcp.tools.guidance", None)

    server_module = importlib.import_module("openscenario_mcp.server")
    server = server_module.build_server(runtime)
    tool_names = sorted(tool.name for tool in asyncio.run(server.list_tools()))

    assert {
        "build_generation_packet",
        "build_vtd_guidance",
        "recommend_vtd_candidates",
        "retrieve_schema_subgraph",
        "explain_validation_errors",
        "check_xml_intent_consistency",
        "get_element_schema",
        "normalize_scenario_intent",
        "resolve_vtd_name",
        "retrieve_spec",
        "retrieve_vtd_asset",
        "validate_xml",
    }.issubset(tool_names)
    assert "build_xml_guidance" not in tool_names
