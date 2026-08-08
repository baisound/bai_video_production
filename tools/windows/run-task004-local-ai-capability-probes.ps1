param(
    [string]$ComfyEndpoint = "http://127.0.0.1:8188",
    [int]$AudacityTimeoutSeconds = 120,
    [switch]$SkipComfyUI,
    [switch]$SkipAudacity
)

$ErrorActionPreference = "Stop"
if ($AudacityTimeoutSeconds -lt 5 -or $AudacityTimeoutSeconds -gt 600) { throw "AudacityTimeoutSeconds must be 5-600" }
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$evidence = Join-Path $repo "task004-live-evidence"
$runtime = Join-Path $evidence "_runtime"
New-Item -ItemType Directory -Force -Path $evidence, $runtime | Out-Null

function Invoke-Probe([string]$Name, [string[]]$Arguments, [string]$OutputFile) {
    Write-Host "TASK-004 probe: $Name"
    $outPath = Join-Path $evidence $OutputFile
    $text = & python @Arguments 2>&1 | Out-String
    $exitCode = $LASTEXITCODE
    [System.IO.File]::WriteAllText($outPath, $text.Trim() + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
    if ($exitCode -eq 0) {
        Write-Host "PASS: $outPath"
    } else {
        Write-Host "PENDING/FAILED (exit $exitCode): $outPath"
    }
    return $exitCode
}

$failed = 0
Push-Location $repo
try {
    if (-not $SkipComfyUI) {
        $code = Invoke-Probe "ComfyUI capability" @("-m", "ai_video_production.comfyui_cli", "--endpoint", $ComfyEndpoint) "comfyui-capability.json"
        if ($code -ne 0) { $failed++ }
    }

    if (-not $SkipAudacity) {
        $audacityRoot = Join-Path $runtime "audacity"
        $assetRoot = Join-Path $audacityRoot "assets"
        $jobRoot = Join-Path $audacityRoot "jobs"
        $workRoot = Join-Path $audacityRoot "work"
        New-Item -ItemType Directory -Force -Path $assetRoot, $jobRoot, $workRoot | Out-Null
        $db = Join-Path $audacityRoot "capability.sqlite3"
        $code = Invoke-Probe "Audacity/OpenVINO capability" @(
            "-m", "ai_video_production.audacity_openvino_cli",
            "--db", $db,
            "--asset-root", $assetRoot,
            "--job-root", $jobRoot,
            "--work-root", $workRoot,
            "--timeout-seconds", $AudacityTimeoutSeconds
        ) "audacity-openvino-capability.json"
        if ($code -ne 0) { $failed++ }
    }
} finally {
    Pop-Location
}

Write-Host "Evidence directory: $evidence"
if ($failed -gt 0) {
    Write-Host "$failed probe(s) are not live-verified yet. This script does not install or modify third-party runtimes."
    exit 2
}
Write-Host "All requested TASK-004 capability probes completed successfully."
exit 0
