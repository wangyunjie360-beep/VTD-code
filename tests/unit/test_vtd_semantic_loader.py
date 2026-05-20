from __future__ import annotations

from pathlib import Path
from typing import get_type_hints

from openscenario_mcp.config import get_project_root
from openscenario_mcp.knowledge.vtd_semantic import build_vtd_semantic_knowledge_base
from openscenario_mcp.models import (
    KnowledgeBase,
    OscVtdBridgeKnowledgeBase,
    VtdKnowledgeBase,
    VtdSemanticKnowledgeBase,
)
from openscenario_mcp.runtime import (
    Runtime,
    _SEMANTIC_RELATIVE_PATH,
    _build_runtime,
    _load_vtd_semantic_knowledge_base,
)
from openscenario_mcp.validator.adapter import ValidatorAdapter


def test_phase2_semantic_output_directory_is_reserved_under_project_root() -> None:
    project_root = get_project_root()

    assert _SEMANTIC_RELATIVE_PATH.as_posix() == "knowledge/structured/vtd/semantic"
    assert (project_root / _SEMANTIC_RELATIVE_PATH).is_dir()


def test_runtime_loads_non_optional_semantic_layer_when_outputs_exist(
    sample_project_root: Path,
) -> None:
    runtime_hints = get_type_hints(Runtime)
    runtime = _build_runtime(project_root=sample_project_root)
    semantic_root = sample_project_root / _SEMANTIC_RELATIVE_PATH

    assert runtime_hints["vtd_semantic_knowledge_base"] is VtdSemanticKnowledgeBase
    assert isinstance(runtime.vtd_semantic_knowledge_base, VtdSemanticKnowledgeBase)
    assert runtime.vtd_semantic_knowledge_base.families_by_id
    assert runtime.vtd_semantic_knowledge_base.variants_by_id
    assert runtime.vtd_semantic_knowledge_base.name_policies_by_id
    assert runtime.vtd_semantic_knowledge_base.sources[0].path == (
        "knowledge/structured/vtd/semantic"
    )
    assert runtime.vtd_semantic_knowledge_base.metadata["status"] == "loaded"
    assert runtime.vtd_semantic_knowledge_base.metadata["exists"] is True
    assert Path(runtime.vtd_semantic_knowledge_base.metadata["root"]) == semantic_root


def test_semantic_placeholder_loader_stays_stable_when_directory_is_missing(
    tmp_path: Path,
) -> None:
    semantic_knowledge_base = _load_vtd_semantic_knowledge_base(tmp_path)

    assert isinstance(semantic_knowledge_base, VtdSemanticKnowledgeBase)
    assert semantic_knowledge_base.families_by_id == {}
    assert semantic_knowledge_base.variants_by_id == {}
    assert semantic_knowledge_base.name_policies_by_id == {}
    assert semantic_knowledge_base.sources[0].id == "vtd-semantic"
    assert semantic_knowledge_base.sources[0].kind == "semantic"
    assert semantic_knowledge_base.sources[0].path == "knowledge/structured/vtd/semantic"
    assert semantic_knowledge_base.metadata["status"] == "placeholder"
    assert semantic_knowledge_base.metadata["exists"] is False
    assert Path(semantic_knowledge_base.metadata["root"]) == tmp_path / _SEMANTIC_RELATIVE_PATH


def test_runtime_keeps_legacy_positional_construction_order() -> None:
    runtime = Runtime(
        KnowledgeBase(),
        VtdKnowledgeBase(),
        [],
        ValidatorAdapter(),
    )

    assert runtime.patterns == []
    assert isinstance(runtime.validator, ValidatorAdapter)
    assert isinstance(runtime.vtd_semantic_knowledge_base, VtdSemanticKnowledgeBase)
    assert isinstance(runtime.osc_vtd_bridge_knowledge_base, OscVtdBridgeKnowledgeBase)
    assert runtime.vtd_semantic_knowledge_base.metadata["status"] == "placeholder"
    assert runtime.vtd_semantic_knowledge_base.metadata["exists"] is False
    assert runtime.osc_vtd_bridge_knowledge_base.metadata["status"] == "placeholder"
    assert runtime.osc_vtd_bridge_knowledge_base.metadata["exists"] is False


def test_build_vtd_semantic_knowledge_base_groups_shared_signal_variants(
    sample_vtd_knowledge_base: VtdKnowledgeBase,
) -> None:
    semantic_knowledge_base, provenance_records = build_vtd_semantic_knowledge_base(
        sample_vtd_knowledge_base
    )

    family = semantic_knowledge_base.families_by_id["signal-family:sharedsignal01"]

    assert len(family.variant_ids) == 2
    assert family.preferred_variant_id in family.variant_ids
    assert {semantic_knowledge_base.variants_by_id[variant_id].country_scope for variant_id in family.variant_ids} == {
        "CN",
        "DE",
    }
    assert provenance_records
