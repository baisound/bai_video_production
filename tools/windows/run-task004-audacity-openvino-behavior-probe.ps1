param(
  [int]$TimeoutSeconds = 1800,
  [string]$EvidenceDirectory = "task004-live-evidence-behavior"
)
$ErrorActionPreference = "Stop"
if($TimeoutSeconds -lt 30 -or $TimeoutSeconds -gt 7200) {
  throw "TimeoutSeconds must be between 30 and 7200."
}
$repo = (Get-Location).Path
$evidence = Join-Path $repo $EvidenceDirectory
if(Test-Path $evidence) {
  Remove-Item -Recurse -Force $evidence
}
New-Item -ItemType Directory -Force -Path $evidence | Out-Null
Write-Host "TASK-004 behavioral probe: Audacity/OpenVINO Noise Suppression + Music Separation (2-stem)"
Write-Host "Safety: synthetic probe audio only; current Audacity project MUST be empty."
& python -m ai_video_production.audacity_openvino_behavior_cli --evidence-root $evidence --timeout-seconds $TimeoutSeconds
$rc = $LASTEXITCODE
$report = Join-Path $evidence "audacity-openvino-behavior.json"
if($rc -eq 0) {
  Write-Host "PASS: $report"
  Write-Host "Behavior Evidence directory: $evidence"
  exit 0
}
Write-Host "PENDING/FAILED (exit $rc): $report"
Write-Host "Behavior Evidence directory: $evidence"
Write-Host "Do not modify or reinstall Audacity/OpenVINO solely because of this result; return the Evidence directory for review."
exit $rc
