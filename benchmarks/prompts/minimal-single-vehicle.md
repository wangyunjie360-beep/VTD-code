# Minimal Single Vehicle

## User Request
Create the smallest reasonable OpenSCENARIO XML scenario for one vehicle named `ego`. The vehicle should start already on the road, continue at a steady speed, and the scenario should stop after 5 seconds of simulation time.

## Coverage Expectations
- One scenario object for `ego`
- Conservative init behavior with no unnecessary catalogs or controllers
- A time-based stop condition
- No extra actors, weather, or traffic complexity unless schema-required
