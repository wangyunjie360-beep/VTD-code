from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Sequence


SKILL_NAME = "openscenario-xml-generator"


def default_source_path() -> Path:
    return Path(__file__).resolve().parents[1] / "skills" / SKILL_NAME / "SKILL.md"


def default_destination_root() -> Path:
    return Path.home() / ".codex" / "skills"


def install_skill(source: Path, destination_root: Path) -> Path:
    if not source.exists():
        raise FileNotFoundError(f"Skill source does not exist: {source}")

    destination_path = destination_root / SKILL_NAME / "SKILL.md"
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination_path)
    return destination_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install the project-local Codex skill for OpenSCENARIO XML generation."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=default_source_path(),
        help="Path to the source SKILL.md file.",
    )
    parser.add_argument(
        "--destination-root",
        type=Path,
        default=default_destination_root(),
        help="Directory that contains installed Codex skills.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the copy destination without writing files.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    source = args.source.resolve()
    destination_path = args.destination_root / SKILL_NAME / "SKILL.md"

    try:
        if args.dry_run:
            print(f"Would install {source} -> {destination_path}")
        else:
            installed_path = install_skill(source=source, destination_root=args.destination_root)
            print(f"Installed {SKILL_NAME} -> {installed_path}")
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        "Start a fresh Codex session after installation so the skill is discoverable for benchmark runs."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
