from __future__ import annotations


def validate(xml: str, schema_version: str) -> list[dict[str, object]]:
    _ = xml
    return [
        {
            "line": 7,
            "message": f"fixture validator rejected schema {schema_version}",
            "severity": "error",
        }
    ]
