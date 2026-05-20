from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from openscenario_mcp.knowledge.vtd_search import (
    _country_alias_map,
    _normalize_country_compare_code,
    search_vtd_assets,
)
from openscenario_mcp.models import VtdAssetRecord, VtdKnowledgeBase, VtdNameRule

_SOFT_NAMESPACES = {"scenario_object", "variable", "external_object"}
_SAFE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9_]+")


@dataclass(frozen=True, slots=True)
class _ExactAssetMatch:
    asset: VtdAssetRecord
    match_field: str
    matched_value: str


@dataclass(frozen=True, slots=True)
class _ExactRuleMatch:
    rule: VtdNameRule
    match_field: str
    matched_value: str
    source_paths: tuple[str, ...] = ()


def build_resolve_vtd_name_tool(knowledge_base: VtdKnowledgeBase):
    def resolve_vtd_name(
        name: str,
        namespace: str,
        asset_kind: str,
        country_code: str | None = None,
        user_override: bool = False,
    ) -> dict[str, Any]:
        normalized_name = name.strip()
        normalized_namespace = namespace.strip()

        if normalized_namespace == "runtime_asset":
            return _resolve_runtime_asset_name(
                knowledge_base,
                normalized_name,
                asset_kind=asset_kind,
                country_code=country_code,
            )

        if normalized_namespace in _SOFT_NAMESPACES:
            return _resolve_soft_namespace_name(
                knowledge_base,
                normalized_name,
                namespace=normalized_namespace,
                asset_kind=asset_kind,
                country_code=country_code,
                user_override=user_override,
            )

        return {
            "normalized_name": normalized_name,
            "severity": "warning",
            "rule_kind": "unsupported_namespace",
            "hard_constraint": False,
            "canonical_target": normalized_name,
            "alternatives": [],
            "reason": f"Unsupported VTD namespace '{normalized_namespace}'.",
            "source_paths": [],
        }

    return resolve_vtd_name


def _resolve_runtime_asset_name(
    knowledge_base: VtdKnowledgeBase,
    name: str,
    *,
    asset_kind: str,
    country_code: str | None,
) -> dict[str, Any]:
    country_aliases = _country_alias_map(knowledge_base)
    exact_matches = _find_exact_asset_matches(
        knowledge_base,
        name,
        asset_kind=asset_kind,
        country_code=country_code,
        country_aliases=country_aliases,
    )
    if exact_matches:
        primary = exact_matches[0]
        alternatives = _unique(
            match.asset.canonical_name for match in exact_matches
        )
        reason = (
            "Runtime asset names are hard-constrained to the VTD canonical asset."
            if primary.match_field == "canonical_name"
            else f"Alias '{primary.matched_value}' maps to the canonical runtime asset."
        )
        return {
            "normalized_name": name,
            "severity": "high" if primary.match_field == "canonical_name" else "info",
            "rule_kind": primary.match_field,
            "hard_constraint": True,
            "canonical_target": primary.asset.canonical_name,
            "alternatives": alternatives,
            "reason": reason,
            "source_paths": _unique(match.asset.source_path for match in exact_matches),
        }

    approximate_hits = search_vtd_assets(
        name,
        knowledge_base,
        asset_kind=asset_kind,
        country_code=country_code,
        top_k=5,
    )
    if approximate_hits:
        alternatives = _unique(hit.asset.canonical_name for hit in approximate_hits)
        return {
            "normalized_name": name,
            "severity": "warning",
            "rule_kind": "approximate_match",
            "hard_constraint": True,
            "canonical_target": approximate_hits[0].asset.canonical_name,
            "alternatives": alternatives,
            "reason": (
                "Runtime asset names must resolve to a VTD asset; use the closest "
                "canonical candidate."
            ),
            "source_paths": _unique(hit.asset.source_path for hit in approximate_hits),
        }

    return {
        "normalized_name": name,
        "severity": "warning",
        "rule_kind": "unresolved_runtime_asset",
        "hard_constraint": True,
        "canonical_target": name,
        "alternatives": [],
        "reason": "Runtime asset names must map to a known VTD asset.",
        "source_paths": [],
    }


