from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from openscenario_mcp.models import VtdAssetRecord, VtdKnowledgeBase, VtdNameRule

_CAMEL_CASE_BOUNDARY_PATTERN = re.compile(
    r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])"
)
_NON_ALNUM_PATTERN = re.compile(r"[^A-Za-z0-9]+")
_LEGACY_COUNTRY_COMPARE_ALIASES = {
    "prc": "cn",
    "china": "cn",
    "cn": "cn",
    "de": "de",
    "deu": "de",
    "germany": "de",
    "france": "fr",
    "usa": "us",
    "us": "us",
    "fra": "fr",
    "fr": "fr",
}


@dataclass(frozen=True, slots=True)
class VtdAssetSearchHit:
    asset: VtdAssetRecord
    score: int
    match_field: str
    matched_value: str


@dataclass(frozen=True, slots=True)
class VtdRuleSearchHit:
    rule: VtdNameRule
    score: int
    match_field: str
    matched_value: str


def search_vtd_assets(
    query: str,
    knowledge_base: VtdKnowledgeBase,
    *,
    asset_kind: str | None = None,
    country_code: str | None = None,
    top_k: int = 5,
) -> list[VtdAssetSearchHit]:
    normalized_query = _normalize_text(query)
    if not normalized_query or top_k <= 0:
        return []

    normalized_asset_kind = _normalize_filter(asset_kind)
    normalized_country_code = _normalize_filter(country_code)
    country_aliases = _country_alias_map(knowledge_base)
    hits: list[VtdAssetSearchHit] = []

    for asset in knowledge_base.assets_by_id.values():
        if (
            normalized_asset_kind is not None
            and asset.asset_kind.casefold() != normalized_asset_kind
        ):
            continue
        if not _asset_matches_country(
            asset,
            normalized_country_code,
            country_aliases=country_aliases,
        ):
            continue

        score, match_field, matched_value = _score_asset(query=normalized_query, asset=asset)
        if score <= 0:
            continue
        hits.append(
            VtdAssetSearchHit(
                asset=asset,
                score=score,
                match_field=match_field,
                matched_value=matched_value,
            )
        )

    hits.sort(
        key=lambda hit: (
            -hit.score,
            _country_match_priority(
                hit.asset.country_codes,
                normalized_country_code,
                country_aliases=country_aliases,
            ),
            hit.asset.asset_kind,
            hit.asset.canonical_name.casefold(),
            tuple(code.casefold() for code in hit.asset.country_codes),
            hit.asset.relative_path,
            hit.asset.asset_id,
        )
    )
    return hits[:top_k]


def search_vtd_rules(
    query: str,
    knowledge_base: VtdKnowledgeBase,
    *,
    namespace: str | None = None,
    asset_kind: str | None = None,
    country_code: str | None = None,
    top_k: int = 5,
) -> list[VtdRuleSearchHit]:
    normalized_query = _normalize_text(query)
    if not normalized_query or top_k <= 0:
        return []

    normalized_namespace = _normalize_filter(namespace)
    normalized_asset_kind = _normalize_filter(asset_kind)
    normalized_country_code = _normalize_filter(country_code)
    country_aliases = _country_alias_map(knowledge_base)
    hits: list[VtdRuleSearchHit] = []

    for rule in knowledge_base.rules_by_name.values():
        if not _rule_matches_scope(
            rule,
            namespace=normalized_namespace,
            asset_kind=normalized_asset_kind,
            country_code=normalized_country_code,
            country_aliases=country_aliases,
        ):
            continue

        score, match_field, matched_value = _score_rule(query=normalized_query, rule=rule)
        if score <= 0:
            continue
        hits.append(
            VtdRuleSearchHit(
                rule=rule,
                score=score,
                match_field=match_field,
                matched_value=matched_value,
            )
        )

    hits.sort(
        key=lambda hit: (
            -hit.score,
            _scope_country_match_priority(
                hit.rule.scope,
                normalized_country_code,
                country_aliases=country_aliases,
            ),
            hit.rule.asset_kind,
            hit.rule.scope.get("namespace", ""),
            hit.rule.scope.get("country_code", ""),
            hit.rule.name.casefold(),
        )
    )
    return hits[:top_k]


def _score_asset(*, query: str, asset: VtdAssetRecord) -> tuple[int, str, str]:
    best_score = 0
    best_field = ""
    best_value = ""

    for field_name, field_value, exact_score, contains_score, token_score in (
        ("canonical_name", asset.canonical_name, 320, 220, 260),
        ("display_name", asset.display_name, 180, 100, 140),
        ("filename", asset.filename, 160, 90, 120),
        ("group_path", asset.group_path, 120, 70, 100),
        ("relative_path", asset.relative_path, 80, 40, 60),
    ):
        score = _score_text(
            query,
            field_value,
            exact_score=exact_score,
            contains_score=contains_score,
            token_score=token_score,
        )
        if score > best_score:
            best_score = score
            best_field = field_name
            best_value = field_value

    for alias in asset.aliases:
        score = _score_text(
            query,
            alias,
            exact_score=240,
            contains_score=150,
            token_score=190,
        )
        if score > best_score:
            best_score = score
            best_field = "alias"
            best_value = alias

    return best_score, best_field, best_value


def _score_rule(*, query: str, rule: VtdNameRule) -> tuple[int, str, str]:
    best_score = 0
    best_field = ""
    best_value = ""

    fields: list[tuple[str, str, int, int, int]] = [
        ("canonical_target", rule.canonical_target, 300, 200, 240),
        ("name", rule.name, 220, 140, 180),
        ("reason", rule.reason, 80, 40, 60),
    ]
    alias = rule.metadata.get("alias")
    if isinstance(alias, str):
        fields.append(("alias", alias, 260, 170, 210))

    for field_name, field_value, exact_score, contains_score, token_score in fields:
        score = _score_text(
            query,
            field_value,
            exact_score=exact_score,
            contains_score=contains_score,
            token_score=token_score,
        )
        if score > best_score:
            best_score = score
            best_field = field_name
            best_value = field_value

    return best_score, best_field, best_value


