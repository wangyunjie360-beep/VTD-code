from __future__ import annotations

from functools import lru_cache
from pathlib import Path

DEFAULT_SCHEMA_VERSION = "1.4.0"
DEFAULT_SCHEMA_RELATIVE_PATH = Path("knowledge") / "raw" / "schema" / "OpenSCENARIO.xsd"


@lru_cache(maxsize=1)
def get_project_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / DEFAULT_SCHEMA_RELATIVE_PATH).is_file():
            return candidate

    raise FileNotFoundError(
        f"Could not locate the project root containing {DEFAULT_SCHEMA_RELATIVE_PATH!s}."
    )


@lru_cache(maxsize=1)
def get_default_schema_path() -> Path:
    schema_path = get_project_root() / DEFAULT_SCHEMA_RELATIVE_PATH
    if not schema_path.is_file():
        raise FileNotFoundError(f"OpenSCENARIO schema not found at {schema_path!s}.")
    return schema_path
