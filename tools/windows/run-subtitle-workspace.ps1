param([string]$Workspace = ".\subtitle-workspace.json", [int]$Port = 8770)
$ErrorActionPreference = "Stop"
Write-Host "BAI Subtitle Workspace: planning / SRT import / manual review"
Write-Host "Local-only. AI typo checking is OFF by default and no paid API starts from this screen."
& python -m ai_video_production.subtitle_workspace_web --workspace $Workspace --port $Port
exit $LASTEXITCODE
