param(
  [ValidateSet('road', 'scripted', 'controller-ready', 'all')]
  [string]$Target = 'all'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

function Get-RequiredPaths([string]$currentTarget) {
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

  return $required[$currentTarget]
}

function Assert-AssetsExist([string]$currentTarget) {
  $missing = Get-RequiredPaths $currentTarget | Where-Object {
    -not (Test-Path (Join-Path $root $_))
  }

  if ($missing) {
    throw "Missing assets for ${currentTarget}: $($missing -join ', ')"
  }
}

function Read-Xml([string]$path) {
  try {
    return [xml](Get-Content -Raw $path)
  } catch {
    throw "Failed to parse XML: $path`n$($_.Exception.Message)"
  }
}

function Test-Road {
  $xodrPath = Join-Path $root 'roads/highway_edge_merge.xodr'
  $xodr = Read-Xml $xodrPath
  $road = $xodr.OpenDRIVE.road

  if (-not $road) { throw 'OpenDRIVE road element is missing' }
  if ([double]$road.length -lt 700) { throw 'Road length is too short for buildup and recovery' }

  $sections = @($road.lanes.laneSection)
  if ($sections.Count -lt 4) { throw 'Expected multiple lane sections for the auxiliary merge lane lifecycle' }

  $hasLane3Mid = $false
  $lastSectionHasLane3 = $false
  foreach ($index in 0..($sections.Count - 1)) {
    $right = $sections[$index].right
    $laneIds = @($right.lane | ForEach-Object { [int]$_.id })
    if ($laneIds -contains -3 -and $index -gt 0 -and $index -lt ($sections.Count - 1)) {
      $hasLane3Mid = $true
    }
    if ($index -eq ($sections.Count - 1) -and ($laneIds -contains -3)) {
      $lastSectionHasLane3 = $true
    }
  }

  if (-not $hasLane3Mid) { throw 'Expected lane -3 in a mid-road lane section' }
  if ($lastSectionHasLane3) { throw 'Lane -3 should be gone by the final lane section' }
}

function Test-Scripted {
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

  $maneuverGroups = @($scripted.OpenSCENARIO.Storyboard.Story.Act.ManeuverGroup)
  $egoGroup = $maneuverGroups | Where-Object { $_.Actors.EntityRef.entityRef -eq 'Ego' }
  if (-not $egoGroup) { throw 'Scripted scenario must contain an ego maneuver group' }

  $stopTrigger = $scripted.OpenSCENARIO.Storyboard.StopTrigger
  if (-not $stopTrigger) { throw 'Scripted scenario must define a StopTrigger' }
}

function Test-ControllerReady {
  $controllerPath = Join-Path $root 'scenarios/highway_edge_merge_controller_ready.xosc'
  $scriptedPath = Join-Path $root 'scenarios/highway_edge_merge_scripted.xosc'
  $controller = Read-Xml $controllerPath
  $scripted = Read-Xml $scriptedPath

  $controllerGroups = @($controller.OpenSCENARIO.Storyboard.Story.Act.ManeuverGroup)
  $egoControllerGroups = $controllerGroups | Where-Object { $_.Actors.EntityRef.entityRef -eq 'Ego' }
  if ($egoControllerGroups) { throw 'Controller-ready scenario must not schedule post-init ego maneuvers' }

  $scriptedNames = @($scripted.OpenSCENARIO.Entities.ScenarioObject | ForEach-Object { $_.name })
  $controllerNames = @($controller.OpenSCENARIO.Entities.ScenarioObject | ForEach-Object { $_.name })
  if (Compare-Object $scriptedNames $controllerNames) {
    throw 'Controller-ready scenario must keep the same entity set as scripted'
  }

  if ($controller.OpenSCENARIO.RoadNetwork.LogicFile.filepath -ne '..\roads\highway_edge_merge.xodr') {
    throw 'Controller-ready scenario must reference the same local XODR'
  }
}

Assert-AssetsExist $Target

switch ($Target) {
  'road' { Test-Road }
  'scripted' { Test-Road; Test-Scripted }
  'controller-ready' { Test-Road; Test-Scripted; Test-ControllerReady }
  'all' { Test-Road; Test-Scripted; Test-ControllerReady }
}
