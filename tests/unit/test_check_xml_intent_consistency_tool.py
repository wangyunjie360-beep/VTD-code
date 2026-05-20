from __future__ import annotations

from openscenario_mcp.tools.check_xml_intent_consistency import (
    build_check_xml_intent_consistency_tool,
)

_XML_WITH_LANE_CHANGE = """\
<OpenSCENARIO>
  <Entities>
    <ScenarioObject name="ego">
      <Vehicle name="egoVehicle" vehicleCategory="car">
        <BoundingBox />
        <Performance />
        <Axles />
      </Vehicle>
    </ScenarioObject>
  </Entities>
  <Storyboard>
    <Story name="story">
      <Act name="act">
        <ManeuverGroup maximumExecutionCount="1" name="group">
          <Actors selectTriggeringEntities="false">
            <EntityRef entityRef="ego" />
          </Actors>
          <Maneuver name="maneuver">
            <Event name="event" priority="overwrite">
              <Action name="laneChange">
                <PrivateAction>
                  <LateralAction>
                    <LaneChangeAction>
                      <LaneChangeTarget>
                        <AbsoluteTargetLane value="-1" />
                      </LaneChangeTarget>
                    </LaneChangeAction>
                  </LateralAction>
                </PrivateAction>
              </Action>
              <StartTrigger>
                <ConditionGroup>
                  <Condition name="afterTwoSeconds" delay="0" conditionEdge="rising">
                    <ByValueCondition>
                      <SimulationTimeCondition value="2.0" rule="greaterThan" />
                    </ByValueCondition>
                  </Condition>
                </ConditionGroup>
              </StartTrigger>
            </Event>
          </Maneuver>
        </ManeuverGroup>
      </Act>
    </Story>
  </Storyboard>
</OpenSCENARIO>
"""

_XML_WITHOUT_LANE_CHANGE = """\
<OpenSCENARIO>
  <Entities>
    <ScenarioObject name="ego">
      <Vehicle name="egoVehicle" vehicleCategory="car">
        <BoundingBox />
        <Performance />
        <Axles />
      </Vehicle>
    </ScenarioObject>
  </Entities>
  <Storyboard />
</OpenSCENARIO>
"""


def test_check_xml_intent_consistency_reports_missing_story_action() -> None:
    tool = build_check_xml_intent_consistency_tool()

    result = tool(
        xml=_XML_WITHOUT_LANE_CHANGE,
        intent={
            "parameters": [],
            "entities": [{"name": "ego", "type": "Vehicle"}],
            "environment": {},
            "map_context": {"road_type": "highway"},
            "init_actions": [],
            "story_actions": [{"type": "lane_change"}],
            "triggers": [],
            "stop_conditions": [],
            "assumptions": [],
        },
    )

    assert "lane_change" in result["xml_intent_check"]["missing"]
    assert result["intent_consistent"] is False
    assert "missing:lane_change" in result["remaining_blockers"]


def test_check_xml_intent_consistency_matches_lane_change_trigger_and_entity() -> None:
    tool = build_check_xml_intent_consistency_tool()

    result = tool(
        xml=_XML_WITH_LANE_CHANGE,
        intent={
            "parameters": [],
            "entities": [{"name": "ego", "type": "Vehicle"}],
            "environment": {},
            "map_context": {"road_type": "highway"},
            "init_actions": [],
            "story_actions": [{"type": "lane_change"}],
            "triggers": [{"type": "simulation_time"}],
            "stop_conditions": [],
            "assumptions": [],
        },
        checklist=["ego", "lane_change", "simulation_time"],
    )

    assert set(result["xml_intent_check"]["matched"]) >= {
        "entity:ego",
        "lane_change",
        "simulation_time",
    }
    assert result["xml_intent_check"]["missing"] == []
    assert result["xml_intent_check"]["extra"] == []
    assert result["intent_consistent"] is True
