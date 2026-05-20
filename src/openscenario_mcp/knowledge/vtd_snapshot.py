from __future__ import annotations

import copy
import hashlib
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from openscenario_mcp.knowledge.vtd_parsers import (
    parse_addon_xml_descriptor,
    parse_dat_definitions,
    parse_decal_scatter,
    parse_pbr_objects,
    parse_resource_dirs,
)
from openscenario_mcp.models import VtdAssetRecord, VtdNameRule

_COUNTRY_SEGMENT_RE = re.compile(r"^Country([A-Z]{2,3})(?:$|[^A-Z])")
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_COUNTRY_CODE_ALIASES = {
    "cn": "CN",
    "china": "CN",
    "prc": "CN",
    "de": "DE",
    "deu": "DE",
    "germany": "DE",
    "fr": "FR",
    "fra": "FR",
    "france": "FR",
    "us": "US",
    "usa": "US",
}
_COUNTRY_TAXONOMY_ALIAS_SEEDS = {
    "CN": ("cn", "china", "prc"),
    "DE": ("de", "deu", "germany"),
    "FR": ("fr", "fra", "france"),
    "US": ("us", "usa"),
}
_TRUSTED_NAME_PREFIX_COUNTRY_CODES = {
    "CN",
    "DE",
    "US",
    "USA",
}
_SUPPORTED_RESERVED_NAME_NAMESPACES = {
    "runtime_asset",
    "scenario_object",
    "variable",
    "external_object",
}
_RULE_KIND_ORDER = {
    "reserved_name": 0,
    "alias": 1,
    "country_preference": 2,
}
_MODEL_EXTENSIONS = {
    ".3ds",
    ".ac",
    ".fbx",
    ".flt",
    ".ive",
    ".obj",
    ".osg",
    ".osgb",
}
_ASSET_BUCKETS = {
    "addons": "addons.jsonl",
    "decals": "decals.jsonl",
    "externals": "externals.jsonl",
    "macros": "macros.jsonl",
    "models": "models.jsonl",
    "samples": "samples.jsonl",
    "signals": "signals.jsonl",
    "styles": "styles.jsonl",
    "tiles": "tiles.jsonl",
}
_ALLOWLIST = [
    {
        "match": "Tools/resourceDirs.txt",
        "match_type": "file",
        "collector": "resource_dirs",
    },
    {
        "match": "VisualLib/Models",
        "match_type": "directory",
        "collector": "model_scan",
        "bucket": "models.jsonl",
    },
    {
        "match": "VisualLib/ModelsPBR",
        "match_type": "directory",
        "collector": "model_scan",
        "bucket": "models.jsonl",
    },
    {
        "match": "VisualLib/Styles",
        "match_type": "directory",
        "collector": "style_scan",
        "bucket": "styles.jsonl",
    },
    {
        "match": "VisualLib/TileLib",
        "match_type": "directory",
        "collector": "tile_scan",
        "bucket": "tiles.jsonl",
    },
    {
        "match": "VisualLib/Models/**/SetupFiles/*.DAT",
        "match_type": "glob",
        "collector": "dat_definitions",
    },
    {
        "match": "Tools/pbr_*.xml",
        "match_type": "glob",
        "collector": "pbr_objects",
        "bucket": "models.jsonl",
    },
    {
        "match": "DefaultProject/Config/*.xml",
        "match_type": "glob",
        "collector": "config_xml",
        "bucket": "decals.jsonl",
    },
    {
        "match": "DefaultProject/Config/Macros/*.rmcr",
        "match_type": "glob",
        "collector": "macro_scan",
        "bucket": "macros.jsonl",
    },
    {
        "match": "Samples/*.tdo",
        "match_type": "glob",
        "collector": "sample_scan",
        "bucket": "samples.jsonl",
    },
    {
        "match": "AddOns/**/*.xml",
        "match_type": "glob",
        "collector": "addon_xml_descriptor",
        "bucket": "addons.jsonl",
    },
]
_EXTRACTOR_MANIFEST = {
    "version": 1,
    "phase": "phase1",
    "allowlist": _ALLOWLIST,
    "buckets": _ASSET_BUCKETS,
}


def build_extractor_manifest() -> dict[str, Any]:
    return copy.deepcopy(_EXTRACTOR_MANIFEST)


