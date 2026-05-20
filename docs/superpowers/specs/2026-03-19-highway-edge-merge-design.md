# Highway Edge Merge Design

## Goal

Create an `esmini`-oriented OpenSCENARIO 1.x edge-case scenario package that is directly runnable and includes both:

- a scripted baseline run that demonstrates a narrowly successful avoidance maneuver
- a controller-ready variant that leaves `Ego` behavior open after initialization while keeping all surrounding traffic and timing intact

The package must be self-contained at the asset level by including both the road description (`.xodr`) and scenario files (`.xosc`).

## Runtime Target

- Primary simulator: `esmini`
- Scenario standard: `OpenSCENARIO 1.1`
- Road standard: `OpenDRIVE`
- Compatibility strategy: prefer simple, well-supported primitives over advanced optional features

## Design Summary

The scenario models a high-speed mainline merge-pressure edge case:

- `Ego` travels on the right mainline lane at highway speed
- a disabled vehicle blocks the same lane ahead
- a medium-speed vehicle occupies the adjacent left lane
- a faster rear vehicle closes from behind in the left lane
- a merge vehicle accelerates from a right-side auxiliary lane into the same conflict zone

The result is a three-direction pressure situation:

- staying on course leads toward the blocked lane
- aggressive left avoidance risks entering an occupied lane under rear pressure
- hard braking increases rear-interaction risk and wastes the narrow lateral opportunity window

The scenario is intended to feel borderline but not guaranteed to end in collision.

## Deliverables

The implementation will produce these files:

- `roads/highway_edge_merge.xodr`
- `scenarios/highway_edge_merge_scripted.xosc`
- `scenarios/highway_edge_merge_controller_ready.xosc`

Optional helper output if useful:

- `README.md` with example `esmini` launch commands and file layout assumptions

## Road Network Design

### Geometry

Use a single straight highway road segment rather than a full junction graph.

Reasoning:

- this is simpler and more stable in `esmini`
- it still reproduces the operational effect of a right-side on-ramp merge
- it reduces failure modes unrelated to the actual test objective

### Road Shape

The road will be a straight reference line long enough to cover initialization, buildup, conflict, and recovery. Expected total length is roughly `700m` to `900m`.

### Lane Layout

The road will contain:

- mainline lane `-1`
- mainline lane `-2`
- right auxiliary merge lane `-3`

The auxiliary lane exists only across the merge region:

- absent at the start of the road
- fully available through the acceleration and conflict buildup section
- tapered out downstream so the merge vehicle must join the mainline before lane termination

This gives the visual and operational behavior of a ramp merge without requiring a separate junction road.

### Road Parameters

Planned defaults:

- lane width about `3.75m`
- simple shoulders
- no elevation or superelevation
- no curves unless later needed for visual polish

The first version should remain straight because scenario timing and vehicle interaction are the real point of the test.

## Entities

Five scenario objects will be used.

### Ego

- starts in lane `-2`
- initialized at highway speed
- exists in both scenario variants

Variant split:

- `scripted` version: receives a tightly timed deceleration and left-lane avoidance sequence
- `controller-ready` version: receives only initialization actions, allowing external control takeover while remaining executable without extra assets

### BreakdownCar

- placed ahead in lane `-2`
- stationary
- slightly yawed to suggest a post-incident stop rather than a neatly parked obstacle

Purpose:

- creates the unavoidable forward conflict that forces a decision

### LeftCruiser

- starts ahead or slightly offset in lane `-1`
- maintains a moderate cruising speed

Purpose:

- denies easy early lane change
- creates a narrow and moving acceptance gap

### RearApproacher

- starts behind in lane `-1`
- travels faster than `Ego`

Purpose:

- adds rear pressure to discourage excessive braking or careless lane entry

### RampMergingCar

- starts in lane `-3`
- accelerates into the merge termination area during the main conflict buildup

Purpose:

- compresses space from the right side
- prevents the scene from collapsing into a simple “move slightly right then recover” case

## Scenario Logic

## Initial State

At scenario start:

- all entities are teleported into lane-relative positions on the same road
- all dynamic vehicles receive initial longitudinal speeds
- no catalogs are required; vehicles are defined inline for portability

## Buildup Phase

During the first several seconds:

- `Ego` closes on `BreakdownCar`
- `LeftCruiser` maintains lane occupancy and moderate speed
- `RearApproacher` closes from the left rear
- `RampMergingCar` remains behind the merge point and then accelerates into contention

The buildup must look ordinary at first. The scene should only reveal itself as dangerous once distances are already compressed.

## Conflict Window

The edge-case peak occurs when:

- `Ego` is near enough to the blockage that continuing straight is no longer viable
- the left lane is partially blocked by `LeftCruiser`
- `RearApproacher` has reduced rear-left margin
- `RampMergingCar` has become relevant near the merge taper

The scripted baseline should choose a tight but viable solution:

- controlled deceleration first
- short delay
- left lane change during the narrow gap
- stabilization after passing the disabled vehicle

This should read as “barely acceptable” rather than “comfortable”.

## Controller-Ready Variant

The controller-ready file keeps the same road, actors, placements, and non-ego timing.

Difference from scripted baseline:

- `Ego` gets initialization only
- the rest of the traffic still evolves to create the same pressure geometry
- non-ego choreography must not depend on post-init `Ego` state

This makes the file useful both as:

- an uncontrolled reference playback in `esmini`
- a harness scenario for external agent takeover

## Trigger Strategy

Use conservative trigger types that are widely supported.

Planned trigger structure:

- simulation-time trigger for startup synchronization
- relative-distance triggers against `Ego` and `BreakdownCar` in the scripted baseline where ego timing is intentionally controlled
- simple state-based triggers for sequential events

Controller-ready constraint:

- after initialization, non-ego sequencing must be driven by simulation time or non-ego references rather than `Ego` state
- this preserves the intended pressure field even when an external controller changes ego behavior

Avoid unnecessary advanced constructs. The goal is portable execution, not specification maximalism.

## End Conditions

All variants should include:

- a maximum simulation time stop trigger
- collision termination

The scripted variant should additionally end successfully when `Ego` has clearly passed the conflict zone and stabilized downstream.

## File Design Principles

### OpenSCENARIO Files

Keep the `.xosc` files conservative:

- relative reference to the local `.xodr`
- inline vehicle definitions
- common `Init`, `Story`, `Act`, `ManeuverGroup`, `Event`, `Action`, and `Trigger` patterns
- no dependence on external catalogs or proprietary controllers

### OpenDRIVE File

Keep the `.xodr` readable and minimal:

- one road
- multiple lane sections
- proper lane links between lane-section transitions
- merge lane width taper instead of a separate junction model

## Verification Plan

The scenario is only considered successful if verified in `esmini`.

Verification expectations:

- the `.xodr` loads without structural parse errors
- both `.xosc` files start and run
- the scripted variant shows the intended narrow-success maneuver
- the controller-ready variant runs with the same traffic setup and conflict timing

## Non-Goals

The first version will not attempt to model:

- weather
- friction maps
- sensor models
- detailed crash physics
- visually rich roadside assets
- multi-road junction topology unless needed to fix a concrete runtime issue

These features add complexity without improving the core edge-case value.

## Recommended Implementation Order

1. Build the straight-road `.xodr` with the merge lane lifecycle.
2. Build the scripted `.xosc` until it loads and plays end-to-end.
3. Clone and reduce it into the controller-ready `.xosc`.
4. Verify both in `esmini`.
