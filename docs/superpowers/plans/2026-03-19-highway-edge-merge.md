# Highway Edge Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained `esmini`-targeted package with one `OpenDRIVE` merge-map and two `OpenSCENARIO 1.1` files: a scripted narrow-success baseline and a controller-ready variant.

**Architecture:** Keep the road model minimal and stable by using one straight road with multiple lane sections and a temporary auxiliary lane `-3` that appears, runs full-width through the conflict area, and tapers out. Build the scripted scenario first with ego-relative triggers, then derive the controller-ready variant by removing post-init ego choreography and switching non-ego timing to simulation-time or non-ego references.

**Tech Stack:** XML (`.xodr`, `.xosc`), PowerShell smoke validation, `esmini` runtime playback

---

### Task 1: Scaffold The Project And Add A Failing Asset Validator

**Files:**
- Create: `D:\wyj\OPenscenario\tests\Test-OpenXAssets.ps1`
- Create: `D:\wyj\OPenscenario\roads\highway_edge_merge.xodr`
- Create: `D:\wyj\OPenscenario\scenarios\highway_edge_merge_scripted.xosc`
- Create: `D:\wyj\OPenscenario\scenarios\highway_edge_merge_controller_ready.xosc`

- [ ] **Step 1: Create the directory layout and a validator script that checks required files exist**

```powershell
param(
  [ValidateSet('road', 'scripted', 'controller-ready', 'all')]
  [string]$Target = 'all'
)

$root = Split-Path -Parent $PSScriptRoot
$required = @{
  road = @('roads/highway_edge_merge.xodr')
  scripted = @('roads/highway_edge_merge.xodr', 'scenarios/highway_edge_merge_scripted.xosc')
  'controller-ready' = @(
    'roads/highway_edge_merge.xodr',
    'scenarios/highway_edge_merge_scripted.xosc',
    'scenarios/highway_edge_merge_controller_ready.xosc'
  )
  all = @(
    'roads/highway_edge_merge.xodr',
    'scenarios/highway_edge_merge_scripted.xosc',
    'scenarios/highway_edge_merge_controller_ready.xosc'
  )
}

$missing = $required[$Target] | Where-Object { -not (Test-Path (Join-Path $root $_)) }
if ($missing) {
  throw "Missing assets for $Target: $($missing -join ', ')"
}
```

- [ ] **Step 2: Run the validator before any assets exist**

Run: `powershell -ExecutionPolicy Bypass -File tests\Test-OpenXAssets.ps1 -Target all`  
Expected: FAIL with `Missing assets for all`

- [ ] **Step 3: Expand the validator so it can parse XML files and stop on malformed XML**

