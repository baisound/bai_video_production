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
if ($SandboxProject -notmatch '^BAI_CAPABILITY_PROBE_[A-Za-z0-9_-]+$') { throw "SandboxProject must match ^BAI_CAPABILITY_PROBE_[A-Za-z0-9_-]+$" }

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$outputRoot = (Resolve-Path $OutputDir).Path
$out = Join-Path $outputRoot "resolve-sandbox-mutation-report.json"
$assetDir = Join-Path (Join-Path $outputRoot "probe-assets") $SandboxProject
New-Item -ItemType Directory -Force -Path $assetDir | Out-Null
Write-Host "TASK-002 sandbox mutation evidence"
Write-Host "Sandbox Project: $SandboxProject"
Write-Host "This sequence may create/save/export a sandbox Project, create a Bin and Timeline, import a generated 1-second silent WAV, append it, and add one marker."
Write-Host "It does NOT delete Projects, start/cancel renders, relink media, terminate Resolve, or write to a non-sandbox Project."
Write-Host "Close any real/client Project before running. The probe fails closed if a non-sandbox Project is current."

function Show-ProbeDiagnostic([string]$ReportPath) {
    if (-not (Test-Path $ReportPath)) {
        Write-Host "Diagnostic Evidence was not created: $ReportPath" -ForegroundColor Red
        return
    }
    Write-Host "Diagnostic Evidence: $ReportPath" -ForegroundColor Yellow
    try {
        $diagnostic = Get-Content -Raw -Path $ReportPath | ConvertFrom-Json
        $err = $diagnostic.mutation_error
        if ($null -eq $err) { $err = $diagnostic.connection_error }
        if ($null -ne $err) {
            Write-Host "Failure code: $($err.code)" -ForegroundColor Red
            Write-Host "Category: $($err.category)" -ForegroundColor Red
            Write-Host "Message: $($err.message)" -ForegroundColor Red
            Write-Host "Retryable: $($err.retryable)" -ForegroundColor Red
            if ($null -ne $err.details -and ($err.details.PSObject.Properties.Count -gt 0)) {
                Write-Host "Details: $($err.details | ConvertTo-Json -Compress -Depth 8)" -ForegroundColor Red
            }
        } else {
            Write-Host "No structured mutation_error/connection_error was present. Review capability rows in the Evidence JSON." -ForegroundColor Yellow
        }
        if ($null -ne $diagnostic.mutation_gate) {
            Write-Host "Mutation gate: authorized=$($diagnostic.mutation_gate.authorized), executed=$($diagnostic.mutation_gate.executed), sandbox=$($diagnostic.mutation_gate.sandbox_project)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "Could not parse diagnostic Evidence JSON: $($_.Exception.Message)" -ForegroundColor Red
    }
}

& $Python -m ai_video_production.resolve_probe_cli --kind resolve --output $out --timeout-seconds $TimeoutSeconds --allow-mutation-probes --sandbox-project $SandboxProject --probe-assets-dir $assetDir
$probeExit = $LASTEXITCODE
if ($probeExit -ne 0) {
    Show-ProbeDiagnostic $out
    throw "Sandbox mutation probe failed (exit $probeExit). The detailed Evidence path is shown above."
}
$report = Get-Content -Raw -Path $out | ConvertFrom-Json
if (-not $report.summary.mutation_probe_executed) {
    Show-ProbeDiagnostic $out
    throw "Mutation evidence did not execute."
}
Write-Host "Evidence: $out"
Write-Host "Probe assets retained: $assetDir"
Write-Host "Supported: $($report.summary.supported) / Probe required: $($report.summary.probe_required)"