def _resolve_soft_namespace_name(
    knowledge_base: VtdKnowledgeBase,
    name: str,
    *,
    namespace: str,
    asset_kind: str,
    country_code: str | None,
    user_override: bool,
) -> dict[str, Any]:
    country_aliases = _country_alias_map(knowledge_base)
    exact_rule_matches = _find_exact_rule_matches(
        knowledge_base,
        name,
        namespace=namespace,
        asset_kind=asset_kind,
        country_code=country_code,
        country_aliases=country_aliases,
    )
    exact_asset_matches = _find_exact_asset_matches(
        knowledge_base,
        name,
        asset_kind=None,
        country_code=country_code,
        country_aliases=country_aliases,
    )

    if exact_rule_matches or exact_asset_matches:
        primary_rule = exact_rule_matches[0] if exact_rule_matches else None
        canonical_target = (
            primary_rule.rule.canonical_target
            if primary_rule is not None
            else exact_asset_matches[0].asset.canonical_name
        )
        safe_name = _build_safe_name(knowledge_base, name=name, namespace=namespace)
        rule_source_paths = _unique(
            source_path
            for match in exact_rule_matches
            for source_path in (match.source_paths or (match.rule.source_path,))
        )
        asset_source_paths = _unique(
            match.asset.source_path for match in exact_asset_matches
        )
        source_paths = rule_source_paths if primary_rule is not None else asset_source_paths
        result: dict[str, Any] = {
            "normalized_name": name,
            "severity": (
                primary_rule.rule.severity
                if primary_rule is not None
                else "high"
            ),
            "rule_kind": _select_soft_rule_kind(exact_rule_matches, exact_asset_matches),
            "hard_constraint": False,
            "canonical_target": canonical_target,
            "safe_name": safe_name,
            "alternatives": _unique(
                [safe_name]
                + [match.rule.canonical_target for match in exact_rule_matches]
                + [match.asset.canonical_name for match in exact_asset_matches]
            ),
            "reason": (
                primary_rule.rule.reason
                if primary_rule is not None
                else (
                    "The requested name collides with an existing VTD asset name. "
                    "Use the safe internal name in this namespace."
                )
            ),
            "source_paths": source_paths,
        }
        if user_override:
            result["override_mapping"] = {
                "requested_name": name,
                "safe_name": safe_name,
            }
        return result

    approximate_hits = search_vtd_assets(
        name,
        knowledge_base,
        asset_kind=asset_kind,
        country_code=country_code,
        top_k=5,
    )
    if approximate_hits:
        return {
            "normalized_name": name,
            "severity": "warning",
            "rule_kind": "approximate_match",
            "hard_constraint": False,
            "canonical_target": approximate_hits[0].asset.canonical_name,
            "alternatives": _unique(hit.asset.canonical_name for hit in approximate_hits),
            "reason": (
                "The requested name is close to existing VTD asset names. "
                "Prefer one of the suggested alternatives."
            ),
            "source_paths": _unique(hit.asset.source_path for hit in approximate_hits),
        }

    return {
        "normalized_name": name,
        "severity": "info",
        "rule_kind": "no_match",
        "hard_constraint": False,
        "canonical_target": name,
        "alternatives": [],
        "reason": "No conflicting VTD asset name was found in the current snapshot.",
        "source_paths": [],
    }


def _find_exact_asset_matches(
    knowledge_base: VtdKnowledgeBase,
    name: str,
    *,
    asset_kind: str | None,
    country_code: str | None,
    country_aliases: dict[str, str],
) -> list[_ExactAssetMatch]:
    normalized_name = name.strip().casefold()
    normalized_asset_kind = _normalize_filter(asset_kind)
    matches: list[_ExactAssetMatch] = []

    for asset in knowledge_base.assets_by_id.values():
        if (
            normalized_asset_kind is not None
            and asset.asset_kind.casefold() != normalized_asset_kind
        ):
            continue
        if not _asset_matches_country(
            asset,
            country_code,
            country_aliases=country_aliases,
        ):
            continue
        if asset.canonical_name.casefold() == normalized_name:
            matches.append(
                _ExactAssetMatch(
                    asset=asset,
                    match_field="canonical_name",
                    matched_value=asset.canonical_name,
                )
            )
            continue
        for alias in asset.aliases:
            if alias.casefold() == normalized_name:
                matches.append(
                    _ExactAssetMatch(
                        asset=asset,
                        match_field="alias",
                        matched_value=alias,
                    )
                )
                break

    matches.sort(
        key=lambda match: (
            0 if match.match_field == "canonical_name" else 1,
            _country_priority(
                match.asset.country_codes,
                country_code,
                country_aliases=country_aliases,
            ),
            match.asset.canonical_name.casefold(),
            match.asset.source_path,
        )
    )
    return matches