def build_asset_buckets(runtime_root: str | Path) -> dict[str, list[VtdAssetRecord]]:
    runtime_path = Path(runtime_root)
    resource_dirs = _load_resource_dirs(runtime_path)
    scanned_models = _scan_model_records(runtime_path, resource_dirs)
    consumed_scan_paths: set[str] = set()
    consumed_model_overlap_keys: set[tuple[str, tuple[str, ...]]] = set()
    buckets: dict[str, dict[str, VtdAssetRecord]] = {
        bucket_name: {} for bucket_name in _ASSET_BUCKETS.values()
    }

    for dat_path in sorted(runtime_path.glob("VisualLib/Models/**/SetupFiles/*.DAT")):
        definition_kind = _infer_dat_definition_kind(dat_path)
        if not definition_kind:
            continue
        for entry in parse_dat_definitions(dat_path, definition_kind=definition_kind):
            record = _build_dat_record(
                runtime_path=runtime_path,
                entry=entry,
                definition_kind=definition_kind,
                resource_dirs=resource_dirs,
                scanned_models=scanned_models,
                consumed_scan_paths=consumed_scan_paths,
                consumed_model_overlap_keys=consumed_model_overlap_keys,
            )
            _store_record(buckets[_bucket_for_asset_kind(record.asset_kind)], record)

    pbr_path = runtime_path / "Tools" / "pbr_objects.xml"
    if pbr_path.is_file():
        for entry in parse_pbr_objects(pbr_path):
            record = _build_pbr_record(
                runtime_path=runtime_path,
                entry=entry,
                resource_dirs=resource_dirs,
                scanned_models=scanned_models,
            )
            _store_record(buckets["models.jsonl"], record)

    for config_path in sorted(runtime_path.glob("DefaultProject/Config/*.xml")):
        if not config_path.name.startswith("decalScatter"):
            continue
        for entry in parse_decal_scatter(config_path):
            canonical_name = entry["name"]
            record = VtdAssetRecord(
                asset_id=_build_asset_id("decal", canonical_name, []),
                asset_kind="decal",
                canonical_name=canonical_name,
                display_name=canonical_name,
                filename=canonical_name,
                relative_path=_relative_path(config_path, runtime_path),
                source_path=_normalize_source_path(entry["source_path"], runtime_path),
                group_path=entry["targettexture"],
                runtime_family="decal",
                aliases=[],
                country_codes=[],
                variant_tags=[],
                metadata={
                    "alignment": entry["alignment"],
                    "config_kind": entry["config_kind"],
                    "quantity": entry["quantity"],
                    "root_element": entry["root_element"],
                    "targettexture": entry["targettexture"],
                },
            )
            _store_record(buckets["decals.jsonl"], record)

    for addon_path in sorted(runtime_path.glob("AddOns/**/*.xml")):
        descriptor = parse_addon_xml_descriptor(addon_path)
        canonical_name = addon_path.stem
        country_codes = _country_codes_for_path(
            _relative_path(addon_path, runtime_path),
            canonical_name,
        )
        record = VtdAssetRecord(
            asset_id=_build_asset_id("addon", canonical_name, country_codes),
            asset_kind="addon",
            canonical_name=canonical_name,
            display_name=canonical_name,
            filename=addon_path.name,
            relative_path=_relative_path(addon_path, runtime_path),
            source_path=_normalize_source_path(descriptor["source_path"], runtime_path),
            group_path=_relative_parent(addon_path, runtime_path),
            runtime_family="addon",
            aliases=[],
            country_codes=country_codes,
            variant_tags=[],
            metadata={
                "config_kind": descriptor["config_kind"],
                "top_level_descriptors": descriptor["top_level_descriptors"],
                "top_level_elements": descriptor["top_level_elements"],
            },
        )
        _store_record(buckets["addons.jsonl"], record)

    for style_path in _iter_files(runtime_path / "VisualLib" / "Styles"):
        record = _build_scanned_record(runtime_path, style_path, asset_kind="style")
        _store_record(buckets["styles.jsonl"], record)

    for tile_path in _iter_files(runtime_path / "VisualLib" / "TileLib"):
        record = _build_scanned_record(runtime_path, tile_path, asset_kind="tile")
        _store_record(buckets["tiles.jsonl"], record)

    for macro_path in sorted(runtime_path.glob("DefaultProject/Config/Macros/*.rmcr")):
        record = _build_scanned_record(runtime_path, macro_path, asset_kind="macro")
        _store_record(buckets["macros.jsonl"], record)

    for sample_path in sorted(runtime_path.glob("Samples/*.tdo")):
        record = _build_scanned_record(runtime_path, sample_path, asset_kind="sample")
        _store_record(buckets["samples.jsonl"], record)

    for scan_records in scanned_models.values():
        for scan_record in scan_records:
            if scan_record.source_path in consumed_scan_paths:
                continue
            if (
                scan_record.asset_kind == "model"
                and _asset_overlap_key(scan_record.canonical_name, scan_record.country_codes)
                in consumed_model_overlap_keys
            ):
                continue
            _store_record(
                buckets[_bucket_for_asset_kind(scan_record.asset_kind)],
                scan_record,
            )

    return {
        bucket_name: sorted(
            records.values(),
            key=lambda record: (
                record.asset_kind,
                record.canonical_name,
                record.relative_path,
            ),
        )
        for bucket_name, records in buckets.items()
    }


