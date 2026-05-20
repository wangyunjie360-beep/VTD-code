from pathlib import Path

from openscenario_mcp.knowledge.loader import load_element_record


POSITION_VARIANTS = [
    "WorldPosition",
    "RelativeWorldPosition",
    "RelativeObjectPosition",
    "RoadPosition",
    "RelativeRoadPosition",
    "LanePosition",
    "RelativeLanePosition",
    "RoutePosition",
    "GeoPosition",
    "TrajectoryPosition",
]

POSITION_CHOICE_GROUP = [{"members": POSITION_VARIANTS, "cardinality": "1..1"}]
POSITION_CHOICE_CONSTRAINT = [
    "Select exactly one of: "
    "WorldPosition, RelativeWorldPosition, RelativeObjectPosition, RoadPosition, "
    "RelativeRoadPosition, LanePosition, RelativeLanePosition, RoutePosition, "
    "GeoPosition, TrajectoryPosition."
]


def _load(name: str):
    return load_element_record(Path(f"knowledge/structured/elements/{name}.json"))


def test_position_wrappers_capture_shared_choice_variants() -> None:
    position = _load("Position")
    position_start = _load("PositionStart")
    target_position = _load("TargetPosition")
    target_position_master = _load("TargetPositionMaster")

    for record in (
        position,
        position_start,
        target_position,
        target_position_master,
    ):
        assert record.content_model_kind == "choice"
        assert record.child_groups == POSITION_CHOICE_GROUP
        assert record.semantic_constraints == POSITION_CHOICE_CONSTRAINT
        assert record.child_order == ["|".join(POSITION_VARIANTS)]
        assert [child["name"] for child in record.allowed_children] == POSITION_VARIANTS
        assert set(record.multiplicity.values()) == {"1..1"}

    assert position.parent_contexts == [
        "AcquirePositionAction",
        "AddEntityAction",
        "Clothoid",
        "ControlPoint",
        "DistanceCondition",
        "Polygon",
        "ReachPositionCondition",
        "TeleportAction",
        "TimeToCollisionConditionTarget",
        "TrafficSinkAction",
        "TrafficSourceAction",
        "UsedArea",
        "Vertex",
        "Waypoint",
    ]


def test_routing_and_trajectory_wrappers_capture_all_group_order_and_references() -> None:
    route = _load("Route")
    route_ref = _load("RouteRef")
    in_route_position = _load("InRoutePosition")
    acquire_position_action = _load("AcquirePositionAction")
    follow_trajectory_action = _load("FollowTrajectoryAction")
    route_position = _load("RoutePosition")
    trajectory = _load("Trajectory")
    trajectory_ref = _load("TrajectoryRef")
    trajectory_position = _load("TrajectoryPosition")
    geo_position = _load("GeoPosition")

    assert route.multiplicity["Waypoint"] == "2..unbounded"
    assert route.child_order == ["ParameterDeclarations", "Waypoint"]

    assert route_ref.child_groups == [
        {"members": ["Route", "CatalogReference"], "cardinality": "1..1"}
    ]
    assert in_route_position.child_groups == [
        {
            "members": [
                "FromCurrentEntity",
                "FromRoadCoordinates",
                "FromLaneCoordinates",
            ],
            "cardinality": "1..1",
        }
    ]
    assert trajectory_ref.child_groups == [
        {"members": ["Trajectory", "CatalogReference"], "cardinality": "1..1"}
    ]
    assert trajectory.multiplicity == {
        "ParameterDeclarations": "0..1",
        "Shape": "1..1",
    }

    for record in (
        acquire_position_action,
        follow_trajectory_action,
        route_position,
        trajectory_position,
        geo_position,
    ):
        assert record.content_model_kind == "all"
        assert record.child_order == []

    assert acquire_position_action.multiplicity == {"Position": "1..1"}
    assert follow_trajectory_action.multiplicity == {
        "Trajectory": "0..1",
        "CatalogReference": "0..1",
        "TimeReference": "1..1",
        "TrajectoryFollowingMode": "1..1",
        "TrajectoryRef": "0..1",
    }
    assert route_position.multiplicity == {
        "RouteRef": "1..1",
        "Orientation": "0..1",
        "InRoutePosition": "1..1",
    }
    assert trajectory_position.multiplicity == {
        "Orientation": "0..1",
        "TrajectoryRef": "1..1",
    }
    assert geo_position.multiplicity == {"Orientation": "0..1"}


