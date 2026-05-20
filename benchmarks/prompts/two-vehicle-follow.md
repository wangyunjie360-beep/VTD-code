# Two Vehicle Follow

## User Request
Create an OpenSCENARIO XML scenario with two vehicles, `lead` and `ego`, where `ego` follows `lead` in the same lane at a safe distance. Keep the scenario conservative and avoid lane changes or sudden maneuvers.

## Coverage Expectations
- Two scenario objects with distinct roles
- Story behavior that keeps `ego` behind `lead`
- Triggers or stop conditions that bound the run cleanly
- No extra entities or unsupported behavior beyond the follow scenario
