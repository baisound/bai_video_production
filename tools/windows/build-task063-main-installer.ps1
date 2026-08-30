param(
    [Parameter(Mandatory = $true)]
    [string]$IsccPath,
    [string]$Version = "0.23.0-task063",
    [string]$PayloadRoot = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not $PayloadRoot) {
    $PayloadRoot = Join-Path $repoRoot "builds\BAI Video Production"
}
$payload = (Resolve-Path -LiteralPath $PayloadRoot).Path
$compiler = (Resolve-Path -LiteralPath $IsccPath).Path
$iss = Join-Path $repoRoot "packaging\task063_main_installer.iss"

$files = Get-ChildItem -LiteralPath $payload -Recurse -File | Sort-Object FullName
if ($files.Count -eq 0) { throw "Main application payload is empty" }
$manifestLines = foreach ($file in $files) {
    $relative = $file.FullName.Substring($payload.Length).TrimStart('\').Replace('\', '/')
    $digest = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()
    "$relative`t$digest"
}
$manifestText = ($manifestLines -join "`n") + "`n"
$sha = [System.Security.Cryptography.SHA256]::Create()
try {
    $payloadTreeSha = ([BitConverter]::ToString(
        $sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($manifestText))
    )).Replace("-", "").ToLowerInvariant()
} finally {
    $sha.Dispose()
}

& $compiler "/DAppVersion=$Version" "/DPayloadRoot=$payload" "/DPayloadTreeSha=$payloadTreeSha" $iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed: $LASTEXITCODE" }

$installer = Join-Path $repoRoot "packaging\output\bai-video-production-$Version-windows-x64-setup.exe"
if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) {
    throw "Expected installer was not produced: $installer"
}
[pscustomobject]@{
    installer = $installer
    installer_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $installer).Hash.ToLowerInvariant()
    payload_tree_sha256 = $payloadTreeSha
    payload_files = $files.Count
} | ConvertTo-Json