```powershell
function Read-Xml([string]$path) {
  try {
    return [xml](Get-Content -Raw $path)
  } catch {
    throw "Failed to parse XML: $path`n$($_.Exception.Message)"
  }
}
```

- [ ] **Step 4: Re-run the validator to confirm it still fails until the real assets are created**

Run: `powershell -ExecutionPolicy Bypass -File tests\Test-OpenXAssets.ps1 -Target road`  
Expected: FAIL with `Missing assets for road`

- [ ] **Step 5: Skip commit bookkeeping because `D:\wyj\OPenscenario` is not a git repository**

Run: `git rev-parse --show-toplevel`  
Expected: FAIL with `not a git repository`

### Task 2: Build The Straight Merge OpenDRIVE Map

**Files:**
- Modify: `D:\wyj\OPenscenario\tests\Test-OpenXAssets.ps1`
- Create: `D:\wyj\OPenscenario\roads\highway_edge_merge.xodr`

- [ ] **Step 1: Add a failing road-specific validation block**

```powershell
$xodrPath = Join-Path $root 'roads/highway_edge_merge.xodr'
$xodr = Read-Xml $xodrPath
$road = $xodr.OpenDRIVE.road
if (-not $road) { throw 'OpenDRIVE road element is missing' }
if ([double]$road.length -lt 700) { throw 'Road length is too short for buildup and recovery' }
$laneSectionCount = @($road.lanes.laneSection).Count
if ($laneSectionCount -lt 3) { throw 'Expected multiple lane sections for the auxiliary merge lane lifecycle' }
```

- [ ] **Step 2: Run the road validator before the road file exists**

Run: `powershell -ExecutionPolicy Bypass -File tests\Test-OpenXAssets.ps1 -Target road`  
Expected: FAIL with `Missing assets for road`

- [ ] **Step 3: Implement `roads/highway_edge_merge.xodr` with a straight reference line and lane-section transitions**

Use these concrete values:

- total road length: `800`
- lane width for mainline lanes: `3.75`
- lane sections:
  - `s=0`: lanes `-1`, `-2`
  - `s=180`: introduce lane `-3` with width ramp-up
  - `s=300`: lane `-3` at full width through the merge pressure zone
  - `s=520`: taper lane `-3` down toward zero
  - `s=640`: return to only lanes `-1`, `-2`

Keep the geometry straight and flat. Use proper predecessor/successor lane links across lane sections so `esmini` can follow the lane continuity.

- [ ] **Step 4: Extend the validator to assert the merge-lane lifecycle**

```powershell
$sections = @($road.lanes.laneSection)
$hasLane3Mid = $false
$lastSectionHasLane3 = $false
for ($i = 0; $i -lt $sections.Count; $i++) {
  $right = $sections[$i].right
  $laneIds = @($right.lane | ForEach-Object { [int]$_.id })
  if ($laneIds -contains -3 -and $i -gt 0 -and $i -lt ($sections.Count - 1)) { $hasLane3Mid = $true }
  if ($i -eq ($sections.Count - 1) -and ($laneIds -contains -3)) { $lastSectionHasLane3 = $true }
}
if (-not $hasLane3Mid) { throw 'Expected lane -3 in a mid-road lane section' }
if ($lastSectionHasLane3) { throw 'Lane -3 should be gone by the final lane section' }
```

- [ ] **Step 5: Run the road validator after implementing the map**

Run: `powershell -ExecutionPolicy Bypass -File tests\Test-OpenXAssets.ps1 -Target road`  
Expected: PASS with no output

### Task 3: Build The Scripted Baseline Scenario

**Files:**
- Modify: `D:\wyj\OPenscenario\tests\Test-OpenXAssets.ps1`
- Create: `D:\wyj\OPenscenario\scenarios\highway_edge_merge_scripted.xosc`

- [ ] **Step 1: Add a failing scripted-scenario validation block**

```powershell
$scriptedPath = Join-Path $root 'scenarios/highway_edge_merge_scripted.xosc'
$scripted = Read-Xml $scriptedPath
if ($scripted.OpenSCENARIO.FileHeader.revMajor -ne '1' -or $scripted.OpenSCENARIO.FileHeader.revMinor -ne '1') {
  throw 'Scripted scenario must target OpenSCENARIO 1.1'
}
$logicFile = $scripted.OpenSCENARIO.RoadNetwork.LogicFile.filepath
if ($logicFile -ne '..\roads\highway_edge_merge.xodr') {
  throw "Unexpected LogicFile path: $logicFile"
}
$entityCount = @($scripted.OpenSCENARIO.Entities.ScenarioObject).Count
if ($entityCount -ne 5) { throw 'Scripted scenario must define exactly five scenario objects' }
```

- [ ] **Step 2: Run scripted validation before the scenario exists**

Run: `powershell -ExecutionPolicy Bypass -File tests\Test-OpenXAssets.ps1 -Target scripted`  
Expected: FAIL with `Missing assets for scripted`

- [ ] **Step 3: Implement `scenarios/highway_edge_merge_scripted.xosc`**

Use these concrete actor values as the first-pass tuning target:

- `Ego`: lane `-2`, `s=300`, speed `27 m/s`
- `BreakdownCar`: lane `-2`, `s=470`, speed `0`
- `LeftCruiser`: lane `-1`, `s=430`, speed `24 m/s`
- `RearApproacher`: lane `-1`, `s=250`, speed `31 m/s`
- `RampMergingCar`: lane `-3`, `s=335`, speed `18 m/s`

Implement these storyboard rules:

- inline vehicle definitions, no catalogs
- `Init` teleports all actors and sets initial speeds
- non-ego actors get lane-keeping longitudinal actions immediately
- `RampMergingCar` accelerates deeper into the merge area after a short delay
- `Ego` first decelerates, then performs a single left lane change through a narrow gap, then stabilizes
- use collision stop conditions and a success stop when `Ego` has cleared the blockage

Prefer `SimulationTimeCondition`, `RelativeDistanceCondition`, `SpeedAction`, and `LaneChangeAction`. Do not introduce custom controllers.

- [ ] **Step 4: Extend the validator with baseline-specific assertions**

```powershell
$maneuverGroups = @($scripted.OpenSCENARIO.Storyboard.Story.Act.ManeuverGroup)
$egoGroup = $maneuverGroups | Where-Object { $_.Actors.EntityRef.entityRef -eq 'Ego' }
if (-not $egoGroup) { throw 'Scripted scenario must contain an ego maneuver group' }
$stopTrigger = $scripted.OpenSCENARIO.Storyboard.StopTrigger
if (-not $stopTrigger) { throw 'Scripted scenario must define a StopTrigger' }
```

- [ ] **Step 5: Run scripted validation after implementing the file**

Run: `powershell -ExecutionPolicy Bypass -File tests\Test-OpenXAssets.ps1 -Target scripted`  
Expected: PASS with no output

### Task 4: Derive The Controller-Ready Variant

**Files:**
- Modify: `D:\wyj\OPenscenario\tests\Test-OpenXAssets.ps1`
- Create: `D:\wyj\OPenscenario\scenarios\highway_edge_merge_controller_ready.xosc`

- [ ] **Step 1: Add a failing controller-ready validation block**

```powershell
$controllerPath = Join-Path $root 'scenarios/highway_edge_merge_controller_ready.xosc'
$controller = Read-Xml $controllerPath
$controllerGroups = @($controller.OpenSCENARIO.Storyboard.Story.Act.ManeuverGroup)
$egoControllerGroups = $controllerGroups | Where-Object { $_.Actors.EntityRef.entityRef -eq 'Ego' }
if ($egoControllerGroups) { throw 'Controller-ready scenario must not schedule post-init ego maneuvers' }
```

- [ ] **Step 2: Run controller-ready validation before the scenario exists**

Run: `powershell -ExecutionPolicy Bypass -File tests\Test-OpenXAssets.ps1 -Target controller-ready`  
Expected: FAIL with `Missing assets for controller-ready`

- [ ] **Step 3: Create `scenarios/highway_edge_merge_controller_ready.xosc` by copying the scripted file and removing ego story actions**

Keep these constraints exact:

- same road path and entity set as the scripted scenario
- same initial positions and speeds
- no post-init `Ego` maneuver group
- non-ego events must be driven by simulation time or non-ego references only
- collision and max-duration stop conditions remain in place

- [ ] **Step 4: Extend the validator so it also checks entity parity and road parity against the scripted file**

```powershell
$scriptedNames = @($scripted.OpenSCENARIO.Entities.ScenarioObject | ForEach-Object { $_.name })
$controllerNames = @($controller.OpenSCENARIO.Entities.ScenarioObject | ForEach-Object { $_.name })
if ((Compare-Object $scriptedNames $controllerNames)) { throw 'Controller-ready scenario must keep the same entity set as scripted' }
if ($controller.OpenSCENARIO.RoadNetwork.LogicFile.filepath -ne '..\roads\highway_edge_merge.xodr') {
  throw 'Controller-ready scenario must reference the same local XODR'
}
```

- [ ] **Step 5: Run controller-ready validation after implementing the file**

Run: `powershell -ExecutionPolicy Bypass -File tests\Test-OpenXAssets.ps1 -Target controller-ready`  
Expected: PASS with no output

### Task 5: Add Runtime Notes And Run Full Verification

**Files:**
- Modify: `D:\wyj\OPenscenario\tests\Test-OpenXAssets.ps1`
- Create: `D:\wyj\OPenscenario\README.md`

- [ ] **Step 1: Write `README.md` with layout and playback commands**

Include:

- directory tree for `roads`, `scenarios`, `tests`
- scripted playback command
- controller-ready playback command
- note that `esmini` must be installed or callable on `PATH`

Use these commands in the README:

```powershell
esmini --osc scenarios\highway_edge_merge_scripted.xosc --fixed_timestep 0.05
esmini --osc scenarios\highway_edge_merge_controller_ready.xosc --fixed_timestep 0.05
```

- [ ] **Step 2: Extend the validator so `-Target all` runs the road, scripted, and controller-ready checks in one pass**

Before adding the final `switch`, refactor the validator into explicit functions:

```powershell
function Test-Road { }
function Test-Scripted { }
function Test-ControllerReady { }
```

Then wire the existing road/scripted/controller-ready checks into those functions and use:

```powershell
switch ($Target) {
  'road' { Test-Road }
  'scripted' { Test-Road; Test-Scripted }
  'controller-ready' { Test-Road; Test-Scripted; Test-ControllerReady }
  'all' { Test-Road; Test-Scripted; Test-ControllerReady }
}
```

- [ ] **Step 3: Run the full PowerShell smoke validation**

Run: `powershell -ExecutionPolicy Bypass -File tests\Test-OpenXAssets.ps1 -Target all`  
Expected: PASS with no output

- [ ] **Step 4: Check whether `esmini` is callable before claiming runtime success**

Run: `where.exe esmini`  
Expected: either a path to `esmini.exe` or `INFO: Could not find files for the given pattern(s).`

- [ ] **Step 5: If `esmini` is available, run the scripted scenario with visible playback**

Run: `esmini --osc scenarios\highway_edge_merge_scripted.xosc --fixed_timestep 0.05 --window 60 60 1280 720`  
Expected: scenario loads and runs without XML parse or road-network errors

- [ ] **Step 6: Inspect the scripted runtime behavior against the acceptance checklist**

Confirm all of the following before claiming scripted success:

- `Ego` remains in lane `-2` during the early buildup
- `Ego` decelerates before reaching `BreakdownCar`
- `Ego` performs a single left lane change to avoid the blockage
- `Ego` clears `BreakdownCar` without collision and stabilizes downstream
- `RearApproacher`, `LeftCruiser`, and `RampMergingCar` are all visibly relevant during the conflict window

- [ ] **Step 7: If `esmini` is available, run the controller-ready scenario with visible playback**

Run: `esmini --osc scenarios\highway_edge_merge_controller_ready.xosc --fixed_timestep 0.05 --window 60 60 1280 720`  
Expected: scenario loads and runs without XML parse or road-network errors

- [ ] **Step 8: Inspect the controller-ready runtime behavior against the acceptance checklist**

Confirm all of the following before claiming controller-ready success:

- the same five actors spawn in the same initial configuration as the scripted file
- non-ego traffic still creates the same forward block, left-lane occupation, rear pressure, and merge pressure
- there is no storyboard-driven post-init ego maneuver
- the conflict geometry emerges on roughly the same early timeline even when ego remains uncontrolled

- [ ] **Step 9: Report the actual verification state**

Only claim full success if:

- the full PowerShell validator passes
- `esmini` is installed
- both runtime commands complete without scenario-load or network-linking errors
- the scripted and controller-ready acceptance checklists are satisfied

If `esmini` is not installed, report that the assets are structurally validated but not runtime-verified.
