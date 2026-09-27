param(
    [string]$RunId = ([Guid]::NewGuid().ToString('N')),
    [string]$ExternalEvidenceRoot = 'C:\home\baisound\evidence\bai-video-production\TASK-102\pmst-n1'
)

$ErrorActionPreference = 'Stop'
$tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')
$runRoot = Join-Path $tempRoot ("bvp-task102-pmst-n1-{0}" -f $RunId)
$evidenceRoot = Join-Path $ExternalEvidenceRoot $RunId
$reportPath = Join-Path $runRoot 'pmst-n1a-report.json'

if ([IO.Path]::GetPathRoot($runRoot).TrimEnd('\') -eq $runRoot.TrimEnd('\')) {
    throw 'DRIVE_ROOT_PLACEMENT_REJECTED'
}
if ((Split-Path -Parent $runRoot) -ne $tempRoot) {
    throw 'RUN_ROOT_NOT_DIRECT_TEMP_CHILD'
}
if (Test-Path -LiteralPath $runRoot) {
    throw 'RUN_ROOT_ALREADY_EXISTS'
}
if ($RunId -notmatch '^[A-Za-z0-9-]{16,64}$') {
    throw 'RUN_ID_REJECTED'
}

$repositoryRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$harnessPath = Join-Path $repositoryRoot 'src\ai_video_production\task102_windows_feasibility.py'
python $harnessPath --run-root $runRoot --report $reportPath
if ($LASTEXITCODE -ne 0) {
    if (Test-Path -LiteralPath $reportPath) { Get-Content -Raw -LiteralPath $reportPath }
    throw "PMST_N1A_FAILED"
}

New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null
$externalReport = Join-Path $evidenceRoot 'pmst-n1a-report.json'
Copy-Item -LiteralPath $reportPath -Destination $externalReport
$readback = Get-Content -Raw -LiteralPath $externalReport | ConvertFrom-Json
if ($readback.result -ne 'PASS') { throw 'EVIDENCE_READBACK_FAILED' }
$reportHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $externalReport).Hash

$checkpoint = [ordered]@{
    task = 'TASK-102'
    atomic_unit = 'PMST-N1A'
    run_id = $RunId
    technical_result = 'PASS'
    resolved_temp_root = $runRoot
    resolved_external_evidence_root = $evidenceRoot
    report_sha256 = "sha256:$($reportHash.ToLowerInvariant())"
    intentional_residuals = @($runRoot, $evidenceRoot)
    prohibited_effects = @('real Project mutation', 'service installation', 'Release', 'Deploy', 'Production')
}
$checkpointPath = Join-Path $evidenceRoot 'checkpoint.json'
$checkpoint | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $checkpointPath -Encoding utf8
$null = Get-Content -Raw -LiteralPath $checkpointPath | ConvertFrom-Json

[ordered]@{
    result = 'PASS'
    run_id = $RunId
    temp_root = $runRoot
    evidence_root = $evidenceRoot
    report_sha256 = "sha256:$($reportHash.ToLowerInvariant())"
} | ConvertTo-Json -Compress