def _find_exact_rule_matches(
    knowledge_base: VtdKnowledgeBase,
    name: str,
    *,
    namespace: str,
    asset_kind: str,
    country_code: str | None,
    country_aliases: dict[str, str],
) -> list[_ExactRuleMatch]:
    normalized_name = name.strip().casefold()
    normalized_namespace = namespace.strip().casefold()
    normalized_asset_kind = asset_kind.strip().casefold()
    matches: list[_ExactRuleMatch] = []

    for policy in _iter_name_policies(knowledge_base):
        policy_namespace = str(policy.get("namespace", "")).strip().casefold()
        if policy_namespace != normalized_namespace:
            continue

        policy_asset_kind = str(policy.get("asset_kind", "")).strip().casefold()
        if policy_asset_kind != normalized_asset_kind:
            continue

        if not _policy_matches_country(
            policy,
            country_code,
            country_aliases=country_aliases,
        ):
            continue

        match_name = str(policy.get("match_name", "")).strip()
        canonical_target = str(policy.get("canonical_target", "")).strip()
        if not match_name and not canonical_target:
            continue

        matched_value = ""
        if match_name and match_name.casefold() == normalized_name:
            matched_value = match_name
        elif canonical_target and canonical_target.casefold() == normalized_name:
            matched_value = canonical_target
        else:
            continue

        source_paths = tuple(_policy_source_paths(policy))
        matches.append(
            _ExactRuleMatch(
                rule=VtdNameRule(
                    name=str(policy.get("policy_id", "")).strip() or matched_value,
                    rule_kind=str(policy.get("rule_kind", "")).strip()
                    or "reserved_name",
                    severity=str(policy.get("severity", "")).strip() or "warning",
                    canonical_target=canonical_target or matched_value,
                    asset_kind=asset_kind,
                    reason=str(policy.get("reason", "")).strip()
                    or "Materialized VTD name policy.",
                    source_path=source_paths[0] if source_paths else "",
                    scope={
                        "namespace": namespace,
                        "asset_kind": asset_kind,
                        "country_code": str(policy.get("country_scope", "")).strip(),
                    },
                    metadata={
                        "match_name": match_name,
                        "safe_name_strategy": str(
                            policy.get("safe_name_strategy", "")
                        ).strip(),
                    },
                ),
                match_field=str(policy.get("rule_kind", "")).strip()
                or "reserved_name",
                matched_value=matched_value,
                source_paths=source_paths,
            )
        )

    for rule in knowledge_base.rules_by_name.values():
        if rule.scope.get("namespace", "").strip().casefold() != normalized_namespace:
            continue
        if rule.scope.get("asset_kind", "").strip().casefold() != normalized_asset_kind:
            continue
        if not _rule_matches_country(
            rule,
            country_code,
            country_aliases=country_aliases,
        ):
            continue
        if rule.canonical_target.casefold() == normalized_name:
            matches.append(
                _ExactRuleMatch(
                    rule=rule,
                    match_field=rule.rule_kind,
                    matched_value=rule.canonical_target,
                )
            )
            continue
        alias = str(rule.metadata.get("alias", "")).strip()
        if alias and alias.casefold() == normalized_name:
            matches.append(
                _ExactRuleMatch(
                    rule=rule,
                    match_field="alias",
                    matched_value=alias,
                )
            )

    matches.sort(
        key=lambda match: (
            0 if match.rule.rule_kind == "reserved_name" else 1,
            _scope_country_priority(
                match.rule.scope,
                country_code,
                country_aliases=country_aliases,
            ),
            match.rule.canonical_target.casefold(),
            match.rule.source_path,
        )
    )
    return matches


def _select_soft_rule_kind(
    exact_rule_matches: list[_ExactRuleMatch],
    exact_asset_matches: list[_ExactAssetMatch],
) -> str:
    if exact_rule_matches:
        return exact_rule_matches[0].rule.rule_kind
    return exact_asset_matches[0].match_field


