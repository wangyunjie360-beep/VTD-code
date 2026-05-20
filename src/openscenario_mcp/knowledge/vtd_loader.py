from __future__ import annotations

import json
from dataclasses import asdict
from fnmatch import fnmatchcase
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from openscenario_mcp.knowledge.vtd_semantic import (
    build_vtd_semantic_knowledge_base,
    serialize_vtd_semantic_knowledge_base,
)
from openscenario_mcp.knowledge.vtd_snapshot import (
    build_asset_records,
    build_country_taxonomy,
    build_extractor_manifest,
    build_name_policies,
    build_name_rules,
    build_reserved_name_candidates,
)
from openscenario_mcp.models import (
    SourceEntry,
    VtdAssetFamily,
    VtdAssetRecord,
    VtdAssetVariant,
    VtdKnowledgeBase,
    VtdNamePolicy,
    VtdNameRule,
    VtdSemanticKnowledgeBase,
)

_EXPECTED_RUNTIME_PARENT = "VTD.2020"
_EXPECTED_RUNTIME_NAME = "Runtime"
_EXPECTED_RELEASE_NAME = "RodDistro_6980_Rod4.6.1"
_SNAPSHOT_SOURCE_ENTRY = {
    "id": "vtd-runtime",
    "kind": "runtime",
    "path": "knowledge/structured/vtd",
}
_ASSET_BUCKET_FILES = {
    "signals": "signals.jsonl",
    "externals": "externals.jsonl",
    "decals": "decals.jsonl",
    "models": "models.jsonl",
    "styles": "styles.jsonl",
    "tiles": "tiles.jsonl",
    "addons": "addons.jsonl",
    "macros": "macros.jsonl",
    "samples": "samples.jsonl",
}
_RULE_BUCKET_FILES = {
    "reserved-names": "reserved-names.jsonl",
    "aliases": "aliases.jsonl",
    "country-preferences": "country-preferences.jsonl",
}
_ASSET_KIND_TO_BUCKET = {
    "signal": "signals",
    "external": "externals",
    "decal": "decals",
    "model": "models",
    "style": "styles",
    "tile": "tiles",
    "addon": "addons",
    "macro": "macros",
    "sample": "samples",
}
_RULE_KIND_TO_BUCKET = {
    "reserved_name": "reserved-names",
    "alias": "aliases",
    "country_preference": "country-preferences",
}
_SEMANTIC_COUNTRY_TAXONOMY_FILE = "country-taxonomy.json"
_SEMANTIC_NAME_POLICIES_FILE = "name-policies.jsonl"
_SEMANTIC_ASSET_FAMILIES_FILE = "asset-families.jsonl"
_SEMANTIC_ASSET_VARIANTS_FILE = "asset-variants.jsonl"
_SEMANTIC_SOURCE_PROVENANCE_FILE = "source-provenance.jsonl"
_SEMANTIC_SOURCE_ROOT = "knowledge/structured/vtd/semantic"
_REQUIRED_RELEASE_PATHS = (
    "Tools/resourceDirs.txt",
    "Tools/pbr_objects.xml",
    "DefaultProject/Config",
    "Samples",
    "VisualLib/Models",
    "VisualLib/Styles",
    "VisualLib/TileLib",
)
_APPROVED_PHASE1_SOURCE_SET = (
    ("file", "Tools/pbr_objects.xml"),
    ("directory", "VisualLib/Models"),
    ("directory", "VisualLib/ModelsPBR"),
    ("directory", "VisualLib/Styles"),
    ("directory", "VisualLib/TileLib"),
    ("glob", "VisualLib/Models/**/SetupFiles/*.DAT"),
    ("glob", "DefaultProject/Config/decalScatter*.xml"),
    ("glob", "DefaultProject/Config/Macros/*.rmcr"),
    ("glob", "Samples/*.tdo"),
    ("glob", "AddOns/**/*.xml"),
)
_RELEASE_RELATIVE_ROOTS = (
    "DefaultProject",
    "Samples",
    "Tools",
    "VisualLib",
)