def build_asset_records(runtime_root: str | Path) -> list[VtdAssetRecord]:
    buckets = build_asset_buckets(runtime_root)
    records: list[VtdAssetRecord] = []
    for bucket_name in _ASSET_BUCKETS.values():
        records.extend(buckets[bucket_name])
    return records


def build_reserved_name_candidates(
    assets: Iterable[VtdAssetRecord],
) -> list[tuple[str, str, str, str]]:
    candidates: set[tuple[str, str, str, str]] = set()
    sorted_assets = sorted(
        assets,
        key=lambda asset: (asset.asset_kind, asset.canonical_name, asset.asset_id),
    )

    for asset in sorted_assets:
        country_scope = _normalize_country_codes(asset.country_codes) or [""]
        soft_names = _dedupe([asset.canonical_name, *asset.aliases])
        for country_code in country_scope:
            candidates.add(
                (
                    asset.canonical_name,
                    "runtime_asset",
                    asset.asset_kind,
                    country_code,
                )
            )
            for namespace in (
                "scenario_object",
                "variable",
                "external_object",
            ):
                for candidate_name in soft_names:
                    candidates.add(
                        (
                            candidate_name,
                            namespace,
                            asset.asset_kind,
                            country_code,
                        )
                    )

    return sorted(candidates, key=lambda item: item)


def build_country_taxonomy(
    assets: Iterable[VtdAssetRecord],
    rules: Iterable[VtdNameRule] | None = None,
) -> dict[str, Any]:
    countries: dict[str, dict[str, list[str] | str]] = {}

    def observe_country(value: str) -> None:
        canonical_code = _normalize_country_code(value)
        if not canonical_code:
            return
        entry = countries.setdefault(
            canonical_code,
            {
                "canonical_code": canonical_code,
                "observed_values": [],
                "aliases": [],
            },
        )
        observed_values = entry["observed_values"]
        if value and value not in observed_values:
            observed_values.append(value)

    for asset in assets:
        for country_code in asset.country_codes:
            observe_country(country_code)

    for rule in rules or []:
        observe_country(rule.scope.get("country_code", ""))
        for country_code in rule.metadata.get("existing_country_codes", []):
            if isinstance(country_code, str):
                observe_country(country_code)

    alias_to_country: dict[str, str] = {}
    for canonical_code in sorted(countries):
        entry = countries[canonical_code]
        aliases = {
            canonical_code.casefold(),
            *(
                alias
                for alias in _COUNTRY_TAXONOMY_ALIAS_SEEDS.get(canonical_code, ())
                if alias
            ),
            *(
                observed_value.casefold()
                for observed_value in entry["observed_values"]
                if isinstance(observed_value, str) and observed_value
            ),
        }
        normalized_aliases = sorted(alias for alias in aliases if alias)
        entry["observed_values"] = sorted(
            entry["observed_values"],
            key=lambda value: value.casefold(),
        )
        entry["aliases"] = normalized_aliases
        for alias in normalized_aliases:
            alias_to_country[alias] = canonical_code

    return {
        "version": 1,
        "countries": {canonical_code: countries[canonical_code] for canonical_code in sorted(countries)},
        "alias_to_country": {
            alias: alias_to_country[alias] for alias in sorted(alias_to_country)
        },
    }


