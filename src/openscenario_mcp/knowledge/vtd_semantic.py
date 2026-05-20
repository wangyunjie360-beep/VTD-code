from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any

from openscenario_mcp.models import (
    SourceEntry,
    VtdAssetFamily,
    VtdAssetVariant,
    VtdKnowledgeBase,
    VtdNamePolicy,
    VtdSemanticKnowledgeBase,
)

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_SEMANTIC_SOURCE_PATH = "knowledge/structured/vtd/semantic"


def build_vtd_semantic_knowledge_base(
    knowledge_base: VtdKnowledgeBase,
) -> tuple[VtdSemanticKnowledgeBase, list[dict[str, Any]]]:
    families_by_id: dict[str, VtdAssetFamily] = {}
    variants_by_id: dict[str, VtdAssetVariant] = {}
    provenance_records: list[dict[str, Any]] = []

    for asset_kind, canonical_name, assets in _iter_family_groups(knowledge_base):
        family_id = _family_id(asset_kind, canonical_name)
        variants: list[VtdAssetVariant] = []
        for asset in assets:
            variant = _build_variant(asset, family_id)
            variants.append(variant)
            variants_by_id[variant.variant_id] = variant
            provenance_records.append(_build_provenance_record(asset, variant))

        families_by_id[family_id] = VtdAssetFamily(
            family_id=family_id,
            canonical_key=canonical_name,
            asset_kind=asset_kind,
            preferred_variant_id=variants[0].variant_id,
            variant_ids=[variant.variant_id for variant in variants],
            country_scopes=_dedupe(
                variant.country_scope for variant in variants if variant.country_scope
            ),
            semantic_tags=_dedupe(
                tag for variant in variants for tag in variant.usage_tags
            ),
            selection_policy="prefer_exact_country",
            notes=[],
        )

    name_policies_by_id = {
        policy.policy_id: policy
        for policy in _load_name_policies(knowledge_base)
    }
    semantic_knowledge_base = VtdSemanticKnowledgeBase(
        families_by_id=families_by_id,
        variants_by_id=variants_by_id,
        name_policies_by_id=name_policies_by_id,
        sources=[
            SourceEntry(
                id="vtd-semantic",
                kind="semantic",
                path=_SEMANTIC_SOURCE_PATH,
            )
        ],
        metadata={
            "status": "loaded",
            "exists": True,
            "family_count": len(families_by_id),
            "variant_count": len(variants_by_id),
            "provenance_count": len(provenance_records),
        },
    )
    return semantic_knowledge_base, provenance_records


