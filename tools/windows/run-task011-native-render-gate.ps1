param(
    [Parameter(Mandatory=$true)][string]$SandboxProject,
    [Parameter(Mandatory=$true)][string]$EvidenceRoot,
    [Parameter(Mandatory=$true)][string]$Output,
    [string]$AssemblyPlan,
    [string]$TimelineName,
    [Nullable[int]]$ExpectedDurationFrames,
    [int]$DurationToleranceFrames = 2,
    [int]$TimeoutSeconds = 1800,
    [double]$TargetLufs = -16.0,
    [double]$ToleranceLu = 2.0,
    [double]$MaxTruePeakDbtp = -1.0,
    [string]$RenderFormat,
    [string]$RenderCodec,
    [switch]$AuthorizeResolveRender
)

$ErrorActionPreference = 'Stop'

$argsList = @(
    '-m', 'ai_video_production.task011_native_render_gate_cli',
    '--sandbox-project', $SandboxProject,
    '--evidence-root', $EvidenceRoot,
    '--output', $Output,
    '--duration-tolerance-frames', "$DurationToleranceFrames",
    '--timeout-seconds', "$TimeoutSeconds",
    '--target-lufs', "$TargetLufs",
    '--tolerance-lu', "$ToleranceLu",
    '--max-true-peak-dbtp', "$MaxTruePeakDbtp"
)

if ($AssemblyPlan) {
    $argsList += @('--assembly-plan', $AssemblyPlan)
} else {
    if (-not $TimelineName -or $null -eq $ExpectedDurationFrames) {
        throw 'Provide -AssemblyPlan or both -TimelineName and -ExpectedDurationFrames.'
    }
    $argsList += @('--timeline-name', $TimelineName, '--expected-duration-frames', "$ExpectedDurationFrames")
}

if ($RenderFormat -or $RenderCodec) {
    if (-not $RenderFormat -or -not $RenderCodec) {
        throw '-RenderFormat and -RenderCodec must be provided together.'
    }
    $argsList += @('--render-format', $RenderFormat, '--render-codec', $RenderCodec)
}

if ($AuthorizeResolveRender) {
    $argsList += '--authorize-resolve-render'
}

Write-Host '=== TASK-011 NATIVE RESOLVE RENDER GATE ==='
Write-Host "Sandbox Project: $SandboxProject"
Write-Host "Evidence Root:   $EvidenceRoot"
Write-Host "Output:          $Output"
if (-not $AuthorizeResolveRender) {
    Write-Warning 'Real Resolve rendering is NOT authorized. The gate is expected to fail closed before mutation.'
}

& python @argsList
exit $LASTEXITCODE