def build_name_policies(
    rules: Iterable[VtdNameRule],
    *,
    country_taxonomy: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    alias_to_country = {}
    if isinstance(country_taxonomy, dict):
        raw_alias_to_country = country_taxonomy.get("alias_to_country", {})
        if isinstance(raw_alias_to_country, dict):
            alias_to_country = {
                str(alias).casefold(): str(country)
                for alias, country in raw_alias_to_country.items()
                if str(alias).strip() and str(country).strip()
            }

    policies_by_key: dict[tuple[str, ...], dict[str, Any]] = {}
    for rule in sorted(
        rules,
        key=lambda item: (
            item.scope.get("namespace", ""),
            item.asset_kind,
            item.scope.get("country_code", ""),
            str(item.metadata.get("match_name", item.canonical_target)),
            item.canonical_target,
            item.name,
        ),
    ):
        if rule.rule_kind != "reserved_name":
            continue

        match_name = str(
            rule.metadata.get("match_name")
            or rule.metadata.get("alias")
            or rule.canonical_target
        ).strip()
        if not match_name:
            continue

        namespace = rule.scope.get("namespace", "")
        country_scope = _policy_country_scope(
            rule.scope.get("country_code", ""),
            alias_to_country,
        )
        policy_key = (
            namespace,
            rule.asset_kind,
            country_scope,
            match_name.casefold(),
            rule.canonical_target.casefold(),
        )
        policies_by_key[policy_key] = {
            "policy_id": _policy_id(
                namespace=namespace,
                asset_kind=rule.asset_kind,
                country_scope=country_scope,
                match_name=match_name,
            ),
            "namespace": namespace,
            "asset_kind": rule.asset_kind,
            "country_scope": country_scope,
            "rule_kind": rule.rule_kind,
            "severity": rule.severity,
            "match_mode": "exact",
            "match_name": match_name,
            "canonical_target": rule.canonical_target,
            "safe_name_strategy": (
                "hard_constraint"
                if namespace == "runtime_asset"
                else "append_namespace"
            ),
            "reason": rule.reason,
            "source_paths": [],
        }

    return sorted(
        policies_by_key.values(),
        key=lambda policy: (
            str(policy["namespace"]),
            str(policy["asset_kind"]),
            str(policy["country_scope"]),
            str(policy["match_name"]).casefold(),
            str(policy["canonical_target"]).casefold(),
            str(policy["policy_id"]),
        ),
    )


def build_name_rules(
    assets: Iterable[VtdAssetRecord],
    candidate_names: Iterable[tuple[str, str, str, str]] | None = None,
) -> list[VtdNameRule]:
    sorted_assets = sorted(
        assets,
        key=lambda asset: (asset.asset_kind, asset.canonical_name, asset.asset_id),
    )
    rules: list[VtdNameRule] = []

    for asset in sorted_assets:
        country_scope = _normalize_country_codes(asset.country_codes) or [""]
        for country_code in country_scope:
            scope = {
                "namespace": "runtime_asset",
                "asset_kind": asset.asset_kind,
                "country_code": country_code,
            }
            for alias in asset.aliases:
                rules.append(
                    VtdNameRule(
                        name=_rule_name(
                            "alias",
                            "runtime_asset",
                            asset.asset_kind,
                            country_code,
                            alias,
                            asset.asset_id,
                        ),
                        rule_kind="alias",
                        severity="info",
                        canonical_target=asset.canonical_name,
                        asset_kind=asset.asset_kind,
                        reason=f"Alias '{alias}' maps to the canonical runtime asset.",
                        source_path=asset.source_path,
                        scope=scope,
                        metadata={"alias": alias, "runtime_family": asset.runtime_family},
                    )
                )
            if country_code:
                rules.append(
                    VtdNameRule(
                        name=_rule_name(
                            "country-preference",
                            "runtime_asset",
                            asset.asset_kind,
                            country_code,
                            asset.canonical_name,
                            asset.asset_id,
                        ),
                        rule_kind="country_preference",
                        severity="info",
                        canonical_target=asset.canonical_name,
                        asset_kind=asset.asset_kind,
                        reason="Prefer the country-specific runtime asset for this scope.",
                        source_path=asset.source_path,
                        scope=scope,
                        metadata={
                            "country_code": country_code,
                            "runtime_family": asset.runtime_family,
                        },
                    )
                )

    for candidate_name, namespace, asset_kind, country_code in sorted(
        candidate_names or [],
        key=lambda item: item,
    ):
        if namespace not in _SUPPORTED_RESERVED_NAME_NAMESPACES:
            continue
        normalized_country_code = _normalize_country_code(country_code)
        candidate_key = _name_compare_key(candidate_name)
        for asset in sorted_assets:
            matched_alias = next(
                (
                    alias
                    for alias in asset.aliases
                    if _name_compare_key(alias) == candidate_key
                ),
                "",
            )
            if candidate_key not in {
                _name_compare_key(asset.canonical_name),
                *(_name_compare_key(alias) for alias in asset.aliases),
            }:
                continue
            if namespace == "runtime_asset":
                severity = _collision_severity(
                    asset=asset,
                    candidate_asset_kind=asset_kind,
                    candidate_country_code=normalized_country_code,
                )
                reason = _collision_reason(
                    asset=asset,
                    candidate_asset_kind=asset_kind,
                    candidate_country_code=normalized_country_code,
                )
            else:
                severity = _soft_namespace_collision_severity(
                    asset=asset,
                    candidate_asset_kind=asset_kind,
                    candidate_country_code=normalized_country_code,
                )
                reason = _soft_namespace_collision_reason(
                    namespace=namespace,
                    asset=asset,
                )
            metadata = {
                "existing_asset_kind": asset.asset_kind,
                "existing_country_codes": asset.country_codes,
                "match_name": candidate_name,
            }
            if matched_alias:
                metadata["alias"] = matched_alias
            rules.append(
                VtdNameRule(
                    name=_rule_name(
                        "reserved-name",
                        namespace,
                        asset_kind,
                        normalized_country_code,
                        candidate_name,
                        asset.asset_id,
                    ),
                    rule_kind="reserved_name",
                    severity=severity,
                    canonical_target=asset.canonical_name,
                    asset_kind=asset_kind,
                    reason=reason,
                    source_path=asset.source_path,
                    scope={
                        "namespace": namespace,
                        "asset_kind": asset_kind,
                        "country_code": normalized_country_code,
                    },
                    metadata=metadata,
                )
            )

    sorted_rules = sorted(
        rules,
        key=lambda rule: (
            _RULE_KIND_ORDER.get(rule.rule_kind, 99),
            rule.asset_kind,
            rule.scope.get("country_code", ""),
            rule.name,
        ),
    )
    return _ensure_unique_rule_names(sorted_rules)


def _build_pbr_record(
    *,
    runtime_path: Path,
    entry: dict[str, Any],
    resource_dirs: set[str],
    scanned_models: dict[tuple[str, str], list[VtdAssetRecord]],
) -> VtdAssetRecord:
    canonical_name = entry["pbr"] or entry["hcs"]
    country_codes = _normalize_country_codes([entry["cc"]] if entry["cc"] else [])
    matched_scan = _pick_scan_match(
        _filter_candidates_by_country_scope(
            _scan_candidates_for_canonical_name(scanned_models, canonical_name),
            country_codes,
        ),
        resource_dirs,
    )
    relative_path = _relative_path(runtime_path / "Tools" / "pbr_objects.xml", runtime_path)
    filename = canonical_name
    group_path = entry["root_element"]
    variant_tags = ["pbr"] if entry["pbr"] else []
    metadata: dict[str, Any] = {
        "config_kind": entry["config_kind"],
        "root_element": entry["root_element"],
    }

    if matched_scan is not None:
        relative_path = matched_scan.relative_path
        filename = matched_scan.filename
        group_path = matched_scan.group_path
        country_codes = _dedupe([*country_codes, *matched_scan.country_codes])
        variant_tags = _dedupe([*variant_tags, *matched_scan.variant_tags])
        metadata["matched_asset_kind"] = matched_scan.asset_kind
        metadata["merged_source_paths"] = [matched_scan.source_path]

    return VtdAssetRecord(
        asset_id=_build_asset_id("model", canonical_name, country_codes),
        asset_kind="model",
        canonical_name=canonical_name,
        display_name=canonical_name,
        filename=filename,
        relative_path=relative_path,
        source_path=_normalize_source_path(entry["source_path"], runtime_path),
        group_path=group_path,
        runtime_family="model",
        aliases=_dedupe(
            [entry["hcs"]] if entry["hcs"] and entry["hcs"] != entry["pbr"] else []
        ),
        country_codes=country_codes,
        variant_tags=variant_tags,
        metadata=metadata,
    )


def _build_dat_record(
    *,
    runtime_path: Path,
    entry: dict[str, Any],
    definition_kind: str,
    resource_dirs: set[str],
    scanned_models: dict[tuple[str, str], list[VtdAssetRecord]],
    consumed_scan_paths: set[str],
    consumed_model_overlap_keys: set[tuple[str, tuple[str, ...]]],
) -> VtdAssetRecord:
    canonical_name = entry["canonical_name"]
    normalized_source_path = _normalize_source_path(entry["source_path"], runtime_path)
    country_codes = _country_codes_for_path(
        normalized_source_path.split("#", maxsplit=1)[0],
        canonical_name,
    )
    candidates = _filter_candidates_by_country_scope(
        _dat_scan_candidates(
            definition_kind=definition_kind,
            canonical_name=canonical_name,
            scanned_models=scanned_models,
        ),
        country_codes,
    )
    matched_scan = _pick_scan_match(candidates, resource_dirs)
    metadata: dict[str, Any] = {
        "definition_kind": definition_kind,
    }
    relative_path = ""
    if matched_scan is not None:
        relative_path = matched_scan.relative_path
        consumed_scan_paths.add(matched_scan.source_path)
        metadata["merged_source_paths"] = [matched_scan.source_path]
        if definition_kind == "external":
            consumed_model_overlap_keys.add(
                _asset_overlap_key(canonical_name, country_codes)
            )
    return VtdAssetRecord(
        asset_id=_build_asset_id(definition_kind, canonical_name, country_codes),
        asset_kind=definition_kind,
        canonical_name=canonical_name,
        display_name=canonical_name,
        filename=entry["filename"],
        relative_path=relative_path,
        source_path=normalized_source_path,
        group_path=entry["group_path"],
        runtime_family=definition_kind,
        aliases=_dedupe(entry["aliases"]),
        country_codes=country_codes,
        variant_tags=[],
        metadata=metadata,
    )


def _scan_candidates_for_canonical_name(
    scanned_models: dict[tuple[str, str], list[VtdAssetRecord]],
    canonical_name: str,
) -> list[VtdAssetRecord]:
    candidates: list[VtdAssetRecord] = []
    for (_, scanned_name), records in scanned_models.items():
        if scanned_name != canonical_name:
            continue
        candidates.extend(records)
    return candidates


def _dat_scan_candidates(
    *,
    definition_kind: str,
    canonical_name: str,
    scanned_models: dict[tuple[str, str], list[VtdAssetRecord]],
) -> list[VtdAssetRecord]:
    exact_kind_candidates = scanned_models.get((definition_kind, canonical_name), [])
    if exact_kind_candidates:
        return exact_kind_candidates
    if definition_kind != "external":
        return exact_kind_candidates
    return _scan_candidates_for_canonical_name(scanned_models, canonical_name)


def _filter_candidates_by_country_scope(
    candidates: list[VtdAssetRecord],
    country_codes: list[str],
) -> list[VtdAssetRecord]:
    if not candidates:
        return []
    target_scope = tuple(sorted(country_codes))
    if target_scope:
        return [
            candidate
            for candidate in candidates
            if tuple(sorted(candidate.country_codes)) == target_scope
        ]
    exact_matches = [
        candidate
        for candidate in candidates
        if tuple(sorted(candidate.country_codes)) == target_scope
    ]
    return exact_matches or candidates


def _scan_model_records(
    runtime_path: Path,
    resource_dirs: set[str],
) -> dict[tuple[str, str], list[VtdAssetRecord]]:
    scanned: dict[tuple[str, str], list[VtdAssetRecord]] = defaultdict(list)
    for root_name in ("VisualLib/Models", "VisualLib/ModelsPBR"):
        for path in _iter_files(runtime_path / root_name):
            if path.suffix.lower() not in _MODEL_EXTENSIONS:
                continue
            record = _build_scanned_record(
                runtime_path,
                path,
                asset_kind=_infer_model_asset_kind(_relative_path(path, runtime_path)),
            )
            if root_name == "VisualLib/ModelsPBR":
                record = _with_variant_tag(record, "pbr")
            if _is_under_resource_dir(record.relative_path, resource_dirs):
                record.metadata["resource_dir_match"] = True
            scanned[(record.asset_kind, record.canonical_name)].append(record)
    return scanned


def _build_scanned_record(
    runtime_path: Path,
    path: Path,
    *,
    asset_kind: str,
) -> VtdAssetRecord:
    relative_path = _relative_path(path, runtime_path)
    canonical_name = path.stem
    country_codes = _country_codes_for_path(relative_path, canonical_name)
    return VtdAssetRecord(
        asset_id=_build_asset_id(asset_kind, canonical_name, country_codes),
        asset_kind=asset_kind,
        canonical_name=canonical_name,
        display_name=canonical_name,
        filename=path.name,
        relative_path=relative_path,
        source_path=_source_path(path, runtime_path),
        group_path=_relative_parent(path, runtime_path),
        runtime_family=asset_kind,
        aliases=[],
        country_codes=country_codes,
        variant_tags=[],
        metadata={},
    )


def _with_variant_tag(record: VtdAssetRecord, variant_tag: str) -> VtdAssetRecord:
    return VtdAssetRecord(
        asset_id=record.asset_id,
        asset_kind=record.asset_kind,
        canonical_name=record.canonical_name,
        display_name=record.display_name,
        filename=record.filename,
        relative_path=record.relative_path,
        source_path=record.source_path,
        group_path=record.group_path,
        runtime_family=record.runtime_family,
        aliases=record.aliases,
        country_codes=record.country_codes,
        variant_tags=_dedupe([*record.variant_tags, variant_tag]),
        metadata=record.metadata,
    )


def _store_record(bucket: dict[str, VtdAssetRecord], incoming: VtdAssetRecord) -> None:
    existing = bucket.get(incoming.asset_id)
    if existing is None:
        bucket[incoming.asset_id] = incoming
        return
    bucket[incoming.asset_id] = VtdAssetRecord(
        asset_id=existing.asset_id,
        asset_kind=existing.asset_kind,
        canonical_name=existing.canonical_name,
        display_name=existing.display_name or incoming.display_name,
        filename=existing.filename or incoming.filename,
        relative_path=existing.relative_path or incoming.relative_path,
        source_path=existing.source_path or incoming.source_path,
        group_path=existing.group_path or incoming.group_path,
        runtime_family=existing.runtime_family or incoming.runtime_family,
        aliases=_dedupe([*existing.aliases, *incoming.aliases]),
        country_codes=_dedupe([*existing.country_codes, *incoming.country_codes]),
        variant_tags=_dedupe([*existing.variant_tags, *incoming.variant_tags]),
        metadata=_merge_metadata(existing.metadata, incoming.metadata),
    )


def _merge_metadata(
    existing: dict[str, Any],
    incoming: dict[str, Any],
) -> dict[str, Any]:
    merged = copy.deepcopy(existing)
    for key, value in incoming.items():
        if key not in merged:
            merged[key] = copy.deepcopy(value)
            continue
        if isinstance(merged[key], list) and isinstance(value, list):
            merged[key] = _dedupe([*merged[key], *value])
            continue
        if not merged[key] and value:
            merged[key] = copy.deepcopy(value)
    return merged


def _load_resource_dirs(runtime_path: Path) -> set[str]:
    resource_dirs_path = runtime_path / "Tools" / "resourceDirs.txt"
    if not resource_dirs_path.is_file():
        return set()
    return {
        entry["resource_dir"]
        for entry in parse_resource_dirs(resource_dirs_path)
        if entry["resource_dir"]
    }


def _pick_scan_match(
    candidates: list[VtdAssetRecord],
    resource_dirs: set[str],
) -> VtdAssetRecord | None:
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda record: (
            not _is_under_resource_dir(record.relative_path, resource_dirs),
            len(Path(record.relative_path).parts),
            record.relative_path,
        ),
    )[0]