def serialize_vtd_semantic_knowledge_base(
    knowledge_base: VtdSemanticKnowledgeBase,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    families = [
        asdict(family)
        for family in sorted(
            knowledge_base.families_by_id.values(),
            key=lambda family: (family.asset_kind, family.canonical_key.casefold()),
        )
    ]
    variants = [
        asdict(variant)
        for variant in sorted(
            knowledge_base.variants_by_id.values(),
            key=lambda variant: (
                variant.family_id,
                variant.country_scope,
                variant.variant_id,
            ),
        )
    ]
    name_policies = [
        asdict(policy)
        for policy in sorted(
            knowledge_base.name_policies_by_id.values(),
            key=lambda policy: (
                policy.namespace,
                policy.asset_kind,
                policy.country_scope,
                policy.policy_id,
            ),
        )
    ]
    return families, variants, name_policies


def _iter_family_groups(
    knowledge_base: VtdKnowledgeBase,
) -> list[tuple[str, str, list[Any]]]:
    grouped: list[tuple[str, str, list[Any]]] = []
    for canonical_name, assets in knowledge_base.assets_by_canonical_name.items():
        sorted_assets = sorted(
            assets,
            key=lambda asset: (
                asset.asset_kind,
                _country_scope(asset.country_codes),
                asset.asset_id,
            ),
        )
        if not sorted_assets:
            continue
        grouped.append(
            (
                sorted_assets[0].asset_kind,
                canonical_name,
                sorted_assets,
            )
        )
    grouped.sort(key=lambda item: (item[0], item[1].casefold()))
    return grouped


def _build_variant(asset: Any, family_id: str) -> VtdAssetVariant:
    country_scope = _country_scope(asset.country_codes)
    return VtdAssetVariant(
        variant_id=_variant_id(asset.asset_id),
        family_id=family_id,
        asset_id=asset.asset_id,
        country_scope=country_scope,
        variant_tags=list(asset.variant_tags),
        source_type=_source_type(asset.metadata),
        source_rank=_source_rank(asset),
        referencable_as=_dedupe([asset.canonical_name, *asset.aliases, asset.filename]),
        usage_tags=_dedupe([asset.asset_kind, asset.runtime_family, *asset.variant_tags]),
        quality_flags=[] if asset.relative_path else ["missing_relative_path"],
    )


def _build_provenance_record(
    asset: Any,
    variant: VtdAssetVariant,
) -> dict[str, Any]:
    merged_source_paths = asset.metadata.get("merged_source_paths", [])
    if not isinstance(merged_source_paths, list):
        merged_source_paths = []
    return {
        "variant_id": variant.variant_id,
        "asset_id": asset.asset_id,
        "family_id": variant.family_id,
        "asset_kind": asset.asset_kind,
        "runtime_family": asset.runtime_family,
        "country_scope": variant.country_scope,
        "source_path": asset.source_path,
        "relative_path": asset.relative_path,
        "merged_source_paths": [
            source_path
            for source_path in merged_source_paths
            if isinstance(source_path, str) and source_path.strip()
        ],
    }


def _load_name_policies(knowledge_base: VtdKnowledgeBase) -> list[VtdNamePolicy]:
    raw_policies = knowledge_base.metadata.get("name_policies", [])
    if not isinstance(raw_policies, list):
        return []

    policies: list[VtdNamePolicy] = []
    for policy in raw_policies:
        if not isinstance(policy, dict):
            continue
        policies.append(
            VtdNamePolicy(
                policy_id=str(policy.get("policy_id", "")).strip(),
                namespace=str(policy.get("namespace", "")).strip(),
                asset_kind=str(policy.get("asset_kind", "")).strip(),
                country_scope=str(policy.get("country_scope", "")).strip(),
                rule_kind=str(policy.get("rule_kind", "")).strip(),
                severity=str(policy.get("severity", "")).strip(),
                match_mode=str(policy.get("match_mode", "")).strip(),
                canonical_target=str(policy.get("canonical_target", "")).strip(),
                safe_name_strategy=str(policy.get("safe_name_strategy", "")).strip(),
                reason=str(policy.get("reason", "")).strip(),
                source_paths=[
                    source_path
                    for source_path in policy.get("source_paths", [])
                    if isinstance(source_path, str) and source_path.strip()
                ],
            )
        )
    return policies


def _family_id(asset_kind: str, canonical_name: str) -> str:
    return f"{asset_kind}-family:{_slug(canonical_name)}"


def _variant_id(asset_id: str) -> str:
    return f"variant:{_slug(asset_id)}"


def _country_scope(country_codes: list[str]) -> str:
    if not country_codes:
        return ""
    return "+".join(sorted(country_codes))


def _source_type(metadata: dict[str, Any]) -> str:
    return str(
        metadata.get("definition_kind")
        or metadata.get("config_kind")
        or "phase1_asset"
    ).strip()


def _source_rank(asset: Any) -> int:
    return 10 if asset.relative_path else 0


def _slug(value: str) -> str:
    slug = _NON_ALNUM_RE.sub("", value.casefold())
    return slug or "value"


def _dedupe(values: list[str] | Any) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        text = value.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


__all__ = [
    "build_vtd_semantic_knowledge_base",
    "serialize_vtd_semantic_knowledge_base",
]
