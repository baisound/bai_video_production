param(
    [switch]$ObsCurrent,
    [Parameter(Mandatory = $true)][int]$SampleRateHz,
    [switch]$GainReady,
    [Nullable[double]]$MeterPeakDbfs = $null,
    [double]$TargetFloorDbfs = -18.0,
    [double]$TargetCeilingDbfs = -6.0,
    [Parameter(Mandatory = $true)][ValidateSet("PASS", "FAIL", "UNKNOWN")][string]$QualityState,
    [int]$ClipSampleCount = 0,
    [Nullable[double]]$NoiseFloorDbfs = $null,
    [Nullable[double]]$SnrDb = $null,
    [string]$Output = ".\owner-voice-recording-preflight.json"
)
$ErrorActionPreference = "Stop"
$arguments = @(
    "-m", "ai_video_production.owner_voice_recording_pipeline", "preflight",
    "--sample-rate-hz", "$SampleRateHz",
    "--target-floor-dbfs", "$TargetFloorDbfs",
    "--target-ceiling-dbfs", "$TargetCeilingDbfs",
    "--quality-state", $QualityState,
    "--clip-sample-count", "$ClipSampleCount",
    "--output", $Output
)
if ($ObsCurrent) { $arguments += "--obs-current" }
if ($GainReady) { $arguments += "--gain-ready" }
if ($null -ne $MeterPeakDbfs) { $arguments += @("--meter-peak-dbfs", "$MeterPeakDbfs") }
if ($null -ne $NoiseFloorDbfs) { $arguments += @("--noise-floor-dbfs", "$NoiseFloorDbfs") }
if ($null -ne $SnrDb) { $arguments += @("--snr-db", "$SnrDb") }
Write-Host "BAI Owner Voice recording preflight (local only)"
Write-Host "This command does not start OBS or recording. READY returns exit code 0; BLOCKED/UNKNOWN returns 2."
& python @arguments
exit $LASTEXITCODE