def _infer_dat_definition_kind(path: Path) -> str:
    name = path.name.upper()
    if "SIGNAL" in name:
        return "signal"
    if "EXTERNAL" in name:
        return "external"
    return ""


def _infer_model_asset_kind(relative_path: str) -> str:
    if "/Signals/" in f"/{relative_path}/":
        return "signal"
    if "/Externals/" in f"/{relative_path}/":
        return "external"
    return "model"


def _bucket_for_asset_kind(asset_kind: str) -> str:
    return {
        "signal": "signals.jsonl",
        "external": "externals.jsonl",
        "model": "models.jsonl",
        "style": "styles.jsonl",
        "tile": "tiles.jsonl",
        "addon": "addons.jsonl",
        "macro": "macros.jsonl",
        "sample": "samples.jsonl",
        "decal": "decals.jsonl",
    }[asset_kind]


def _build_asset_id(
    asset_kind: str,
    canonical_name: str,
    country_codes: list[str],
) -> str:
    country_codes = _normalize_country_codes(country_codes)
    if not country_codes:
        return f"{asset_kind}:{canonical_name}"
    country_scope = "+".join(sorted(country_codes))
    return f"{asset_kind}:{country_scope}:{canonical_name}"


def _country_codes_for_path(relative_path: str, canonical_name: str) -> list[str]:
    country_codes: list[str] = []
    for segment in Path(relative_path).parts:
        match = _COUNTRY_SEGMENT_RE.match(segment)
        if match:
            country_codes.append(_normalize_country_code(match.group(1)))
    prefix, _, _ = canonical_name.partition("_")
    if prefix in _TRUSTED_NAME_PREFIX_COUNTRY_CODES:
        country_codes.append(_normalize_country_code(prefix))
    return _normalize_country_codes(country_codes)