def build_vtd_knowledge_snapshot(
    runtime_root: str | Path,
    snapshot_root: str | Path = Path("knowledge/structured/vtd"),
    *,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime_path = Path(runtime_root)
    release_root = resolve_vtd_phase1_release_root(runtime_path)
    manifest_payload = _resolve_manifest(Path(snapshot_root), manifest)
    assets = _merge_asset_records(
        [
            asset
            for asset in build_asset_records(release_root)
            if asset.asset_kind != "addon"
        ],
        [
            asset
            for asset in build_asset_records(runtime_path)
            if asset.asset_kind == "addon"
        ],
    )
    rules = build_name_rules(
        assets,
        candidate_names=build_reserved_name_candidates(assets),
    )
    return write_vtd_snapshot(
        snapshot_root=snapshot_root,
        assets=assets,
        rules=rules,
        runtime_root=runtime_path,
        release_root=release_root,
        manifest=manifest_payload,
    )


def write_vtd_snapshot(
    *,
    snapshot_root: str | Path,
    assets: Iterable[VtdAssetRecord],
    rules: Iterable[VtdNameRule],
    runtime_root: str | Path,
    release_root: str | Path,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    snapshot_path = Path(snapshot_root)
    runtime_path = Path(runtime_root)
    release_path = Path(release_root)
    release_prefix = _release_prefix(runtime_path, release_path)
    manifest_payload = _resolve_manifest(snapshot_path, manifest)
    asset_records = list(assets)
    rule_records = list(rules)
    asset_buckets = {bucket: [] for bucket in _ASSET_BUCKET_FILES}
    rule_buckets = {bucket: [] for bucket in _RULE_BUCKET_FILES}

    for asset in asset_records:
        normalized_asset = _normalize_asset_record(asset, release_prefix)
        bucket_name = _ASSET_KIND_TO_BUCKET.get(asset.asset_kind)
        if bucket_name is None:
            raise ValueError(f"Unsupported VTD asset kind: {asset.asset_kind}")
        _validate_snapshot_path(
            manifest_payload,
            path_text=normalized_asset.source_path,
            record_kind="asset source",
            record_name=normalized_asset.asset_id,
            release_prefix=release_prefix,
        )
        _validate_snapshot_path(
            manifest_payload,
            path_text=normalized_asset.relative_path,
            record_kind="asset runtime",
            record_name=normalized_asset.asset_id,
            allow_empty=True,
            release_prefix=release_prefix,
        )
        asset_buckets[bucket_name].append(normalized_asset)

    for rule in rule_records:
        normalized_rule = _normalize_rule(rule, release_prefix)
        bucket_name = _RULE_KIND_TO_BUCKET.get(rule.rule_kind)
        if bucket_name is None:
            raise ValueError(f"Unsupported VTD rule kind: {rule.rule_kind}")
        _validate_snapshot_path(
            manifest_payload,
            path_text=normalized_rule.source_path,
            record_kind="rule source",
            record_name=normalized_rule.name,
            release_prefix=release_prefix,
        )
        rule_buckets[bucket_name].append(normalized_rule)

    assets_path = snapshot_path / "assets"
    rules_path = snapshot_path / "rules"
    semantic_path = snapshot_path / "semantic"
    assets_path.mkdir(parents=True, exist_ok=True)
    rules_path.mkdir(parents=True, exist_ok=True)
    semantic_path.mkdir(parents=True, exist_ok=True)

    for bucket_name, filename in _ASSET_BUCKET_FILES.items():
        _write_jsonl(
            assets_path / filename,
            sorted(asset_buckets[bucket_name], key=_asset_sort_key),
        )

    for bucket_name, filename in _RULE_BUCKET_FILES.items():
        _write_jsonl(
            rules_path / filename,
            sorted(rule_buckets[bucket_name], key=_rule_sort_key),
        )

    country_taxonomy = build_country_taxonomy(
        assets=[asset for bucket in asset_buckets.values() for asset in bucket],
        rules=[rule for bucket in rule_buckets.values() for rule in bucket],
    )
    name_policies = _materialize_name_policy_sources(
        build_name_policies(
            [rule for bucket in rule_buckets.values() for rule in bucket],
            country_taxonomy=country_taxonomy,
        )
    )
    semantic_seed = _build_semantic_seed_knowledge_base(
        assets=[asset for bucket in asset_buckets.values() for asset in bucket],
        rules=[rule for bucket in rule_buckets.values() for rule in bucket],
        runtime_root=runtime_root,
        release_root=release_root,
        summary_sources=[_SNAPSHOT_SOURCE_ENTRY],
        country_taxonomy=country_taxonomy,
        name_policies=name_policies,
    )
    semantic_knowledge_base, provenance_records = build_vtd_semantic_knowledge_base(
        semantic_seed
    )
    family_records, variant_records, policy_records = serialize_vtd_semantic_knowledge_base(
        semantic_knowledge_base
    )
    _write_json(
        semantic_path / _SEMANTIC_COUNTRY_TAXONOMY_FILE,
        country_taxonomy,
    )
    _write_jsonl_objects(
        semantic_path / _SEMANTIC_NAME_POLICIES_FILE,
        name_policies,
    )
    _write_jsonl_objects(
        semantic_path / _SEMANTIC_ASSET_FAMILIES_FILE,
        family_records,
    )
    _write_jsonl_objects(
        semantic_path / _SEMANTIC_ASSET_VARIANTS_FILE,
        variant_records,
    )
    _write_jsonl_objects(
        semantic_path / _SEMANTIC_SOURCE_PROVENANCE_FILE,
        provenance_records,
    )

    summary = _build_summary(
        asset_buckets=asset_buckets,
        rule_buckets=rule_buckets,
        runtime_root=runtime_root,
        release_root=release_root,
        manifest=manifest_payload,
        country_taxonomy=country_taxonomy,
        name_policies=name_policies,
    )
    _write_json(snapshot_path / "summary.json", summary)
    return summary


def load_vtd_snapshot(
    snapshot_root: str | Path = Path("knowledge/structured/vtd"),
) -> VtdKnowledgeBase:
    snapshot_path = Path(snapshot_root)
    summary = _load_summary(snapshot_path / "summary.json")
    assets: list[VtdAssetRecord] = []
    rules: list[VtdNameRule] = []

    for bucket_name, filename in _ASSET_BUCKET_FILES.items():
        assets.extend(
            _load_jsonl(snapshot_path / "assets" / filename, bucket_name, VtdAssetRecord)
        )

    for bucket_name, filename in _RULE_BUCKET_FILES.items():
        rules.extend(
            _load_jsonl(snapshot_path / "rules" / filename, bucket_name, VtdNameRule)
        )

    _validate_summary_counts(summary, assets, rules)
    country_taxonomy = _load_country_taxonomy(
        snapshot_path / "semantic" / _SEMANTIC_COUNTRY_TAXONOMY_FILE,
        assets,
        rules,
    )
    name_policies = _load_name_policies(
        snapshot_path / "semantic" / _SEMANTIC_NAME_POLICIES_FILE,
        rules,
        country_taxonomy,
    )
    _validate_summary_semantics(summary, country_taxonomy, name_policies)
    assets_by_id = _index_assets_by_id(assets)
    assets_by_canonical_name, canonical_collisions = _index_assets_by_canonical_name(
        assets
    )
    rules_by_name = _index_rules_by_name(rules)
    sources = [
        SourceEntry(
            id=str(entry["id"]),
            kind=str(entry["kind"]),
            path=str(entry["path"]),
        )
        for entry in _require_sources(summary)
    ]
    metadata = {
        "summary": summary,
        "runtime_root": summary.get("runtime_root", ""),
        "release_root": summary.get("release_root", ""),
        "release_name": summary.get("release_name", ""),
        "canonical_collisions": canonical_collisions,
        "country_taxonomy": country_taxonomy,
        "name_policies": name_policies,
    }
    return VtdKnowledgeBase(
        runtime_root=str(summary.get("runtime_root", "")),
        assets_by_id=assets_by_id,
        assets_by_canonical_name=assets_by_canonical_name,
        rules_by_name=rules_by_name,
        sources=sources,
        metadata=metadata,
    )


def load_vtd_semantic_snapshot(
    snapshot_root: str | Path = Path("knowledge/structured/vtd"),
) -> VtdSemanticKnowledgeBase:
    snapshot_path = Path(snapshot_root)
    semantic_path = snapshot_path / "semantic"
    if not semantic_path.is_dir():
        raise FileNotFoundError(
            f"Structured VTD semantic directory not found at {semantic_path.as_posix()}."
        )

    families = _load_jsonl(
        semantic_path / _SEMANTIC_ASSET_FAMILIES_FILE,
        "semantic-asset-families",
        VtdAssetFamily,
    )
    variants = _load_jsonl(
        semantic_path / _SEMANTIC_ASSET_VARIANTS_FILE,
        "semantic-asset-variants",
        VtdAssetVariant,
    )
    name_policies = _load_semantic_name_policies(
        semantic_path / _SEMANTIC_NAME_POLICIES_FILE
    )
    provenance_records = _load_jsonl_objects(
        semantic_path / _SEMANTIC_SOURCE_PROVENANCE_FILE,
        "semantic-source-provenance",
    )

    return VtdSemanticKnowledgeBase(
        families_by_id={family.family_id: family for family in families},
        variants_by_id={variant.variant_id: variant for variant in variants},
        name_policies_by_id={
            policy.policy_id: policy for policy in name_policies if policy.policy_id
        },
        sources=[
            SourceEntry(
                id="vtd-semantic",
                kind="semantic",
                path=_SEMANTIC_SOURCE_ROOT,
            )
        ],
        metadata={
            "root": semantic_path.as_posix(),
            "exists": True,
            "status": "loaded",
            "source_provenance": provenance_records,
        },
    )


def resolve_vtd_phase1_release_root(runtime_root: str | Path) -> Path:
    runtime_path = Path(runtime_root)
    if (
        runtime_path.name != _EXPECTED_RUNTIME_NAME
        or runtime_path.parent.name != _EXPECTED_RUNTIME_PARENT
    ):
        raise ValueError(
            "Expected runtime root to end with "
            f"'{_EXPECTED_RUNTIME_PARENT}/{_EXPECTED_RUNTIME_NAME}', got "
            f"'{runtime_path.as_posix()}'."
        )

    release_root = runtime_path / "Tools" / _EXPECTED_RELEASE_NAME
    if not release_root.is_dir():
        raise ValueError(
            "Expected phase-1 VTD release directory "
            f"'{_EXPECTED_RELEASE_NAME}' under '{(runtime_path / 'Tools').as_posix()}'."
        )

    missing_paths = [
        relative_path
        for relative_path in _REQUIRED_RELEASE_PATHS
        if not (release_root / relative_path).exists()
    ]
    if missing_paths:
        missing_text = ", ".join(missing_paths)
        raise ValueError(
            "The phase-1 VTD release tree is incomplete. Missing: "
            f"{missing_text}."
        )

    return release_root


def _build_summary(
    *,
    asset_buckets: dict[str, list[VtdAssetRecord]],
    rule_buckets: dict[str, list[VtdNameRule]],
    runtime_root: str | Path,
    release_root: str | Path,
    manifest: dict[str, Any],
    country_taxonomy: dict[str, Any],
    name_policies: list[dict[str, Any]],
) -> dict[str, Any]:
    asset_counts = {
        bucket_name: len(asset_buckets[bucket_name]) for bucket_name in _ASSET_BUCKET_FILES
    }
    rule_counts = {
        bucket_name: len(rule_buckets[bucket_name]) for bucket_name in _RULE_BUCKET_FILES
    }
    return {
        "version": int(manifest["version"]),
        "phase": str(manifest["phase"]),
        "runtime_family": _EXPECTED_RUNTIME_PARENT,
        "release_name": _EXPECTED_RELEASE_NAME,
        "runtime_root": _normalize_display_path(runtime_root),
        "release_root": _normalize_display_path(release_root),
        "source_id": _SNAPSHOT_SOURCE_ENTRY["id"],
        "sources": [_SNAPSHOT_SOURCE_ENTRY],
        "asset_counts": asset_counts,
        "rule_counts": rule_counts,
        "semantic_counts": {
            "country-taxonomy": len(country_taxonomy.get("countries", {})),
            "name-policies": len(name_policies),
        },
        "asset_total": sum(asset_counts.values()),
        "rule_total": sum(rule_counts.values()),
    }


def _merge_asset_records(
    primary: Iterable[VtdAssetRecord],
    secondary: Iterable[VtdAssetRecord],
) -> list[VtdAssetRecord]:
    merged: dict[str, VtdAssetRecord] = {}
    for asset in primary:
        merged[asset.asset_id] = asset
    for asset in secondary:
        merged.setdefault(asset.asset_id, asset)
    return list(merged.values())


def _resolve_manifest(
    snapshot_root: Path,
    manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    if manifest is not None:
        payload = manifest
    else:
        manifest_path = snapshot_root / "extractor_manifest.json"
        if manifest_path.is_file():
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        else:
            payload = build_extractor_manifest()
    _validate_manifest(payload)
    return payload


def _validate_manifest(manifest: dict[str, Any]) -> None:
    expected = build_extractor_manifest()
    if not isinstance(manifest, dict):
        raise ValueError("VTD extractor manifest must be a JSON object.")

    if manifest.get("version") != expected["version"]:
        raise ValueError(
            "VTD phase-1 manifest version does not match the approved source set."
        )
    if manifest.get("phase") != expected["phase"]:
        raise ValueError(
            "VTD phase-1 manifest phase does not match the approved source set."
        )
    if manifest.get("buckets") != expected["buckets"]:
        raise ValueError(
            "VTD phase-1 manifest buckets do not match the approved source set."
        )

    allowlist = manifest.get("allowlist")
    if allowlist != expected["allowlist"]:
        extra_matches = _manifest_delta_matches(
            actual=allowlist if isinstance(allowlist, list) else [],
            expected=expected["allowlist"],
        )
        detail = ", ".join(extra_matches) if extra_matches else "allowlist mismatch"
        raise ValueError(
            "VTD phase-1 manifest allowlist does not match the approved source set: "
            f"{detail}."
        )


def _manifest_delta_matches(
    *,
    actual: list[dict[str, Any]],
    expected: list[dict[str, Any]],
) -> list[str]:
    expected_entries = {json.dumps(entry, sort_keys=True) for entry in expected}
    deltas: list[str] = []
    for entry in actual:
        encoded = json.dumps(entry, sort_keys=True)
        if encoded in expected_entries:
            continue
        match = entry.get("match")
        deltas.append(str(match) if match is not None else encoded)
    return deltas


def _validate_snapshot_path(
    manifest: dict[str, Any],
    *,
    path_text: str,
    record_kind: str,
    record_name: str,
    release_prefix: str,
    allow_empty: bool = False,
) -> None:
    if not path_text:
        if allow_empty:
            return
        raise ValueError(f"Missing {record_kind} path for '{record_name}'.")

    relative_path = _normalize_manifest_path(path_text)
    if not _matches_phase1_source_set(relative_path, release_prefix=release_prefix):
        raise ValueError(
            f"VTD phase-1 {record_kind} path for '{record_name}' is out of scope: "
            f"{relative_path}."
        )


def _normalize_manifest_path(path_text: str) -> str:
    path_only, _, _ = path_text.partition("#")
    normalized = path_only.replace("\\", "/").strip()
    if not normalized:
        return ""
    if normalized.startswith("/"):
        raise ValueError(f"Expected a repository-relative VTD path, got '{path_text}'.")
    if len(normalized) >= 2 and normalized[1] == ":":
        raise ValueError(f"Expected a relative VTD path, got '{path_text}'.")

    parts = [segment for segment in normalized.split("/") if segment not in {"", "."}]
    if any(segment == ".." for segment in parts):
        raise ValueError(f"VTD path escapes the phase-1 root: '{path_text}'.")
    return "/".join(parts)


def _normalize_asset_record(
    asset: VtdAssetRecord,
    release_prefix: str,
) -> VtdAssetRecord:
    source_path = asset.source_path
    if (
        asset.asset_kind == "addon"
        and asset.relative_path.startswith("AddOns/")
        and "#" not in source_path
    ):
        source_path = asset.relative_path

    return VtdAssetRecord(
        asset_id=asset.asset_id,
        asset_kind=asset.asset_kind,
        canonical_name=asset.canonical_name,
        display_name=asset.display_name,
        filename=asset.filename,
        relative_path=_normalize_record_path(asset.relative_path, release_prefix),
        source_path=_normalize_record_path(source_path, release_prefix),
        group_path=asset.group_path,
        runtime_family=asset.runtime_family,
        aliases=list(asset.aliases),
        country_codes=list(asset.country_codes),
        variant_tags=list(asset.variant_tags),
        metadata=_normalize_asset_metadata(asset.metadata, release_prefix),
    )


def _normalize_rule(
    rule: VtdNameRule,
    release_prefix: str,
) -> VtdNameRule:
    return VtdNameRule(
        name=rule.name,
        rule_kind=rule.rule_kind,
        severity=rule.severity,
        canonical_target=rule.canonical_target,
        asset_kind=rule.asset_kind,
        reason=rule.reason,
        source_path=_normalize_record_path(rule.source_path, release_prefix),
        scope=dict(rule.scope),
        metadata=dict(rule.metadata),
    )


def _normalize_asset_metadata(
    metadata: dict[str, Any],
    release_prefix: str,
) -> dict[str, Any]:
    normalized = dict(metadata)
    merged_source_paths = normalized.get("merged_source_paths")
    if isinstance(merged_source_paths, list):
        normalized["merged_source_paths"] = [
            _normalize_record_path(path, release_prefix)
            for path in merged_source_paths
            if isinstance(path, str)
        ]
    return normalized


def _normalize_record_path(path_text: str, release_prefix: str) -> str:
    if not path_text:
        return ""

    path_only, separator, suffix = path_text.partition("#")
    normalized_path = _normalize_manifest_path(path_only)
    if not normalized_path:
        return ""

    if normalized_path.startswith("AddOns/") or normalized_path == "AddOns":
        normalized = normalized_path
    elif release_prefix and (
        normalized_path == release_prefix
        or normalized_path.startswith(f"{release_prefix}/")
    ):
        normalized = normalized_path
    elif _is_release_relative_path(normalized_path):
        normalized = f"{release_prefix}/{normalized_path}"
    else:
        normalized = normalized_path

    if not separator:
        return normalized
    return f"{normalized}#{suffix}"


def _is_release_relative_path(path_text: str) -> bool:
    return any(
        path_text == root_name or path_text.startswith(f"{root_name}/")
        for root_name in _RELEASE_RELATIVE_ROOTS
    )


def _release_prefix(runtime_root: Path, release_root: Path) -> str:
    return release_root.relative_to(runtime_root).as_posix()


def _strip_release_prefix(relative_path: str, release_prefix: str) -> str:
    if not release_prefix:
        return relative_path
    if relative_path == release_prefix:
        return ""

    prefix = f"{release_prefix}/"
    if relative_path.startswith(prefix):
        return relative_path[len(prefix) :]
    return relative_path


def _matches_allowlist(relative_path: str, allowlist: list[dict[str, Any]]) -> bool:
    for entry in allowlist:
        match = str(entry.get("match", ""))
        match_type = str(entry.get("match_type", ""))
        if match_type == "file" and relative_path == match:
            return True
        if match_type == "directory" and (
            relative_path == match or relative_path.startswith(f"{match}/")
        ):
            return True
        if match_type == "glob" and _glob_match(relative_path, match):
            return True
    return False


def _matches_phase1_source_set(relative_path: str, *, release_prefix: str) -> bool:
    candidate_path = _strip_release_prefix(relative_path, release_prefix)
    for match_type, match in _APPROVED_PHASE1_SOURCE_SET:
        if match_type == "file" and candidate_path == match:
            return True
        if match_type == "directory" and (
            candidate_path == match or candidate_path.startswith(f"{match}/")
        ):
            return True
        if match_type == "glob" and _glob_match(candidate_path, match):
            return True
    return False


def _glob_match(relative_path: str, pattern: str) -> bool:
    path_parts = tuple(part for part in relative_path.split("/") if part)
    pattern_parts = tuple(part for part in pattern.split("/") if part)

    @lru_cache(maxsize=None)
    def matches(path_index: int, pattern_index: int) -> bool:
        if pattern_index == len(pattern_parts):
            return path_index == len(path_parts)

        token = pattern_parts[pattern_index]
        if token == "**":
            return matches(path_index, pattern_index + 1) or (
                path_index < len(path_parts) and matches(path_index + 1, pattern_index)
            )

        if path_index >= len(path_parts):
            return False

        if not fnmatchcase(path_parts[path_index], token):
            return False
        return matches(path_index + 1, pattern_index + 1)

    return matches(0, 0)


def _write_jsonl(path: Path, records: Iterable[VtdAssetRecord | VtdNameRule]) -> None:
    lines = [
        json.dumps(asdict(record), ensure_ascii=False, sort_keys=True)
        for record in records
    ]
    content = "\n".join(lines)
    if content:
        content = f"{content}\n"
    path.write_text(content, encoding="utf-8")


def _write_jsonl_objects(path: Path, records: Iterable[dict[str, Any]]) -> None:
    lines = [
        json.dumps(record, ensure_ascii=False, sort_keys=True)
        for record in records
    ]
    content = "\n".join(lines)
    if content:
        content = f"{content}\n"
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def _load_summary(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("VTD snapshot summary must be a JSON object.")
    return payload


def _load_jsonl(
    path: Path,
    bucket_name: str,
    record_type: type[VtdAssetRecord]
    | type[VtdNameRule]
    | type[VtdAssetFamily]
    | type[VtdAssetVariant]
    | type[VtdNamePolicy],
) -> list[VtdAssetRecord] | list[VtdNameRule] | list[VtdAssetFamily] | list[VtdAssetVariant] | list[VtdNamePolicy]:
    if not path.is_file():
        raise ValueError(f"Missing VTD snapshot bucket '{bucket_name}': {path.as_posix()}")

    records: (
        list[VtdAssetRecord]
        | list[VtdNameRule]
        | list[VtdAssetFamily]
        | list[VtdAssetVariant]
        | list[VtdNamePolicy]
    ) = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(
                f"VTD snapshot bucket '{bucket_name}' line {line_number} must be an object."
            )
        records.append(record_type(**payload))
    return records


def _load_semantic_name_policies(path: Path) -> list[VtdNamePolicy]:
    raw_policies = _load_jsonl_objects(path, "semantic-name-policies")
    policies: list[VtdNamePolicy] = []
    for payload in raw_policies:
        policies.append(
            VtdNamePolicy(
                policy_id=str(payload.get("policy_id", "")).strip(),
                namespace=str(payload.get("namespace", "")).strip(),
                asset_kind=str(payload.get("asset_kind", "")).strip(),
                country_scope=str(payload.get("country_scope", "")).strip(),
                rule_kind=str(payload.get("rule_kind", "")).strip(),
                severity=str(payload.get("severity", "")).strip(),
                match_mode=str(payload.get("match_mode", "")).strip(),
                canonical_target=str(payload.get("canonical_target", "")).strip(),
                safe_name_strategy=str(payload.get("safe_name_strategy", "")).strip(),
                reason=str(payload.get("reason", "")).strip(),
                source_paths=[
                    source_path
                    for source_path in payload.get("source_paths", [])
                    if isinstance(source_path, str) and source_path.strip()
                ],
            )
        )
    return policies


def _load_jsonl_objects(path: Path, bucket_name: str) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f"Missing VTD snapshot bucket '{bucket_name}': {path.as_posix()}")

    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(
                f"VTD snapshot bucket '{bucket_name}' line {line_number} must be a JSON object."
            )
        records.append(payload)
    return records


def _load_country_taxonomy(
    path: Path,
    assets: list[VtdAssetRecord],
    rules: list[VtdNameRule],
) -> dict[str, Any]:
    if not path.is_file():
        return build_country_taxonomy(assets, rules)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("VTD country taxonomy must be a JSON object.")
    return payload


def _load_name_policies(
    path: Path,
    rules: list[VtdNameRule],
    country_taxonomy: dict[str, Any],
) -> list[dict[str, Any]]:
    if not path.is_file():
        return _materialize_name_policy_sources(
            build_name_policies(rules, country_taxonomy=country_taxonomy)
        )

    policies: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(
                f"VTD name policy line {line_number} must be a JSON object."
            )
        policies.append(payload)
    return policies


def _validate_summary_counts(
    summary: dict[str, Any],
    assets: list[VtdAssetRecord],
    rules: list[VtdNameRule],
) -> None:
    expected_asset_counts = {bucket_name: 0 for bucket_name in _ASSET_BUCKET_FILES}
    expected_rule_counts = {bucket_name: 0 for bucket_name in _RULE_BUCKET_FILES}

    for asset in assets:
        bucket_name = _ASSET_KIND_TO_BUCKET.get(asset.asset_kind)
        if bucket_name is None:
            raise ValueError(f"Unsupported VTD asset kind in snapshot: {asset.asset_kind}")
        expected_asset_counts[bucket_name] += 1

    for rule in rules:
        bucket_name = _RULE_KIND_TO_BUCKET.get(rule.rule_kind)
        if bucket_name is None:
            raise ValueError(f"Unsupported VTD rule kind in snapshot: {rule.rule_kind}")
        expected_rule_counts[bucket_name] += 1

    if summary.get("asset_counts") != expected_asset_counts:
        raise ValueError("VTD snapshot asset counts do not match summary.json.")
    if summary.get("rule_counts") != expected_rule_counts:
        raise ValueError("VTD snapshot rule counts do not match summary.json.")
    if summary.get("asset_total") != sum(expected_asset_counts.values()):
        raise ValueError("VTD snapshot asset total does not match summary.json.")
    if summary.get("rule_total") != sum(expected_rule_counts.values()):
        raise ValueError("VTD snapshot rule total does not match summary.json.")


def _validate_summary_semantics(
    summary: dict[str, Any],
    country_taxonomy: dict[str, Any],
    name_policies: list[dict[str, Any]],
) -> None:
    semantic_counts = summary.get("semantic_counts")
    if semantic_counts is None:
        summary["semantic_counts"] = {
            "country-taxonomy": len(country_taxonomy.get("countries", {})),
            "name-policies": len(name_policies),
        }
        return
    expected_semantic_counts = {
        "country-taxonomy": len(country_taxonomy.get("countries", {})),
        "name-policies": len(name_policies),
    }
    if semantic_counts != expected_semantic_counts:
        raise ValueError("VTD snapshot semantic counts do not match summary.json.")


def _index_assets_by_id(assets: list[VtdAssetRecord]) -> dict[str, VtdAssetRecord]:
    assets_by_id: dict[str, VtdAssetRecord] = {}
    for asset in assets:
        if asset.asset_id in assets_by_id:
            raise ValueError(f"Duplicate VTD asset id in snapshot: {asset.asset_id}")
        assets_by_id[asset.asset_id] = asset
    return assets_by_id


def _index_assets_by_canonical_name(
    assets: list[VtdAssetRecord],
) -> tuple[dict[str, list[VtdAssetRecord]], dict[str, list[str]]]:
    grouped: dict[str, list[VtdAssetRecord]] = {}
    for asset in assets:
        grouped.setdefault(asset.canonical_name, []).append(asset)

    canonical_index: dict[str, list[VtdAssetRecord]] = {}
    canonical_collisions: dict[str, list[str]] = {}
    for canonical_name, records in grouped.items():
        sorted_records = sorted(records, key=_asset_sort_key)
        canonical_index[canonical_name] = sorted_records
        if len(sorted_records) > 1:
            canonical_collisions[canonical_name] = [
                record.asset_id for record in sorted_records
            ]
    return canonical_index, canonical_collisions


def _index_rules_by_name(rules: list[VtdNameRule]) -> dict[str, VtdNameRule]:
    rules_by_name: dict[str, VtdNameRule] = {}
    for rule in rules:
        if rule.name in rules_by_name:
            raise ValueError(f"Duplicate VTD rule name in snapshot: {rule.name}")
        rules_by_name[rule.name] = rule
    return rules_by_name


def _require_sources(summary: dict[str, Any]) -> list[dict[str, Any]]:
    raw_sources = summary.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ValueError("VTD snapshot summary must define a non-empty 'sources' list.")
    return [
        entry
        for entry in raw_sources
        if isinstance(entry, dict)
        and isinstance(entry.get("id"), str)
        and isinstance(entry.get("kind"), str)
        and isinstance(entry.get("path"), str)
    ]


def _materialize_name_policy_sources(
    name_policies: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    materialized: list[dict[str, Any]] = []
    for policy in name_policies:
        policy_id = str(policy.get("policy_id", "")).strip()
        source_path = (
            f"{_SEMANTIC_SOURCE_ROOT}/{_SEMANTIC_NAME_POLICIES_FILE}#{policy_id}"
            if policy_id
            else f"{_SEMANTIC_SOURCE_ROOT}/{_SEMANTIC_NAME_POLICIES_FILE}"
        )
        materialized.append(
            {
                **policy,
                "source_paths": [source_path],
            }
        )
    return materialized


def _build_semantic_seed_knowledge_base(
    *,
    assets: list[VtdAssetRecord],
    rules: list[VtdNameRule],
    runtime_root: str | Path,
    release_root: str | Path,
    summary_sources: list[dict[str, Any]],
    country_taxonomy: dict[str, Any],
    name_policies: list[dict[str, Any]],
) -> VtdKnowledgeBase:
    assets_by_canonical_name, _ = _index_assets_by_canonical_name(assets)
    sources = [
        SourceEntry(
            id=str(entry["id"]),
            kind=str(entry["kind"]),
            path=str(entry["path"]),
        )
        for entry in summary_sources
    ]
    return VtdKnowledgeBase(
        runtime_root=_normalize_display_path(runtime_root),
        assets_by_id=_index_assets_by_id(assets),
        assets_by_canonical_name=assets_by_canonical_name,
        rules_by_name={rule.name: rule for rule in rules},
        sources=sources,
        metadata={
            "runtime_root": _normalize_display_path(runtime_root),
            "release_root": _normalize_display_path(release_root),
            "country_taxonomy": country_taxonomy,
            "name_policies": name_policies,
        },
    )


def _asset_sort_key(asset: VtdAssetRecord) -> tuple[Any, ...]:
    return (
        asset.asset_kind,
        asset.canonical_name.lower(),
        tuple(asset.country_codes),
        asset.relative_path,
        asset.asset_id,
    )


def _rule_sort_key(rule: VtdNameRule) -> tuple[Any, ...]:
    return (
        rule.asset_kind,
        rule.scope.get("country_code", ""),
        rule.name,
    )


def _normalize_display_path(path: str | Path) -> str:
    return Path(path).as_posix() if isinstance(path, Path) else str(path).replace("\\", "/")


__all__ = [
    "build_vtd_knowledge_snapshot",
    "load_vtd_snapshot",
    "resolve_vtd_phase1_release_root",
    "write_vtd_snapshot",
]
