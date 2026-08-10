param(
    [Parameter(Mandatory = $true)][string]$MediaPath,
    [string]$OutputDirectory = ".\task006-transcription-output",
    [string]$Model = "small",
    [string]$Language = "ja",
    [ValidateSet("auto", "cpu", "cuda")][string]$Device = "auto",
    [string]$ComputeType = "int8",
    [switch]$AllowModelDownload
)

$ErrorActionPreference = "Stop"
$arguments = @(
    "-m", "ai_video_production.transcription_cli", $MediaPath,
    "--output-dir", $OutputDirectory,
    "--model", $Model,
    "--language", $Language,
    "--device", $Device,
    "--compute-type", $ComputeType
)
if ($AllowModelDownload) {
    $arguments += "--allow-model-download"
}

Write-Host "TASK-006 local transcription: FasterWhisper -> Transcript + SRT"
Write-Host "Privacy: inference is local. Transcript text is written only to the selected output directory."
if ($AllowModelDownload) {
    Write-Host "Model download: explicitly authorized when the selected model is not cached."
} else {
    Write-Host "Model download: disabled. Use -AllowModelDownload only when you approve the download."
}
& python @arguments
exit $LASTEXITCODE
