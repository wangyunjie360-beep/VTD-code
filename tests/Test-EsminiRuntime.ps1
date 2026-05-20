param(
  [Parameter(Mandatory = $true)]
  [string]$EsminiPath,

  [ValidateSet('scripted', 'controller-ready')]
  [string]$Target = 'scripted'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path $EsminiPath)) {
  throw "esmini executable not found: $EsminiPath"
}

$scenarioMap = @{
  scripted = Join-Path $root 'scenarios\highway_edge_merge_scripted.xosc'
  'controller-ready' = Join-Path $root 'scenarios\highway_edge_merge_controller_ready.xosc'
}

$scenarioPath = $scenarioMap[$Target]
if (-not (Test-Path $scenarioPath)) {
  throw "Scenario not found: $scenarioPath"
}

$output = & $EsminiPath --osc $scenarioPath --headless --fixed_timestep 0.05 2>&1 | Out-String
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
  throw "esmini exited with code $exitCode`n$output"
}

if ($output -match '\[error\]') {
  throw "esmini reported an error`n$output"
}

switch ($Target) {
  'scripted' {
    if ($output -match 'CollisionStop: true') {
      throw "Scripted scenario collided`n$output"
    }
    if ($output -notmatch 'SuccessfulClearance: true') {
      throw "Scripted scenario did not reach the success trigger`n$output"
    }
  }
  'controller-ready' {
    if ($output -notmatch 'Loaded OpenDRIVE') {
      throw "Controller-ready scenario did not load the road network`n$output"
    }
  }
}
