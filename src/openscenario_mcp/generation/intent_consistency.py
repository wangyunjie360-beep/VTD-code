from __future__ import annotations

from typing import Any
import xml.etree.ElementTree as ET


def check_xml_intent_consistency(
    xml: str,
    intent: dict[str, Any],
    *,
    checklist: list[str] | None = None,
) -> dict[str, Any]:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        message = f"parse_error:{exc.msg}"
        return {
            "xml_intent_check": {
                "matched": [],
                "missing": [],
                "extra": [],
            },
            "intent_consistent": False,
            "remaining_blockers": [message],
        }

    matched: list[str] = []
    missing: list[str] = []
    extra: list[str] = []

    scenario_object_names = {
        element.attrib.get("name", "").strip()
        for element in root.findall(".//ScenarioObject")
        if element.attrib.get("name", "").strip()
    }
    has_lane_change = root.find(".//LaneChangeAction") is not None
    has_speed_action = root.find(".//SpeedAction") is not None
    has_sim_time = root.find(".//SimulationTimeCondition") is not None
    has_stop_trigger = root.find(".//StopTrigger") is not None

    for entity in intent.get("entities", []):
        if not isinstance(entity, dict):
            continue
        name = str(entity.get("name", "")).strip()
        if not name:
            continue
        token = f"entity:{name}"
        if name in scenario_object_names:
            matched.append(token)
        else:
            missing.append(token)

    requested_story_actions = {_story_action_type(action) for action in intent.get("story_actions", [])}
    requested_story_actions.discard("")
    if "lane_change" in requested_story_actions:
        if has_lane_change:
            matched.append("lane_change")
        else:
            missing.append("lane_change")
    elif has_lane_change:
        extra.append("lane_change")

    if "speed_change" in requested_story_actions:
        if has_speed_action:
            matched.append("speed_change")
        else:
            missing.append("speed_change")
    elif has_speed_action:
        extra.append("speed_change")

    requested_triggers = {_trigger_type(trigger) for trigger in intent.get("triggers", [])}
    requested_triggers.discard("")
    if "simulation_time" in requested_triggers:
        if has_sim_time:
            matched.append("simulation_time")
        else:
            missing.append("simulation_time")
    elif has_sim_time:
        extra.append("simulation_time")

    requested_stop_conditions = {
        _stop_condition_type(condition) for condition in intent.get("stop_conditions", [])
    }
    requested_stop_conditions.discard("")
    if requested_stop_conditions:
        if has_stop_trigger:
            matched.append("stop_trigger")
        else:
            missing.append("stop_trigger")

    if checklist:
        for item in checklist:
            text = str(item).strip()
            if not text:
                continue
            if text == "ego" and "entity:ego" in matched:
                continue
            if text in matched or text in missing:
                continue
            if text in scenario_object_names:
                matched.append(text)

    matched = _dedupe(matched)
    missing = _dedupe(missing)
    extra = _dedupe(extra)
    blockers = [f"missing:{item}" for item in missing] + [f"extra:{item}" for item in extra]
    return {
        "xml_intent_check": {
            "matched": matched,
            "missing": missing,
            "extra": extra,
        },
        "intent_consistent": not blockers,
        "remaining_blockers": blockers,
    }


def _story_action_type(action: Any) -> str:
    if isinstance(action, dict):
        return str(action.get("type", "")).strip()
    if isinstance(action, str):
        lowered = action.casefold()
        if "lane change" in lowered or "变道" in action:
            return "lane_change"
        if "speed" in lowered or "deceleration" in lowered or "减速" in action:
            return "speed_change"
    return ""


def _trigger_type(trigger: Any) -> str:
    if isinstance(trigger, dict):
        return str(trigger.get("type", "")).strip()
    if isinstance(trigger, str):
        lowered = trigger.casefold()
        if "simulation time" in lowered or "仿真时间" in trigger:
            return "simulation_time"
    return ""


def _stop_condition_type(condition: Any) -> str:
    if isinstance(condition, dict):
        return str(condition.get("type", "")).strip() or "stop_trigger"
    if isinstance(condition, str) and condition.strip():
        return "stop_trigger"
    return ""


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


__all__ = ["check_xml_intent_consistency"]
