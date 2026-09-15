param(
    [Parameter(Mandatory = $true)][string]$Input,
    [string]$OutputDir = ".\owner-voice-dataset",
    [string]$StyleId = "NORMAL",
    [string]$EmotionId = "NORMAL",
    [double]$OverallTargetSeconds = 7200,
    [string]$StyleTargetSeconds,
    [string]$EmotionTargetSeconds,
    [Nullable[int]]$ChannelIndex = $null,
    [string]$Transcript,
    [string]$Model = "small",
    [ValidateSet("auto", "cpu", "cuda")][string]$Device = "auto",
    [string]$ComputeType = "int8",
    [switch]$ApproveDerivedSegments,
    [switch]$AcceptAsrTranscripts,
    [switch]$NoResume
)
$ErrorActionPreference = "Stop"
$arguments = @(
    "-m", "ai_video_production.owner_voice_recording_pipeline", "prepare",
    "--input", $Input,
    "--output-dir", $OutputDir,
    "--style-id", $StyleId,
    "--emotion-id", $EmotionId,
    "--overall-target-seconds", "$OverallTargetSeconds",
    "--model", $Model,
    "--device", $Device,
    "--compute-type", $ComputeType
)
if ($StyleTargetSeconds) { $arguments += @("--style-target-seconds", $StyleTargetSeconds) }
if ($EmotionTargetSeconds) { $arguments += @("--emotion-target-seconds", $EmotionTargetSeconds) }
if ($null -ne $ChannelIndex) { $arguments += @("--channel-index", "$ChannelIndex") }
if ($Transcript) { $arguments += @("--transcript", $Transcript) }
if ($ApproveDerivedSegments) { $arguments += "--approve-derived-segments" }
if ($AcceptAsrTranscripts) { $arguments += "--accept-asr-transcripts" }
if ($NoResume) { $arguments += "--no-resume" }
Write-Host "BAI Owner Voice recording preparation: RAW -> canonical -> ASR -> speech-continuous -> Dataset"
Write-Host "Raw recording is preserved. Model download is disabled by the local FasterWhisper contract."
& python @arguments
exit $LASTEXITCODE