def _score_text(
    query: str,
    value: str,
    *,
    exact_score: int,
    contains_score: int,
    token_score: int,
) -> int:
    normalized_value = _normalize_text(value)
    if not normalized_value:
        return 0

    score = 0
    if query == normalized_value:
        score = max(score, exact_score)
    if query in normalized_value:
        score = max(score, contains_score)

    query_tokens = set(_tokenize(query))
    value_tokens = set(_tokenize(normalized_value))
    if query_tokens and query_tokens <= value_tokens:
        score = max(score, token_score)
    overlap = len(query_tokens & value_tokens)
    if query_tokens and (overlap * 2 >= len(query_tokens)):
        score += 8 * overlap
    return score


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
    requested_country = _normalize_country_compare_code(
        country_code,
        country_aliases=country_aliases,
    )
    return any(
        _normalize_country_compare_code(code, country_aliases=country_aliases)
        == requested_country
        for code in asset.country_codes
    )


def _rule_matches_scope(
    rule: VtdNameRule,
    *,
    namespace: str | None,
    asset_kind: str | None,
    country_code: str | None,
    country_aliases: dict[str, str],
) -> bool:
    return (
        _scope_matches(rule.scope, "namespace", namespace)
        and _scope_matches(rule.scope, "asset_kind", asset_kind)
        and _scope_matches(
            rule.scope,
            "country_code",
            country_code,
            country_aliases=country_aliases,
        )
    )


def _scope_matches(
    scope: dict[str, str],
    key: str,
    expected: str | None,
    *,
    country_aliases: dict[str, str] | None = None,
) -> bool:
    if expected is None:
        return True
    actual = scope.get(key, "").strip().casefold()
    if key == "country_code" and not actual:
        return True
    if key == "country_code":
        resolved_aliases = (
            {} if country_aliases is None else country_aliases
        )
        return _normalize_country_compare_code(
            actual,
            country_aliases=resolved_aliases,
        ) == _normalize_country_compare_code(
            expected,
            country_aliases=resolved_aliases,
        )
    return actual == expected


def _country_match_priority(
    country_codes: list[str],
    requested_country: str | None,
    *,
    country_aliases: dict[str, str],
) -> int:
    if requested_country is None:
        return 0

    normalized_codes = [
        _normalize_country_compare_code(code, country_aliases=country_aliases)
        for code in country_codes
        if code.strip()
    ]
    normalized_requested_country = _normalize_country_compare_code(
        requested_country,
        country_aliases=country_aliases,
    )
    if normalized_requested_country in normalized_codes:
        return 0
    if not normalized_codes:
        return 1
    return 2


def _scope_country_match_priority(
    scope: dict[str, str],
    requested_country: str | None,
    *,
    country_aliases: dict[str, str],
) -> int:
    if requested_country is None:
        return 0

    scope_country = _normalize_country_compare_code(
        scope.get("country_code", ""),
        country_aliases=country_aliases,
    )
    normalized_requested_country = _normalize_country_compare_code(
        requested_country,
        country_aliases=country_aliases,
    )
    if scope_country == normalized_requested_country:
        return 0
    if not scope_country:
        return 1
    return 2


def _normalize_country_compare_code(
    value: str,
    *,
    country_aliases: dict[str, str],
) -> str:
    normalized = value.strip().casefold()
    return country_aliases.get(normalized, normalized)


def _country_alias_map(knowledge_base: VtdKnowledgeBase) -> dict[str, str]:
    aliases: dict[str, str] = {}

    taxonomy = knowledge_base.metadata.get("country_taxonomy")
    if isinstance(taxonomy, dict):
        raw_aliases = taxonomy.get("alias_to_country", {})
        if isinstance(raw_aliases, dict):
            for alias, canonical_country in raw_aliases.items():
                normalized_alias = str(alias).strip().casefold()
                normalized_country = str(canonical_country).strip().casefold()
                if normalized_alias and normalized_country:
                    aliases[normalized_alias] = normalized_country

        raw_countries = taxonomy.get("countries", {})
        if isinstance(raw_countries, dict):
            for canonical_country, entry in raw_countries.items():
                normalized_country = str(canonical_country).strip().casefold()
                if not normalized_country:
                    continue
                aliases.setdefault(normalized_country, normalized_country)
                if not isinstance(entry, dict):
                    continue
                for field_name in ("aliases", "observed_values"):
                    field_values = entry.get(field_name, [])
                    if not isinstance(field_values, list):
                        continue
                    for field_value in field_values:
                        normalized_value = str(field_value).strip().casefold()
                        if normalized_value:
                            aliases.setdefault(normalized_value, normalized_country)

    for alias, canonical_country in _LEGACY_COUNTRY_COMPARE_ALIASES.items():
        aliases.setdefault(alias, canonical_country)
    return aliases


def _normalize_filter(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    return normalized or None


def _normalize_text(value: str) -> str:
    return " ".join(_tokenize(value))


def _tokenize(value: str) -> list[str]:
    normalized = _CAMEL_CASE_BOUNDARY_PATTERN.sub(" ", value)
    normalized = _NON_ALNUM_PATTERN.sub(" ", normalized)
    return [token.lower() for token in normalized.split() if token]


__all__ = [
    "VtdAssetSearchHit",
    "VtdRuleSearchHit",
    "search_vtd_assets",
    "search_vtd_rules",
]
