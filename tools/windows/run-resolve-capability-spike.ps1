param(
    [Parameter(Mandatory=$false)][string]$Python = "python",
    [Parameter(Mandatory=$false)][string]$OutputDir = ".\resolve-spike-evidence",
    [Parameter(Mandatory=$false)][int]$TimeoutSeconds = 90
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$srcRoot = Join-Path $repoRoot "src"
if ([string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
    $env:PYTHONPATH = $srcRoot
} else {
    $env:PYTHONPATH = "$srcRoot;$($env:PYTHONPATH)"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$resolveOut = Join-Path $OutputDir "resolve-capability-report.json"
$ipcOut = Join-Path $OutputDir "resolve-ipc-probe-report.json"

Write-Host "[preflight] Checking Python and required runtime dependency..."
& $Python -c "import jsonschema; import ai_video_production; print('Python probe preflight PASS')"
if ($LASTEXITCODE -ne 0) {
    throw "Python preflight failed. Install project dependencies first (for example: python -m pip install -e .)."
}

$resolveProcess = Get-Process -Name "Resolve" -ErrorAction SilentlyContinue
if ($null -eq $resolveProcess) {
    Write-Warning "DaVinci Resolve process was not detected. Start Resolve and wait until it is fully loaded before using this run as completion evidence."
} else {
    Write-Host "[preflight] DaVinci Resolve process detected."
}

$standardModule = $null
if (-not [string]::IsNullOrWhiteSpace($env:PROGRAMDATA)) {
    $standardModule = Join-Path $env:PROGRAMDATA "Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules\DaVinciResolveScript.py"
}
if ($null -ne $standardModule -and (Test-Path $standardModule)) {
    Write-Host "[preflight] Standard Resolve Python bridge module detected."
} else {
    Write-Warning "Standard PROGRAMDATA Resolve Python bridge module was not detected. The probe can still use RESOLVE_SCRIPT_API, RESOLVE_SCRIPT_MODULE_DIR, or PYTHONPATH when configured."
}

$failures = @()

Write-Host "[1/2] Running read-only Resolve capability probe..."
& $Python -m ai_video_production.resolve_probe_cli --kind resolve --output $resolveOut --timeout-seconds $TimeoutSeconds
$resolveExit = $LASTEXITCODE
if ($resolveExit -ne 0) {
    $failures += "Resolve capability probe exit=$resolveExit"
    Write-Warning "Resolve probe did not complete normally. A schema-valid supervision failure report should still exist when the supervisor handled the failure."
}

if (Test-Path $resolveOut) {
    try {
        $resolveReport = Get-Content -Raw -Path $resolveOut | ConvertFrom-Json
        if (-not $resolveReport.summary.live_resolve_connected) {
            $sourceKind = $resolveReport.resolve.module_source_kind
            $connectionCode = $resolveReport.connection_error.code
            $failures += "Resolve live connection not established ($connectionCode / module_source_kind=$sourceKind)"
            Write-Warning "Resolve live connection was not established. The JSON remains valid diagnostic Evidence, but it does not satisfy TASK-002 live-Resolve completion evidence."
            Write-Host "[action] Keep Resolve running and fully loaded, verify that local external scripting is allowed for the installed Resolve version, then rerun this script."
        } else {
            Write-Host "[evidence] Live Resolve scripting connection established."
            Write-Host "[evidence] Resolve version: $($resolveReport.resolve.version)"
            Write-Host "[evidence] Product: $($resolveReport.resolve.product_name)"
            Write-Host "[evidence] Module source: $($resolveReport.resolve.module_source_kind)"
        }
    } catch {
        $failures += "Resolve evidence could not be parsed after probe"
        Write-Warning "Resolve evidence parse failed: $($_.Exception.GetType().Name)"
    }
}

Write-Host "[2/2] Running local IPC comparison probe..."
& $Python -m ai_video_production.resolve_probe_cli --kind ipc --output $ipcOut --timeout-seconds $TimeoutSeconds
$ipcExit = $LASTEXITCODE
if ($ipcExit -ne 0) {
    $failures += "IPC probe exit=$ipcExit"
    Write-Warning "IPC probe did not complete normally. A schema-valid supervision failure report should still exist when the supervisor handled the failure."
}

Write-Host "Evidence directory: $OutputDir"
Write-Host "Resolve evidence: $resolveOut"
Write-Host "IPC evidence:     $ipcOut"
Write-Host "No mutation probe, project deletion, Resolve termination, or human-timeline write was requested."
Write-Host "WSL2-to-Windows reachability is NOT proven by this script and remains a separate completion-gate item."

if ($failures.Count -gt 0) {
    Write-Error ($failures -join "; ")
    exit 1
}
exit 0
