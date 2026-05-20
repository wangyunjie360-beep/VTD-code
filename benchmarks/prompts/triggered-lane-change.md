# Triggered Lane Change

## User Request
Create an OpenSCENARIO XML scenario where `ego` cruises in its starting lane until a trigger fires, then performs a single lane change. Keep the XML conservative and avoid extra scenario complexity beyond the triggered lane change.

## Coverage Expectations
- One vehicle named `ego`
- A trigger that starts the lane-change maneuver
- One lateral action for the lane change
- Clear stop behavior after the maneuver completes or after a bounded simulation time
