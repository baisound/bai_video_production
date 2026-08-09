param(
  [int]$TimeoutSeconds = 1800,
  [string]$EvidenceDirectory = "task004-live-evidence-behavior",
  [string]$FFprobeExecutable = ""
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
function Resolve-FFprobeExecutable {
  param([string]$ExplicitPath)
  $candidates = [System.Collections.Generic.List[string]]::new()
  if(-not [string]::IsNullOrWhiteSpace($ExplicitPath)) { $candidates.Add($ExplicitPath) }
  if(-not [string]::IsNullOrWhiteSpace($env:BAI_FFPROBE_EXECUTABLE)) { $candidates.Add($env:BAI_FFPROBE_EXECUTABLE) }
  $command = Get-Command ffprobe.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
  if($null -ne $command) { $candidates.Add($command.Source) }
  $ffmpegCommand = Get-Command ffmpeg.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
  if($null -ne $ffmpegCommand) { $candidates.Add((Join-Path (Split-Path $ffmpegCommand.Source -Parent) "ffprobe.exe")) }
  foreach($candidate in @((Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links\ffprobe.exe"),(Join-Path $env:ProgramData "chocolatey\bin\ffprobe.exe"),(Join-Path $env:USERPROFILE "scoop\shims\ffprobe.exe"))) { $candidates.Add($candidate) }
  $wingetPackages = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
  if(Test-Path -LiteralPath $wingetPackages -PathType Container) {
    $match = Get-ChildItem -LiteralPath $wingetPackages -Filter ffprobe.exe -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if($null -ne $match) { $candidates.Add($match.FullName) }
  }
  foreach($candidate in $candidates) {
    try {
      $resolved = (Resolve-Path -LiteralPath $candidate -ErrorAction Stop).Path
      if((Test-Path -LiteralPath $resolved -PathType Leaf) -and ([IO.Path]::GetFileName($resolved) -ieq "ffprobe.exe")) { return $resolved }
    } catch { continue }
  }
  throw "ffprobe.exe was not found. Install FFmpeg with ffprobe, pass -FFprobeExecutable, or set BAI_FFPROBE_EXECUTABLE. The behavioral probe will not bypass canonical media validation."
}
$ffprobe = Resolve-FFprobeExecutable -ExplicitPath $FFprobeExecutable
Write-Host "TASK-004 behavioral probe: Audacity/OpenVINO Noise Suppression + Music Separation (2-stem)"
Write-Host "Safety: synthetic probe audio only; current Audacity project MUST be empty."
Write-Host "Media validation: ffprobe resolved."
& python -m ai_video_production.audacity_openvino_behavior_cli --evidence-root $evidence --timeout-seconds $TimeoutSeconds --ffprobe-executable $ffprobe
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
