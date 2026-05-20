from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_prompt_guidance_packet(
    *,
    prompt_path: str | Path,
    guidance_tool,
    query: str,
    element: str,
    parent_context: str | None = None,
    top_k: int = 3,
    errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    path = Path(prompt_path)
    prompt_text = path.read_text(encoding="utf-8")
    guidance = guidance_tool(
        query=query,
        element=element,
        parent_context=parent_context,
        top_k=top_k,
        errors=errors,
    )
    return {
        "prompt_path": path.as_posix(),
        "prompt_text": prompt_text,
        "guidance": guidance,
    }


def build_request_generation_packet(
    *,
    request: str,
    packet_tool,
    country_code: str | None = None,
    stage: str = "draft",
) -> dict[str, Any]:
    generation_packet = packet_tool(
        request=request,
        country_code=country_code,
        stage=stage,
    )
    return {
        "request": request,
        "generation_packet": generation_packet,
    }


def write_guidance_packet(path: str | Path, packet: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.write_text(
        json.dumps(packet, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


__all__ = [
    "build_prompt_guidance_packet",
    "build_request_generation_packet",
    "write_guidance_packet",
]
