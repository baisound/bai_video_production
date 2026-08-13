param(
    [Parameter(Mandatory=$true)][string]$EditorWorkRoot,
    [Parameter(Mandatory=$true)][string]$Output,
    [switch]$RequireCubaseReturn
)

$ErrorActionPreference = 'Stop'

$argsList = @(
    '-m', 'ai_video_production.task012_native_handoff_gate_cli',
    $EditorWorkRoot,
    '--output', $Output
)

if ($RequireCubaseReturn) {
    $argsList += '--require-cubase-return'
}

Write-Host '=== TASK-012 NATIVE EDITOR_WORK / CUBASE GATE ==='
Write-Host "EDITOR_WORK: $EditorWorkRoot"
Write-Host "Output:      $Output"
Write-Host "Cubase final close required: $RequireCubaseReturn"

& python @argsList
exit $LASTEXITCODE