def _collision_severity(
    *,
    asset: VtdAssetRecord,
    candidate_asset_kind: str,
    candidate_country_code: str,
) -> str:
    same_kind = candidate_asset_kind == asset.asset_kind
    if not same_kind:
        return "warning"
    if not candidate_country_code or not asset.country_codes:
        return "high"
    return "high" if candidate_country_code in asset.country_codes else "warning"


def _soft_namespace_collision_severity(
    *,
    asset: VtdAssetRecord,
    candidate_asset_kind: str,
    candidate_country_code: str,
) -> str:
    severity = _collision_severity(
        asset=asset,
        candidate_asset_kind=candidate_asset_kind,
        candidate_country_code=candidate_country_code,
    )
    return "warning" if severity == "high" else severity


def _collision_reason(
    *,
    asset: VtdAssetRecord,
    candidate_asset_kind: str,
    candidate_country_code: str,
) -> str:
    if candidate_asset_kind != asset.asset_kind:
        return "Name collides with an existing runtime asset in the same namespace."
    if candidate_country_code and asset.country_codes:
        if candidate_country_code not in asset.country_codes:
            return "Name collides with a country-scoped runtime asset in another country."
    return "Name collides exactly with an existing runtime asset in the same scope."


def _soft_namespace_collision_reason(
    *,
    namespace: str,
    asset: VtdAssetRecord,
) -> str:
    return (
        f"Name overlaps the runtime asset '{asset.canonical_name}' inside the "
        f"'{namespace}' namespace."
    )


