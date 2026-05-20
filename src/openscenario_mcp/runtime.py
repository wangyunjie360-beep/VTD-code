from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openscenario_mcp.config import get_project_root
from openscenario_mcp.knowledge.bridge_loader import load_osc_vtd_bridge
from openscenario_mcp.knowledge.loader import load_element_record
from openscenario_mcp.knowledge.vtd_loader import (
    load_vtd_semantic_snapshot,
    load_vtd_snapshot,
)
from openscenario_mcp.models import (
    KnowledgeBase,
    OscVtdBridgeKnowledgeBase,
    SourceEntry,
    VtdKnowledgeBase,
    VtdSemanticKnowledgeBase,
)
from openscenario_mcp.validator.adapter import ValidatorAdapter
from openscenario_mcp.validator.classifier import load_patterns

_ELEMENTS_RELATIVE_PATH = Path("knowledge") / "structured" / "elements"
_VTD_RELATIVE_PATH = Path("knowledge") / "structured" / "vtd"
_SEMANTIC_RELATIVE_PATH = _VTD_RELATIVE_PATH / "semantic"
_BRIDGE_RELATIVE_PATH = Path("knowledge") / "structured" / "bridges" / "osc_vtd"


def _build_vtd_semantic_placeholder(
    semantic_dir: Path | None = None,
) -> VtdSemanticKnowledgeBase:
    exists = semantic_dir.is_dir() if semantic_dir is not None else False
    root = semantic_dir.as_posix() if semantic_dir is not None else ""
    return VtdSemanticKnowledgeBase(
        sources=[
            SourceEntry(
                id="vtd-semantic",
                kind="semantic",
                path=_SEMANTIC_RELATIVE_PATH.as_posix(),
            )
        ],
        metadata={
            "root": root,
            "exists": exists,
            "status": "placeholder",
        },
    )


def _build_osc_vtd_bridge_placeholder(
    bridge_dir: Path | None = None,
) -> OscVtdBridgeKnowledgeBase:
    exists = bridge_dir.is_dir() if bridge_dir is not None else False
    root = bridge_dir.as_posix() if bridge_dir is not None else ""
    return OscVtdBridgeKnowledgeBase(
        sources=[
            SourceEntry(
                id="osc-vtd-bridge",
                kind="bridge",
                path=_BRIDGE_RELATIVE_PATH.as_posix(),
            )
        ],
        metadata={
            "root": root,
            "exists": exists,
            "status": "placeholder",
        },
    )


@dataclass(frozen=True, slots=True)
class Runtime:
    knowledge_base: KnowledgeBase
    vtd_knowledge_base: VtdKnowledgeBase
    patterns: list[dict[str, Any]]
    validator: ValidatorAdapter
    vtd_semantic_knowledge_base: VtdSemanticKnowledgeBase = field(
        default_factory=_build_vtd_semantic_placeholder
    )
    osc_vtd_bridge_knowledge_base: OscVtdBridgeKnowledgeBase = field(
        default_factory=_build_osc_vtd_bridge_placeholder
    )


def build_runtime_from_config() -> Runtime:
    return _build_runtime(project_root=get_project_root())


def build_runtime_for_tests() -> Runtime:
    return _build_runtime(project_root=get_project_root())


def _build_runtime(
    *,
    project_root: Path,
    validator: ValidatorAdapter | None = None,
) -> Runtime:
    return Runtime(
        knowledge_base=_load_knowledge_base(project_root),
        vtd_knowledge_base=_load_vtd_knowledge_base(project_root),
        vtd_semantic_knowledge_base=_load_vtd_semantic_knowledge_base(project_root),
        osc_vtd_bridge_knowledge_base=_load_osc_vtd_bridge_knowledge_base(project_root),
        patterns=list(load_patterns()),
        validator=validator or ValidatorAdapter(),
    )


def _load_knowledge_base(project_root: Path) -> KnowledgeBase:
    elements_dir = project_root / _ELEMENTS_RELATIVE_PATH
    if not elements_dir.is_dir():
        raise FileNotFoundError(
            f"Structured element directory not found at {elements_dir!s}."
        )

    records_by_element = {}
    for path in sorted(elements_dir.glob("*.json")):
        record = load_element_record(path)
        records_by_element[record.element] = record

    if not records_by_element:
        raise FileNotFoundError(f"No structured element records found in {elements_dir!s}.")

    return KnowledgeBase(records_by_element=records_by_element)


def _load_vtd_knowledge_base(project_root: Path) -> VtdKnowledgeBase:
    snapshot_dir = project_root / _VTD_RELATIVE_PATH
    if not snapshot_dir.is_dir():
        raise FileNotFoundError(
            f"Structured VTD snapshot directory not found at {snapshot_dir!s}."
        )

    try:
        return load_vtd_snapshot(snapshot_dir)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Structured VTD snapshot is incomplete under {snapshot_dir!s}: {exc}"
        ) from exc
    except ValueError as exc:
        raise ValueError(
            f"Failed to load structured VTD snapshot from {snapshot_dir!s}: {exc}"
        ) from exc


def _load_vtd_semantic_knowledge_base(project_root: Path) -> VtdSemanticKnowledgeBase:
    semantic_dir = project_root / _SEMANTIC_RELATIVE_PATH
    if not semantic_dir.is_dir():
        return _build_vtd_semantic_placeholder(semantic_dir)

    families_path = semantic_dir / "asset-families.jsonl"
    variants_path = semantic_dir / "asset-variants.jsonl"
    provenance_path = semantic_dir / "source-provenance.jsonl"
    if not (families_path.is_file() and variants_path.is_file() and provenance_path.is_file()):
        return _build_vtd_semantic_placeholder(semantic_dir)

    loaded = load_vtd_semantic_snapshot(project_root / _VTD_RELATIVE_PATH)
    return VtdSemanticKnowledgeBase(
        families_by_id=loaded.families_by_id,
        variants_by_id=loaded.variants_by_id,
        name_policies_by_id=loaded.name_policies_by_id,
        sources=loaded.sources,
        metadata={
            **loaded.metadata,
            "root": semantic_dir.as_posix(),
            "exists": True,
        },
    )


def _load_osc_vtd_bridge_knowledge_base(
    project_root: Path,
) -> OscVtdBridgeKnowledgeBase:
    bridge_dir = project_root / _BRIDGE_RELATIVE_PATH
    required_files = (
        bridge_dir / "field-bindings.jsonl",
        bridge_dir / "generation-policies.jsonl",
        bridge_dir / "guidance-recipes.jsonl",
    )
    if not bridge_dir.is_dir() or not all(path.is_file() for path in required_files):
        return _build_osc_vtd_bridge_placeholder(bridge_dir)

    loaded = load_osc_vtd_bridge(bridge_dir)
    return OscVtdBridgeKnowledgeBase(
        rules_by_id=loaded.rules_by_id,
        bindings_by_field=loaded.bindings_by_field,
        sources=loaded.sources,
        metadata={
            **loaded.metadata,
            "root": bridge_dir.as_posix(),
            "exists": True,
        },
    )
