param(
  [switch]$Launch
)

$ErrorActionPreference = 'Stop'

Write-Host '=== TASK-036 NATIVE SHELL PREFLIGHT ==='
python -m ai_video_production.task036_native_probe_cli
$probeExit = $LASTEXITCODE

if (-not $Launch) {
  Write-Host ''
  Write-Host 'Read-only preflight complete. No UI was launched and no dependency was installed.'
  Write-Host 'Re-run with -Launch only after reviewing the preflight and native acceptance runbook.'
  exit $probeExit
}

if ($probeExit -ne 0) {
  throw 'TASK-036 preflight is not ready; refusing to launch native layout spike.'
}

Write-Host ''
Write-Host '=== TASK-036 NATIVE LAYOUT SPIKE ==='
Write-Host 'Expected: pywebview native window using installed EdgeChromium/WebView2.'
Write-Host 'This command does not install dependencies and does not perform Product mutations.'
python -m ai_video_production.task036_shell_cli
exit $LASTEXITCODE