def _build_safe_name(
    knowledge_base: VtdKnowledgeBase,
    *,
    name: str,
    namespace: str,
) -> str:
    stem = _SAFE_NAME_PATTERN.sub("_", name).strip("_")
    if not stem:
        stem = "vtd_name"

    candidate = f"{stem}_{namespace}"
    suffix = 2
    while _name_in_use(knowledge_base, candidate):
        candidate = f"{stem}_{namespace}_{suffix}"
        suffix += 1
    return candidate


def _name_in_use(knowledge_base: VtdKnowledgeBase, candidate: str) -> bool:
    normalized_candidate = candidate.casefold()
    for asset in knowledge_base.assets_by_id.values():
        if asset.canonical_name.casefold() == normalized_candidate:
            return True
        if any(alias.casefold() == normalized_candidate for alias in asset.aliases):
            return True
    return False


def _asset_matches_country(
    asset: VtdAssetRecord,
    country_code: str | None,
    *,
    country_aliases: dict[str, str],
) -> bool:
    if country_code is None:
        return True
    if not asset.country_codes:
        return True
    normalized_country = _normalize_country_code(
        country_code,
        country_aliases=country_aliases,
    )
    return any(
        _normalize_country_code(code, country_aliases=country_aliases)
        == normalized_country
        for code in asset.country_codes
    )


def _rule_matches_country(
    rule: VtdNameRule,
    country_code: str | None,
    *,
    country_aliases: dict[str, str],
) -> bool:
    if country_code is None:
        return True
    rule_country = rule.scope.get("country_code", "")
    if not rule_country.strip():
        return True
    return _normalize_country_code(
        rule_country,
        country_aliases=country_aliases,
    ) == _normalize_country_code(
        country_code,
        country_aliases=country_aliases,
    )


def _country_priority(
    country_codes: list[str],
    country_code: str | None,
    *,
    country_aliases: dict[str, str],
) -> int:
    if country_code is None:
        return 0
    normalized_requested = _normalize_country_code(
        country_code,
        country_aliases=country_aliases,
    )
    normalized_codes = [
        _normalize_country_code(code, country_aliases=country_aliases)
        for code in country_codes
        if code.strip()
    ]
    if normalized_requested in normalized_codes:
        return 0
    if not normalized_codes:
        return 1
    return 2


def _scope_country_priority(
    scope: dict[str, str],
    country_code: str | None,
    *,
    country_aliases: dict[str, str],
) -> int:
    if country_code is None:
        return 0
    scope_country = scope.get("country_code", "").strip()
    if not scope_country:
        return 1
    return (
        0
        if _normalize_country_code(
            scope_country,
            country_aliases=country_aliases,
        )
        == _normalize_country_code(
            country_code,
            country_aliases=country_aliases,
        )
        else 2
    )


def _normalize_country_code(
    value: str,
    *,
    country_aliases: dict[str, str],
) -> str:
    return _normalize_country_compare_code(value, country_aliases=country_aliases)


def _iter_name_policies(knowledge_base: VtdKnowledgeBase) -> list[dict[str, Any]]:
    raw_policies = knowledge_base.metadata.get("name_policies", [])
    if not isinstance(raw_policies, list):
        return []
    return [policy for policy in raw_policies if isinstance(policy, dict)]


def _policy_matches_country(
    policy: dict[str, Any],
    country_code: str | None,
    *,
    country_aliases: dict[str, str],
) -> bool:
    if country_code is None:
        return True

    policy_country = str(policy.get("country_scope", "")).strip()
    if not policy_country:
        return True

    return _normalize_country_code(
        policy_country,
        country_aliases=country_aliases,
    ) == _normalize_country_code(
        country_code,
        country_aliases=country_aliases,
    )


def _policy_source_paths(policy: dict[str, Any]) -> list[str]:
    raw_source_paths = policy.get("source_paths", [])
    if not isinstance(raw_source_paths, list):
        return []
    return [
        source_path
        for source_path in raw_source_paths
        if isinstance(source_path, str) and source_path.strip()
    ]


def _normalize_filter(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    return normalized or None


def _unique(values: Any) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        text = value.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        deduped.append(text)
    return deduped


__all__ = ["build_resolve_vtd_name_tool"]
