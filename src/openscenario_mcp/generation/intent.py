from __future__ import annotations

from dataclasses import asdict
import re
from typing import Any

from openscenario_mcp.models import ScenarioIntent

_TIME_PATTERN = re.compile(r"(?P<value>\d+(?:\.\d+)?)\s*(?:s|sec|seconds|秒)")


def normalize_scenario_intent(
    request: str,
    *,
    locale: str | None = None,
    draft_assumptions: list[str] | None = None,
) -> dict[str, Any]:
    text = request.strip()
    normalized = text.casefold()
    assumptions = list(draft_assumptions or [])

    intent = ScenarioIntent(assumptions=list(assumptions))
    intent_checklist: list[str] = []
    unresolved_slots: list[str] = []
    open_questions: list[str] = []

    if _mentions_ego(text, normalized):
        intent.entities.append({"name": "ego", "type": "Vehicle", "role": "primary"})
        intent_checklist.append("ego")
    elif "vehicle" in normalized or "车" in text:
        intent.entities.append({"name": "ego", "type": "Vehicle", "role": "primary"})
        assumptions.append("Treat the unnamed vehicle as the primary ego vehicle.")
        intent.assumptions = list(assumptions)
        intent_checklist.append("ego")
    else:
        unresolved_slots.append("entity")
        open_questions.append("Which entity should act as the primary ego vehicle?")

    road_type = _infer_road_type(text, normalized)
    if road_type:
        intent.map_context["road_type"] = road_type

    if "变道" in text or "lane change" in normalized:
        intent.story_actions.append({"type": "lane_change"})
        intent_checklist.append("lane_change")
        if "target_lane" not in unresolved_slots:
            unresolved_slots.append("target_lane")
            open_questions.append("Which target lane should the lane change use?")

    if "减速" in text or "deceleration" in normalized or "brake" in normalized:
        intent.story_actions.append({"type": "speed_change", "mode": "deceleration"})
        intent_checklist.append("speed_change")

    trigger = _infer_trigger(text, normalized)
    if trigger is not None:
        intent.triggers.append(trigger)
        intent_checklist.append(trigger["type"])
    elif ("触发" in text or "trigger" in normalized) and "trigger_detail" not in unresolved_slots:
        unresolved_slots.append("trigger_detail")
        open_questions.append("What exact condition should trigger the scenario action?")

    if not intent.stop_conditions:
        intent.stop_conditions = []

    unresolved_slots = sorted(
        unresolved_slots,
        key=lambda slot: {"trigger_detail": 0, "target_lane": 1}.get(slot, 99),
    )

    return {
        "intent": asdict(intent),
        "intent_checklist": intent_checklist,
        "unresolved_slots": unresolved_slots,
        "open_questions": open_questions,
        "assumptions": list(intent.assumptions),
        "locale": locale,
    }


def _mentions_ego(text: str, normalized: str) -> bool:
    return any(token in text for token in ("主车", "自车")) or "ego" in normalized


def _infer_road_type(text: str, normalized: str) -> str | None:
    if "高速" in text or "highway" in normalized:
        return "highway"
    if "城市" in text or "urban" in normalized:
        return "urban"
    return None


def _infer_trigger(text: str, normalized: str) -> dict[str, Any] | None:
    if "触发" not in text and "trigger" not in normalized:
        return None

    match = _TIME_PATTERN.search(text) or _TIME_PATTERN.search(normalized)
    if match is None:
        return None

    return {
        "type": "simulation_time",
        "value": float(match.group("value")),
        "unit": "s",
    }


__all__ = ["normalize_scenario_intent"]