def _rule_name(
    prefix: str,
    namespace: str,
    asset_kind: str,
    country_code: str,
    value: str,
    discriminator: str,
) -> str:
    country_segment = country_code.lower() if country_code else "global"
    token = hashlib.sha1(
        "\x1f".join(
            [prefix, namespace, asset_kind, country_code, value, discriminator]
        ).encode("utf-8")
    ).hexdigest()[:10]
    return (
        f"{prefix}-{_slugify(namespace)}-{asset_kind}-{country_segment}-"
        f"{_slugify(value)}-{_slugify(discriminator)}-{token}"
    )


def _slugify(value: str) -> str:
    slug = _SLUG_RE.sub("-", value.lower()).strip("-")
    return slug or "unnamed"


def _name_compare_key(value: str) -> str:
    return value.lower()


def _relative_path(path: Path, runtime_path: Path) -> str:
    return path.relative_to(runtime_path).as_posix()


def _relative_parent(path: Path, runtime_path: Path) -> str:
    return path.parent.relative_to(runtime_path).as_posix()


def _source_path(path: Path, runtime_path: Path) -> str:
    return path.relative_to(runtime_path).as_posix()


def _normalize_source_path(source_path: str, runtime_path: Path) -> str:
    path_text, separator, suffix = source_path.partition("#")
    candidate_path = Path(path_text)
    try:
        normalized = candidate_path.resolve().relative_to(runtime_path.resolve()).as_posix()
    except ValueError:
        normalized = candidate_path.as_posix()
    if not separator:
        return normalized
    return f"{normalized}#{suffix}"


