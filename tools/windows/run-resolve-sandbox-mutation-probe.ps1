param(
    [Parameter(Mandatory=$false)][string]$Python = "python",
    [Parameter(Mandatory=$false)][string]$OutputDir = ".\resolve-spike-evidence",
    [Parameter(Mandatory=$false)][string]$SandboxProject = "",
    [Parameter(Mandatory=$true)][switch]$IUnderstandThisCreatesSandboxProject,
    [Parameter(Mandatory=$false)][int]$TimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"
if (-not $IUnderstandThisCreatesSandboxProject) { throw "Explicit sandbox mutation acknowledgement is required." }
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$srcRoot = Join-Path $repoRoot "src"
if ([string]::IsNullOrWhiteSpace($env:PYTHONPATH)) { $env:PYTHONPATH = $srcRoot } else { $env:PYTHONPATH = "$srcRoot;$($env:PYTHONPATH)" }
if ([string]::IsNullOrWhiteSpace($SandboxProject)) { $SandboxProject = "BAI_CAPABILITY_PROBE_" + (Get-Date -Format "yyyyMMdd_HHmmss") }
if (-not $SandboxProject.StartsWith("BAI_CAPABILITY_PROBE_")) { throw "SandboxProject must begin BAI_CAPABILITY_PROBE_" }

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$out = Join-Path $OutputDir "resolve-sandbox-mutation-report.json"
Write-Host "TASK-002 sandbox mutation evidence"
Write-Host "Sandbox Project: $SandboxProject"
Write-Host "This sequence may create/save/export a sandbox Project, create a Bin and Timeline, import a generated 1-second silent WAV, append it, and add one marker."
Write-Host "It does NOT delete Projects, start/cancel renders, relink media, terminate Resolve, or write to a non-sandbox Project."
Write-Host "Close any real/client Project before running. The probe fails closed if a non-sandbox Project is current."

& $Python -m ai_video_production.resolve_probe_cli --kind resolve --output $out --timeout-seconds $TimeoutSeconds --allow-mutation-probes --sandbox-project $SandboxProject
if ($LASTEXITCODE -ne 0) { throw "Sandbox mutation probe failed. Keep the generated diagnostic Evidence if present." }
$report = Get-Content -Raw -Path $out | ConvertFrom-Json
if (-not $report.summary.mutation_probe_executed) { throw "Mutation evidence did not execute." }
Write-Host "Evidence: $out"
Write-Host "Supported: $($report.summary.supported) / Probe required: $($report.summary.probe_required)"