def test_geometry_records_capture_control_points_repeats_and_source_anchors() -> None:
    shape = _load("Shape")
    clothoid = _load("Clothoid")
    clothoid_spline = _load("ClothoidSpline")
    clothoid_spline_segment = _load("ClothoidSplineSegment")
    control_point = _load("ControlPoint")
    knot = _load("Knot")
    nurbs = _load("Nurbs")
    polygon = _load("Polygon")
    polyline = _load("Polyline")
    vertex = _load("Vertex")

    assert shape.child_groups == [
        {
            "members": ["Polyline", "Clothoid", "ClothoidSpline", "Nurbs"],
            "cardinality": "1..1",
        }
    ]
    assert clothoid_spline.multiplicity["ClothoidSplineSegment"] == "1..unbounded"
    assert clothoid_spline_segment.multiplicity == {
        "PositionStart": "0..1",
        "MotionStart": "0..1",
    }
    assert control_point.allowed_children == [{"name": "Position", "cardinality": "1..1"}]
    assert control_point.optional_attributes == [
        {"name": "time", "type": "Double"},
        {"name": "weight", "type": "Double"},
    ]
    assert knot.required_attributes == [{"name": "value", "type": "Double"}]
    assert nurbs.multiplicity == {
        "ControlPoint": "2..unbounded",
        "Knot": "2..unbounded",
    }
    assert polyline.multiplicity["Vertex"] == "2..unbounded"
    assert polygon.multiplicity["Position"] == "3..unbounded"
    assert vertex.multiplicity == {"Position": "1..1", "Motion": "0..1"}

    assert {
        "Clothoid": clothoid.source_path,
        "ClothoidSpline": clothoid_spline.source_path,
        "ClothoidSplineSegment": clothoid_spline_segment.source_path,
        "ControlPoint": control_point.source_path,
        "Knot": knot.source_path,
        "Nurbs": nurbs.source_path,
        "Polygon": polygon.source_path,
        "Polyline": polyline.source_path,
        "Vertex": vertex.source_path,
    } == {
        "Clothoid": "knowledge/raw/schema/OpenSCENARIO.xsd#L969; "
        "knowledge/raw/schema/OpenSCENARIO.xsd#L2128",
        "ClothoidSpline": "knowledge/raw/schema/OpenSCENARIO.xsd#L984; "
        "knowledge/raw/schema/OpenSCENARIO.xsd#L2129",
        "ClothoidSplineSegment": "knowledge/raw/schema/OpenSCENARIO.xsd#L986; "
        "knowledge/raw/schema/OpenSCENARIO.xsd#L991",
        "ControlPoint": "knowledge/raw/schema/OpenSCENARIO.xsd#L1081; "
        "knowledge/raw/schema/OpenSCENARIO.xsd#L1603",
        "Knot": "knowledge/raw/schema/OpenSCENARIO.xsd#L1411; "
        "knowledge/raw/schema/OpenSCENARIO.xsd#L1604",
        "Nurbs": "knowledge/raw/schema/OpenSCENARIO.xsd#L1601; "
        "knowledge/raw/schema/OpenSCENARIO.xsd#L2130",
        "Polygon": "knowledge/raw/schema/OpenSCENARIO.xsd#L1816; "
        "knowledge/raw/schema/OpenSCENARIO.xsd#L2310",
        "Polyline": "knowledge/raw/schema/OpenSCENARIO.xsd#L1821; "
        "knowledge/raw/schema/OpenSCENARIO.xsd#L2127",
        "Vertex": "knowledge/raw/schema/OpenSCENARIO.xsd#L1823; "
        "knowledge/raw/schema/OpenSCENARIO.xsd#L2646",
    }
