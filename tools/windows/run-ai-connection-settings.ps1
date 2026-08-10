param(
    [string]$SettingsPath = ".\ai-connection-settings.json",
    [string]$ProfilePath = ".\profiles\ai-connection-creator.example.json",
    [int]$Port = 8765,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$arguments = @(
    "-m", "ai_video_production.connection_settings_web",
    "--settings", $SettingsPath,
    "--profile", $ProfilePath,
    "--port", $Port
)
if ($NoBrowser) {
    $arguments += "--no-browser"
}

Write-Host "BAI Video Production: local AI Connection settings"
Write-Host "Safety: saving settings does not start paid APIs, generation, or editing."
& python @arguments
exit $LASTEXITCODE