def _asset_overlap_key(
    canonical_name: str,
    country_codes: list[str],
) -> tuple[str, tuple[str, ...]]:
    return (canonical_name, tuple(sorted(_normalize_country_codes(country_codes))))


def _ensure_unique_rule_names(rules: list[VtdNameRule]) -> list[VtdNameRule]:
    seen_counts: dict[str, int] = {}
    for rule in rules:
        count = seen_counts.get(rule.name, 0) + 1
        seen_counts[rule.name] = count
        if count == 1:
            continue
        rule.name = f"{rule.name}-{count}"
    return rules


def _normalize_country_code(value: str) -> str:
    if not value:
        return ""
    normalized = value.strip()
    if not normalized:
        return ""
    aliased = _COUNTRY_CODE_ALIASES.get(normalized.casefold())
    if aliased:
        return aliased
    if len(normalized) <= 3 and normalized.isalpha():
        return normalized.upper()
    return normalized


def _policy_country_scope(
    country_code: str,
    alias_to_country: dict[str, str],
) -> str:
    normalized_country = _normalize_country_code(country_code)
    if not normalized_country:
        return ""
    return alias_to_country.get(normalized_country.casefold(), normalized_country)


def _policy_id(
    *,
    namespace: str,
    asset_kind: str,
    country_scope: str,
    match_name: str,
) -> str:
    country_segment = country_scope.lower() if country_scope else "global"
    return (
        f"policy-{_slugify(namespace)}-{asset_kind}-{country_segment}-"
        f"{_slugify(match_name)}"
    )


def _normalize_country_codes(values: Iterable[str]) -> list[str]:
    normalized_values = [_normalize_country_code(value) for value in values]
    return _dedupe(normalized_values)


def _is_under_resource_dir(relative_path: str, resource_dirs: set[str]) -> bool:
    return any(
        relative_path == resource_dir or relative_path.startswith(f"{resource_dir}/")
        for resource_dir in resource_dirs
    )


def _iter_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file())


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


__all__ = [
    "build_asset_buckets",
    "build_asset_records",
    "build_country_taxonomy",
    "build_extractor_manifest",
    "build_name_policies",
    "build_name_rules",
    "build_reserved_name_candidates",
]
